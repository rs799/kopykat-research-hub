from __future__ import annotations

"""
Ingestion of resolved/closed positions from the Polymarket Data API.

Why this file exists
---------------------
`ingest/wallets.py` stores whatever the Data API's `/positions` endpoint
returns *right now* for a wallet. That includes open, unresolved positions
where PnL is mark-to-market and can fully reverse before the market settles.
Treating that PnL as evidence of skill is exactly the mistake this project
is trying to avoid.

`/closed-positions` is the Data API endpoint for positions that have
actually settled. Realized PnL from a resolved market is much stronger
evidence, because no further mark-to-market reversal is possible. This
module ingests that endpoint into its own table (`wallet_closed_positions`),
kept completely separate from `wallet_positions`.

KNOWN API UNCERTAINTY - READ BEFORE TRUSTING THE FIELD MAPPING BELOW
---------------------------------------------------------------------
This build environment has no network egress to polymarket.com, so none of
the code in this repo (old or new) has been run against the live Data API.
The field-name mapping below is written defensively against several
plausible key names (matching the pattern already used in
`ingest/wallets.py`) and falls back to NULL + a logged/returned note when a
field can't be found under any of the candidate keys, instead of guessing a
value.

Before trusting this for scoring decisions with real money on the line:
  1. Run `ingest_closed_positions()` once against a wallet with known
     trading history.
  2. Manually diff the stored `raw_json` column against the parsed columns
     in `wallet_closed_positions`.
  3. Update the candidate key lists in `_first(...)` calls below if the API
     uses different field names than assumed here.
"""

import json
import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from polyalgo.clients.polymarket import PolymarketClient
from polyalgo.db import get_engine

logger = logging.getLogger(__name__)


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _first(d: dict, *keys):
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return None


def _extract_closed_positions(payload) -> list[dict]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("data", "positions", "closedPositions", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return []


def parse_closed_position(wallet: str, p: dict) -> dict:
    """Map one Data API closed-position record onto our storage schema.

    Every field is looked up defensively across several candidate key names.
    If a field is missing under all of them we store NULL rather than
    guessing - a missing realized_pnl must never be silently treated as 0,
    since that would make a wallet with genuinely unknown performance look
    like a break-even wallet.
    """
    size = _to_float(_first(p, "size", "quantity", "shares"))
    avg_price = _to_float(_first(p, "avgPrice", "averagePrice", "avg_price"))
    realized_pnl = _to_float(_first(p, "realizedPnl", "realizedPnL", "cashPnl", "pnl"))
    realized_pnl_pct = _to_float(
        _first(p, "realizedPnlPct", "realizedPercentPnl", "percentPnl", "percentRealizedPnl")
    )
    resolved_price = _to_float(_first(p, "curPrice", "resolvedPrice", "settlementPrice"))
    closed_ts = _first(p, "closedAt", "resolvedAt", "endDate", "timestamp")

    missing_fields = [
        name
        for name, value in [("size", size), ("avg_price", avg_price), ("realized_pnl", realized_pnl)]
        if value is None
    ]
    if missing_fields:
        logger.warning(
            "closed position for %s is missing expected fields: %s (raw keys: %s)",
            wallet,
            missing_fields,
            sorted(p.keys()),
        )

    return {
        "wallet": wallet.lower(),
        "market_id": str(_first(p, "market", "marketId") or ""),
        "condition_id": _first(p, "conditionId", "condition_id"),
        "token_id": str(_first(p, "asset", "assetId", "tokenId") or ""),
        "outcome": _first(p, "outcome"),
        "size": size,
        "avg_price": avg_price,
        "realized_pnl": realized_pnl,
        "realized_pnl_pct": realized_pnl_pct,
        "resolved_price": resolved_price,
        "closed_ts": closed_ts,
        "raw_json": json.dumps(p),
        "_missing_fields": missing_fields,
    }


def ingest_closed_positions(wallet: str, limit: int = 500, engine: Engine | None = None) -> dict:
    """Fetch and store resolved/closed positions for one wallet.

    Does NOT touch `wallet_positions` (open/unrealized). Realized and
    unrealized PnL are kept in separate tables on purpose so scoring code
    can never accidentally mix them.

    The Data API's closed-positions endpoint doesn't give us a cheap
    "since last sync" cursor, so each call re-fetches and replaces this
    wallet's rows wholesale rather than trying to diff/append.
    """
    client = PolymarketClient()

    try:
        payload = client.get_wallet_closed_positions(wallet, limit=limit)
    except Exception as exc:
        logger.error("closed-positions fetch failed for %s: %s", wallet, exc)
        return {"wallet": wallet.lower(), "closed_positions": 0, "error": str(exc)}

    raw_positions = _extract_closed_positions(payload)
    rows = [parse_closed_position(wallet, p) for p in raw_positions if isinstance(p, dict)]

    engine = engine or get_engine()
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM wallet_closed_positions WHERE lower(wallet) = lower(:wallet)"),
            {"wallet": wallet},
        )
        for row in rows:
            conn.execute(
                text("""
                    INSERT INTO wallet_closed_positions (
                        wallet, market_id, condition_id, token_id, outcome,
                        size, avg_price, realized_pnl, realized_pnl_pct,
                        resolved_price, closed_ts, raw_json
                    ) VALUES (
                        :wallet, :market_id, :condition_id, :token_id, :outcome,
                        :size, :avg_price, :realized_pnl, :realized_pnl_pct,
                        :resolved_price, :closed_ts, :raw_json
                    )
                """),
                {k: v for k, v in row.items() if not k.startswith("_")},
            )

    missing_pnl = sum(1 for r in rows if r["realized_pnl"] is None)
    return {
        "wallet": wallet.lower(),
        "closed_positions": len(rows),
        "missing_realized_pnl": missing_pnl,
    }
