from __future__ import annotations

import json
from sqlalchemy import text
from polyalgo.clients.polymarket import PolymarketClient
from polyalgo.db import get_engine


def _extract_token_ids(market: dict) -> list[str]:
    raw = market.get("clobTokenIds") or market.get("clob_token_ids") or "[]"
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return []
    else:
        parsed = raw
    return [str(x) for x in parsed] if isinstance(parsed, list) else []


def upsert_market(conn, market: dict) -> None:
    market_id = str(market.get("id") or market.get("marketId") or market.get("conditionId"))
    condition_id = market.get("conditionId") or market.get("condition_id")
    token_ids = _extract_token_ids(market)

    conn.execute(
        text("""
        INSERT OR REPLACE INTO markets (
            market_id, condition_id, question, slug, category, tags,
            outcomes, outcome_prices, clob_token_ids, enable_orderbook,
            active, closed, end_date, raw_json, updated_at
        )
        VALUES (
            :market_id, :condition_id, :question, :slug, :category, :tags,
            :outcomes, :outcome_prices, :clob_token_ids, :enable_orderbook,
            :active, :closed, :end_date, :raw_json, CURRENT_TIMESTAMP
        )
        """),
        {
            "market_id": market_id,
            "condition_id": condition_id,
            "question": market.get("question") or market.get("title") or "",
            "slug": market.get("slug"),
            "category": market.get("category"),
            "tags": json.dumps(market.get("tags", [])),
            "outcomes": json.dumps(market.get("outcomes")),
            "outcome_prices": json.dumps(market.get("outcomePrices") or market.get("outcome_prices")),
            "clob_token_ids": json.dumps(token_ids),
            "enable_orderbook": bool(market.get("enableOrderBook", False)),
            "active": bool(market.get("active", False)),
            "closed": bool(market.get("closed", False)),
            "end_date": market.get("endDate") or market.get("end_date_iso"),
            "raw_json": json.dumps(market),
        },
    )


def fetch_and_store_markets(limit: int = 100) -> int:
    client = PolymarketClient()
    payload = client.get_markets_keyset(limit=limit)
    markets = payload.get("data") if isinstance(payload, dict) else payload
    if markets is None:
        markets = payload.get("markets", []) if isinstance(payload, dict) else []

    engine = get_engine()
    count = 0
    with engine.begin() as conn:
        for market in markets:
            if isinstance(market, dict):
                upsert_market(conn, market)
                count += 1
    return count

