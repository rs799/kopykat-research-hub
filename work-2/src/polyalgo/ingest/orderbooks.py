from __future__ import annotations

import json
from sqlalchemy import text
from polyalgo.clients.polymarket import PolymarketClient
from polyalgo.db import get_engine
from polyalgo.models import BookSummary


def _float_or_none(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def summarize_book(token_id: str, book: dict) -> BookSummary:
    bids = book.get("bids") or []
    asks = book.get("asks") or []

    def price_size(level):
        if isinstance(level, dict):
            return _float_or_none(level.get("price")), _float_or_none(level.get("size"))
        if isinstance(level, (list, tuple)) and len(level) >= 2:
            return _float_or_none(level[0]), _float_or_none(level[1])
        return None, None

    bid_levels = [(p, s) for p, s in (price_size(x) for x in bids) if p is not None and s is not None]
    ask_levels = [(p, s) for p, s in (price_size(x) for x in asks) if p is not None and s is not None]

    best_bid = max((p for p, _ in bid_levels), default=None)
    best_ask = min((p for p, _ in ask_levels), default=None)

    midpoint = None
    spread = None
    if best_bid is not None and best_ask is not None:
        midpoint = (best_bid + best_ask) / 2
        spread = best_ask - best_bid

    def depth_within(cents: float) -> float:
        if best_ask is None:
            return 0.0
        return sum(s for p, s in ask_levels if p <= best_ask + cents)

    return BookSummary(
        token_id=token_id,
        best_bid=best_bid,
        best_ask=best_ask,
        midpoint=midpoint,
        spread=spread,
        depth_1c=depth_within(0.01),
        depth_3c=depth_within(0.03),
        raw=book,
    )


def snapshot_books(limit: int = 20) -> int:
    client = PolymarketClient()
    engine = get_engine()

    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT market_id, condition_id, clob_token_ids
            FROM markets
            WHERE enable_orderbook = 1 AND active = 1 AND closed = 0
            LIMIT :limit
        """), {"limit": limit}).mappings().all()

        count = 0
        for row in rows:
            try:
                token_ids = json.loads(row["clob_token_ids"] or "[]")
            except json.JSONDecodeError:
                token_ids = []

            for token_id in token_ids:
                try:
                    book = client.get_orderbook(str(token_id))
                    summary = summarize_book(str(token_id), book)
                except Exception as exc:
                    print(f"Orderbook fetch failed for {token_id}: {exc}")
                    continue

                conn.execute(text("""
                    INSERT INTO orderbook_snapshots (
                        market_id, condition_id, token_id, best_bid, best_ask,
                        midpoint, spread, depth_1c, depth_3c, raw_json
                    )
                    VALUES (
                        :market_id, :condition_id, :token_id, :best_bid, :best_ask,
                        :midpoint, :spread, :depth_1c, :depth_3c, :raw_json
                    )
                """), {
                    "market_id": row["market_id"],
                    "condition_id": row["condition_id"],
                    "token_id": summary.token_id,
                    "best_bid": summary.best_bid,
                    "best_ask": summary.best_ask,
                    "midpoint": summary.midpoint,
                    "spread": summary.spread,
                    "depth_1c": summary.depth_1c,
                    "depth_3c": summary.depth_3c,
                    "raw_json": json.dumps(summary.raw),
                })
                count += 1

    return count

