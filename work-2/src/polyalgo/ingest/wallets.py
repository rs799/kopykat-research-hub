from __future__ import annotations

import json
from sqlalchemy import text
from polyalgo.clients.polymarket import PolymarketClient
from polyalgo.db import get_engine


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def ingest_wallet(wallet: str) -> dict:
    client = PolymarketClient()
    trades = client.get_wallet_trades(wallet)
    positions = client.get_wallet_positions(wallet)

    trades_data = trades.get("data") if isinstance(trades, dict) else trades
    if trades_data is None and isinstance(trades, dict):
        trades_data = trades.get("trades")
    trades_data = trades_data or []

    positions_data = positions.get("data") if isinstance(positions, dict) else positions
    if positions_data is None and isinstance(positions, dict):
        positions_data = positions.get("positions")
    positions_data = positions_data or []

    engine = get_engine()
    with engine.begin() as conn:
        for t in trades_data:
            conn.execute(text("""
                INSERT INTO wallet_trades (
                    wallet, ts, market_id, condition_id, token_id, outcome,
                    side, price, size, usdc_size, tx_hash, raw_json
                )
                VALUES (
                    :wallet, :ts, :market_id, :condition_id, :token_id, :outcome,
                    :side, :price, :size, :usdc_size, :tx_hash, :raw_json
                )
            """), {
                "wallet": wallet.lower(),
                "ts": t.get("timestamp") or t.get("createdAt") or t.get("time"),
                "market_id": str(t.get("market") or t.get("marketId") or ""),
                "condition_id": t.get("conditionId"),
                "token_id": str(t.get("asset") or t.get("assetId") or t.get("tokenId") or ""),
                "outcome": t.get("outcome"),
                "side": t.get("side"),
                "price": _to_float(t.get("price")),
                "size": _to_float(t.get("size")),
                "usdc_size": _to_float(t.get("usdcSize") or t.get("amount")),
                "tx_hash": t.get("transactionHash") or t.get("txHash"),
                "raw_json": json.dumps(t),
            })

        for p in positions_data:
            conn.execute(text("""
                INSERT INTO wallet_positions (
                    wallet, market_id, condition_id, token_id, outcome,
                    size, avg_price, cur_price, cash_pnl, percent_pnl, raw_json
                )
                VALUES (
                    :wallet, :market_id, :condition_id, :token_id, :outcome,
                    :size, :avg_price, :cur_price, :cash_pnl, :percent_pnl, :raw_json
                )
            """), {
                "wallet": wallet.lower(),
                "market_id": str(p.get("market") or p.get("marketId") or ""),
                "condition_id": p.get("conditionId"),
                "token_id": str(p.get("asset") or p.get("assetId") or p.get("tokenId") or ""),
                "outcome": p.get("outcome"),
                "size": _to_float(p.get("size") or p.get("quantity")),
                "avg_price": _to_float(p.get("avgPrice")),
                "cur_price": _to_float(p.get("curPrice")),
                "cash_pnl": _to_float(p.get("cashPnl")),
                "percent_pnl": _to_float(p.get("percentPnl")),
                "raw_json": json.dumps(p),
            })

    return {"wallet": wallet, "trades": len(trades_data), "positions": len(positions_data)}

