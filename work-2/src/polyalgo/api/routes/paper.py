from __future__ import annotations

"""
Paper-simulation summary, built from the existing paper_orders/paper_positions
tables (see strategy/paper.py). This is real data whenever paper-execute has
been run - it is never live money, per the project's hard rules.

`balance` has no real value yet: there is no persisted starting-bankroll
concept in the schema (paper-execute takes --bankroll as a one-off CLI
argument, not something stored). Returned as 0 with a TODO rather than
guessed.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.engine import Engine

from polyalgo.api.deps import get_engine_dependency
from polyalgo.api.schemas import PaperOrder, PaperPosition, PaperSimulation

router = APIRouter()


@router.get("/api/paper-simulation", response_model=PaperSimulation)
def get_paper_simulation(engine: Engine = Depends(get_engine_dependency)) -> PaperSimulation:
    with engine.begin() as conn:
        pnl_row = conn.execute(
            text("""
                SELECT
                    COALESCE(SUM(realized_pnl), 0) AS realized,
                    COALESCE(SUM(unrealized_pnl), 0) AS unrealized,
                    SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) AS open_count,
                    SUM(CASE WHEN status = 'closed' AND realized_pnl > 0 THEN 1 ELSE 0 END) AS wins,
                    SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END) AS closed_count
                FROM paper_positions
            """)
        ).mappings().first()

        status_counts = {
            r["status"]: r["n"]
            for r in conn.execute(
                text("SELECT status, COUNT(*) AS n FROM paper_orders GROUP BY status")
            ).mappings().all()
        }

        order_rows = conn.execute(
            text("""
                SELECT id, ts, market_id, side, fill_price, limit_price,
                       filled_size_usd, requested_size_usd, status, signal_id
                FROM paper_orders
                ORDER BY ts DESC
                LIMIT 200
            """)
        ).mappings().all()

        position_rows = conn.execute(
            text("""
                SELECT market_id, side, avg_entry, shares, mark_price, unrealized_pnl, status
                FROM paper_positions
                WHERE status = 'open'
                ORDER BY opened_at DESC
                LIMIT 200
            """)
        ).mappings().all()

    total_orders = sum(status_counts.values())
    filled = status_counts.get("filled", 0)
    missed = status_counts.get("missed", 0)
    fill_rate = (filled / total_orders) if total_orders else None
    missed_rate = (missed / total_orders) if total_orders else None

    closed_count = int(pnl_row["closed_count"] or 0)
    win_rate = (int(pnl_row["wins"] or 0) / closed_count) if closed_count else None

    orders = [
        PaperOrder(
            id=str(r["id"]),
            time=str(r["ts"]) if r["ts"] else "",
            market=r["market_id"] or "",
            side=r["side"] or "",
            price=float(r["fill_price"] if r["fill_price"] is not None else (r["limit_price"] or 0)),
            size=float(r["filled_size_usd"] if r["filled_size_usd"] is not None else (r["requested_size_usd"] or 0)),
            status=r["status"] if r["status"] in ("filled", "partial", "missed") else "missed",
            linkedAlert=str(r["signal_id"]) if r["signal_id"] is not None else None,
        )
        for r in order_rows
    ]

    positions = [
        PaperPosition(
            market=r["market_id"] or "",
            side=r["side"] or "",
            avgPrice=float(r["avg_entry"] or 0),
            size=float(r["shares"] or 0),
            markPrice=float(r["mark_price"]) if r["mark_price"] is not None else None,
            unrealized=float(r["unrealized_pnl"]) if r["unrealized_pnl"] is not None else None,
        )
        for r in position_rows
    ]

    return PaperSimulation(
        # TODO: no persisted starting-bankroll concept exists yet.
        balance=0.0,
        openPositions=int(pnl_row["open_count"] or 0),
        realizedPnl=float(pnl_row["realized"] or 0),
        unrealizedPnl=float(pnl_row["unrealized"] or 0),
        winRate=win_rate,
        # TODO: max drawdown over the paper equity curve isn't computed yet.
        maxDrawdown=None,
        fillRate=fill_rate,
        missedFillRate=missed_rate,
        orders=orders,
        positions=positions,
    )
