from __future__ import annotations

"""
Closing-line value (CLV) calculation.

CLV answers: "after this wallet entered a position, did the market move in
their favor?" It is one of the few metrics in prediction-market / sports
betting analysis that separates skill from luck reasonably well, because it
doesn't depend on whether the bet actually won - it only asks whether the
price moved the direction the wallet's side needed it to move.

Side-adjustment
----------------
A BUY of an outcome token profits when that token's price rises. So for a
BUY at entry_price, CLV at horizon H is:

    clv_H = price_H - entry_price   (positive = market moved in their favor)

A SELL trade in the trades feed is closing/reducing an existing position,
not a fresh directional bet, so CLV is not well-defined the same way for it.
We explicitly skip CLV for SELL trades rather than guessing a sign
convention for them (see `is_clv_eligible_side`). This means our CLV sample
only covers position-opening trades - documented in every summary this
module returns.

Data availability
------------------
Price history comes from `PolymarketClient.get_prices_history`
(`/prices-history` on the CLOB API). This build environment has no network
egress to polymarket.com, so the retention window and time resolution of
that endpoint have not been verified against live data here. If a requested
horizon has no matching data point within `TOLERANCE_SECONDS` of the target
time, we record NULL and set the corresponding `missing_*` flag to True.
We never interpolate or substitute the nearest available price without
flagging it as such.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

from polyalgo.clients.polymarket import PolymarketClient
from polyalgo.db import get_engine

logger = logging.getLogger(__name__)

HORIZONS_HOURS = {"1h": 1, "6h": 6, "24h": 24}

# How far a returned price-history point can be from the exact target
# timestamp and still count as "the price at that horizon". Prices-history
# resolution is coarser than tick-level, so this needs to be generous.
TOLERANCE_SECONDS = 45 * 60  # 45 minutes
CLOSE_TOLERANCE_SECONDS = TOLERANCE_SECONDS * 2

CLV_ELIGIBLE_SIDES = {"BUY"}

PriceHistoryFetcher = Callable[[str, int, int], object]


def is_clv_eligible_side(side: str | None) -> bool:
    """Only BUY (position-opening) trades get a CLV calculation.

    SELL trades close/reduce an existing position rather than opening a new
    directional bet, so "did price move in their favor after this trade" is
    not a well-defined question for them with the data we have.
    """
    return (side or "").upper() in CLV_ELIGIBLE_SIDES


def _parse_ts(value) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        ts = float(value)
        if ts > 10**12:  # looks like milliseconds
            ts /= 1000.0
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            try:
                return datetime.fromtimestamp(float(value), tz=timezone.utc)
            except (TypeError, ValueError):
                return None
    return None


def _nearest_price(
    history_points: list[tuple[datetime, float]],
    target: datetime,
    tolerance_seconds: float = TOLERANCE_SECONDS,
) -> float | None:
    """Price of the history point closest to `target`, or None if the
    closest point is farther than `tolerance_seconds` away (or there are no
    points at all)."""
    if not history_points:
        return None
    best = min(history_points, key=lambda pt: abs((pt[0] - target).total_seconds()))
    if abs((best[0] - target).total_seconds()) > tolerance_seconds:
        return None
    return best[1]


def _extract_history_points(payload) -> list[tuple[datetime, float]]:
    """Normalize a /prices-history response into sorted (timestamp, price) tuples.

    Field names (`t`/`timestamp`/`time`, `p`/`price`) are guessed defensively
    since this hasn't been run against the live endpoint from this
    environment - see module docstring.
    """
    if isinstance(payload, dict):
        raw = payload.get("history") or payload.get("data") or []
    elif isinstance(payload, list):
        raw = payload
    else:
        raw = []

    points: list[tuple[datetime, float]] = []
    for point in raw:
        if not isinstance(point, dict):
            continue
        t = point.get("t") or point.get("timestamp") or point.get("time")
        p = point.get("p") if "p" in point else point.get("price")
        ts = _parse_ts(t)
        try:
            price = float(p) if p is not None else None
        except (TypeError, ValueError):
            price = None
        if ts is not None and price is not None:
            points.append((ts, price))

    points.sort(key=lambda pt: pt[0])
    return points


@dataclass
class TradeClvResult:
    entry_price: float
    entry_ts: datetime
    prices: dict[str, float | None]  # {"1h", "6h", "24h", "close"}
    clv: dict[str, float | None]
    missing: dict[str, bool]


def compute_trade_clv(
    token_id: str,
    side: str,
    entry_price: float,
    entry_ts: datetime,
    close_ts: datetime | None,
    fetch_history: PriceHistoryFetcher,
) -> TradeClvResult | None:
    """Compute side-adjusted CLV for a single trade.

    `fetch_history(token_id, start_ts_unix, end_ts_unix) -> raw API payload`
    is injected so this function is testable without hitting the network.
    Returns None if the trade isn't CLV-eligible or is missing required
    inputs (never raises for "just missing data" cases).
    """
    if not is_clv_eligible_side(side):
        return None
    if entry_price is None or entry_ts is None:
        return None

    horizon_targets = {name: entry_ts + timedelta(hours=h) for name, h in HORIZONS_HOURS.items()}
    close_target = close_ts

    window_ends = list(horizon_targets.values()) + ([close_target] if close_target else [])
    window_end = max(window_ends)
    start_unix = int(entry_ts.timestamp())
    end_unix = int((window_end + timedelta(hours=2)).timestamp())

    try:
        payload = fetch_history(token_id, start_unix, end_unix)
    except Exception as exc:
        logger.warning("prices-history fetch failed for token %s: %s", token_id, exc)
        payload = None

    points = _extract_history_points(payload) if payload is not None else []

    prices: dict[str, float | None] = {}
    missing: dict[str, bool] = {}

    for name, target in horizon_targets.items():
        price = _nearest_price(points, target)
        prices[name] = price
        missing[name] = price is None

    if close_target is not None:
        price_close = _nearest_price(points, close_target, tolerance_seconds=CLOSE_TOLERANCE_SECONDS)
        prices["close"] = price_close
        missing["close"] = price_close is None
    else:
        # We don't know when the market closed (e.g. end_date wasn't stored),
        # so we cannot compute a close-vs-entry comparison. Marked missing
        # rather than silently falling back to the 24h figure, since a
        # market that closes 3 days out is not comparable to one closing in
        # 25 hours.
        prices["close"] = None
        missing["close"] = True

    side_sign = 1.0 if (side or "").upper() == "BUY" else -1.0
    clv = {
        name: (side_sign * (p - entry_price) if p is not None else None) for name, p in prices.items()
    }

    return TradeClvResult(entry_price=entry_price, entry_ts=entry_ts, prices=prices, clv=clv, missing=missing)


def _default_fetch_history(client: PolymarketClient) -> PriceHistoryFetcher:
    def fetch(token_id: str, start_ts: int, end_ts: int):
        return client.get_prices_history(token_id, interval="1h", start_ts=start_ts, end_ts=end_ts)

    return fetch


def compute_and_store_wallet_clv(
    wallet: str,
    limit_trades: int = 300,
    fetch_history: PriceHistoryFetcher | None = None,
    engine: Engine | None = None,
) -> dict:
    """Compute CLV for a wallet's not-yet-scored BUY trades and persist it.

    Skips trades that already have a stored CLV row, so repeated runs are
    cheap and don't re-hit the price-history API for the same trade twice.
    """
    engine = engine or get_engine()
    if fetch_history is None:
        fetch_history = _default_fetch_history(PolymarketClient())

    with engine.begin() as conn:
        trades = conn.execute(
            text("""
                SELECT t.id, t.wallet, t.market_id, t.token_id, t.side, t.price, t.ts,
                       m.end_date
                FROM wallet_trades t
                LEFT JOIN markets m ON m.market_id = t.market_id
                WHERE lower(t.wallet) = lower(:wallet)
                  AND t.id NOT IN (
                      SELECT wallet_trade_id FROM wallet_trade_clv
                      WHERE wallet_trade_id IS NOT NULL
                  )
                ORDER BY t.ts DESC
                LIMIT :limit
            """),
            {"wallet": wallet, "limit": limit_trades},
        ).mappings().all()

    computed = 0
    skipped_ineligible = 0
    skipped_bad_data = 0

    with engine.begin() as conn:
        for t in trades:
            if not is_clv_eligible_side(t["side"]):
                skipped_ineligible += 1
                continue

            entry_ts = _parse_ts(t["ts"])
            try:
                entry_price = float(t["price"]) if t["price"] is not None else None
            except (TypeError, ValueError):
                entry_price = None

            if entry_ts is None or entry_price is None:
                skipped_bad_data += 1
                continue

            close_ts = _parse_ts(t["end_date"])

            result = compute_trade_clv(
                token_id=t["token_id"],
                side=t["side"],
                entry_price=entry_price,
                entry_ts=entry_ts,
                close_ts=close_ts,
                fetch_history=fetch_history,
            )
            if result is None:
                skipped_bad_data += 1
                continue

            conn.execute(
                text("""
                    INSERT INTO wallet_trade_clv (
                        wallet, wallet_trade_id, market_id, token_id, side,
                        entry_price, entry_ts, price_1h, price_6h, price_24h, price_close,
                        clv_1h, clv_6h, clv_24h, clv_close,
                        missing_1h, missing_6h, missing_24h, missing_close, notes
                    ) VALUES (
                        :wallet, :wallet_trade_id, :market_id, :token_id, :side,
                        :entry_price, :entry_ts, :price_1h, :price_6h, :price_24h, :price_close,
                        :clv_1h, :clv_6h, :clv_24h, :clv_close,
                        :missing_1h, :missing_6h, :missing_24h, :missing_close, :notes
                    )
                """),
                {
                    "wallet": wallet.lower(),
                    "wallet_trade_id": t["id"],
                    "market_id": t["market_id"],
                    "token_id": t["token_id"],
                    "side": t["side"],
                    "entry_price": result.entry_price,
                    "entry_ts": result.entry_ts.isoformat(),
                    "price_1h": result.prices["1h"],
                    "price_6h": result.prices["6h"],
                    "price_24h": result.prices["24h"],
                    "price_close": result.prices["close"],
                    "clv_1h": result.clv["1h"],
                    "clv_6h": result.clv["6h"],
                    "clv_24h": result.clv["24h"],
                    "clv_close": result.clv["close"],
                    "missing_1h": result.missing["1h"],
                    "missing_6h": result.missing["6h"],
                    "missing_24h": result.missing["24h"],
                    "missing_close": result.missing["close"],
                    "notes": None,
                },
            )
            computed += 1

    return {
        "wallet": wallet.lower(),
        "computed": computed,
        "skipped_ineligible_side": skipped_ineligible,
        "skipped_bad_data": skipped_bad_data,
    }


@dataclass
class WalletClvSummary:
    wallet: str
    sample_size_1h: int
    sample_size_24h: int
    sample_size_close: int
    avg_clv_1h: float | None
    avg_clv_24h: float | None
    avg_clv_close: float | None
    pct_positive_clv_24h: float | None
    data_note: str


def summarize_wallet_clv(wallet: str, engine: Engine | None = None) -> WalletClvSummary:
    engine = engine or get_engine()
    with engine.begin() as conn:
        rows = conn.execute(
            text("""
                SELECT clv_1h, clv_24h, clv_close, missing_1h, missing_24h, missing_close
                FROM wallet_trade_clv
                WHERE lower(wallet) = lower(:wallet)
            """),
            {"wallet": wallet},
        ).mappings().all()

    clv_1h_vals = [r["clv_1h"] for r in rows if not r["missing_1h"] and r["clv_1h"] is not None]
    clv_24h_vals = [r["clv_24h"] for r in rows if not r["missing_24h"] and r["clv_24h"] is not None]
    clv_close_vals = [r["clv_close"] for r in rows if not r["missing_close"] and r["clv_close"] is not None]

    def avg(values):
        return sum(values) / len(values) if values else None

    pct_positive_24h = None
    if clv_24h_vals:
        pct_positive_24h = sum(1 for v in clv_24h_vals if v > 0) / len(clv_24h_vals)

    if not rows:
        note = "no CLV data computed yet for this wallet (run compute_and_store_wallet_clv first)"
    elif not clv_24h_vals and not clv_close_vals:
        note = f"CLV attempted for {len(rows)} trades but price-history data was missing for all of them"
    else:
        note = (
            f"CLV based on {len(clv_24h_vals)}/{len(rows)} eligible trades with 24h data, "
            f"{len(clv_close_vals)}/{len(rows)} with close data"
        )

    return WalletClvSummary(
        wallet=wallet.lower(),
        sample_size_1h=len(clv_1h_vals),
        sample_size_24h=len(clv_24h_vals),
        sample_size_close=len(clv_close_vals),
        avg_clv_1h=avg(clv_1h_vals),
        avg_clv_24h=avg(clv_24h_vals),
        avg_clv_close=avg(clv_close_vals),
        pct_positive_clv_24h=pct_positive_24h,
        data_note=note,
    )
