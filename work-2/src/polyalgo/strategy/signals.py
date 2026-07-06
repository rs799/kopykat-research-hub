from __future__ import annotations

import json
from sqlalchemy import text
from polyalgo.config import get_settings
from polyalgo.db import get_engine
from polyalgo.models import Signal


def estimate_fee_usd(size_usd: float, price: float, fee_rate: float = 0.04) -> float:
    if price <= 0:
        return 0.0
    shares = size_usd / price
    return shares * fee_rate * price * (1 - price)


def generate_basic_wallet_signals(default_size_usd: float = 25.0) -> int:
    settings = get_settings()
    engine = get_engine()

    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT
                m.market_id,
                m.condition_id,
                b.token_id,
                b.best_ask,
                b.spread,
                b.depth_3c
            FROM markets m
            JOIN orderbook_snapshots b ON b.market_id = m.market_id
            WHERE m.active = 1
              AND m.closed = 0
              AND b.best_ask IS NOT NULL
              AND b.spread IS NOT NULL
            GROUP BY m.market_id, b.token_id
            ORDER BY b.ts DESC
            LIMIT 100
        """)).mappings().all()

        count = 0
        for row in rows:
            entry = float(row["best_ask"])
            spread = float(row["spread"])

            if spread > settings.max_spread:
                continue

            fair_probability = min(0.99, entry + 0.06)
            fee = estimate_fee_usd(default_size_usd, entry)
            slippage = default_size_usd * min(0.03, spread)
            gross_edge = fair_probability - entry
            net_edge = gross_edge - (fee / default_size_usd) - (slippage / default_size_usd)

            status = "candidate" if net_edge >= settings.min_net_edge else "rejected"
            reason = "basic placeholder signal" if status == "candidate" else "edge too low"

            conn.execute(text("""
                INSERT INTO signals (
                    market_id, condition_id, token_id, strategy, side,
                    fair_probability, entry_price, gross_edge, estimated_fee,
                    estimated_slippage, net_edge, confidence, size_usd,
                    status, reason, raw_json
                )
                VALUES (
                    :market_id, :condition_id, :token_id, :strategy, :side,
                    :fair_probability, :entry_price, :gross_edge, :estimated_fee,
                    :estimated_slippage, :net_edge, :confidence, :size_usd,
                    :status, :reason, :raw_json
                )
            """), {
                "market_id": row["market_id"],
                "condition_id": row["condition_id"],
                "token_id": row["token_id"],
                "strategy": "basic_wallet_model_placeholder",
                "side": "BUY",
                "fair_probability": fair_probability,
                "entry_price": entry,
                "gross_edge": gross_edge,
                "estimated_fee": fee,
                "estimated_slippage": slippage,
                "net_edge": net_edge,
                "confidence": 0.50,
                "size_usd": default_size_usd,
                "status": status,
                "reason": reason,
                "raw_json": json.dumps(dict(row)),
            })
            count += 1

    return count


def latest_candidate_signals(limit: int = 20) -> list[Signal]:
    engine = get_engine()
    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT *
            FROM signals
            WHERE status = 'candidate'
            ORDER BY ts DESC
            LIMIT :limit
        """), {"limit": limit}).mappings().all()

    return [
        Signal(
            market_id=r["market_id"],
            condition_id=r["condition_id"],
            token_id=r["token_id"],
            strategy=r["strategy"],
            side=r["side"],
            fair_probability=float(r["fair_probability"]),
            entry_price=float(r["entry_price"]),
            gross_edge=float(r["gross_edge"]),
            estimated_fee=float(r["estimated_fee"]),
            estimated_slippage=float(r["estimated_slippage"]),
            net_edge=float(r["net_edge"]),
            confidence=float(r["confidence"]),
            size_usd=float(r["size_usd"]),
            status=r["status"],
            reason=r["reason"],
        )
        for r in rows
    ]

