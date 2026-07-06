from __future__ import annotations

"""
Realized ("resolved-market") PnL statistics for a wallet.

Kept strictly separate from unrealized/open-position PnL. A wallet sitting
on a large *unrealized* gain in a market that hasn't resolved yet has not
demonstrated anything - the position can (and often does) round-trip
partway or all the way to zero before it settles. Only resolved positions
(`wallet_closed_positions`, populated by `ingest/closed_positions.py`) count
as evidence for wallet scoring.

`compute_unrealized_pnl_stats` still exists here so the dashboard can show
unrealized PnL for context, but nothing in `scoring/wallets.py` should ever
add it into a score.
"""

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.engine import Engine

from polyalgo.db import get_engine


@dataclass
class ResolvedPnlStats:
    wallet: str
    resolved_trade_count: int
    total_realized_pnl: float
    total_realized_cost_basis: float
    realized_roi: float | None
    win_count: int
    loss_count: int
    win_rate: float | None
    missing_pnl_count: int
    data_note: str


def compute_resolved_pnl_stats(wallet: str, engine: Engine | None = None) -> ResolvedPnlStats:
    engine = engine or get_engine()
    with engine.begin() as conn:
        rows = conn.execute(
            text("""
                SELECT size, avg_price, realized_pnl
                FROM wallet_closed_positions
                WHERE lower(wallet) = lower(:wallet)
            """),
            {"wallet": wallet},
        ).mappings().all()

    missing_pnl_count = sum(1 for r in rows if r["realized_pnl"] is None)
    usable = [r for r in rows if r["realized_pnl"] is not None]

    total_realized_pnl = sum(float(r["realized_pnl"]) for r in usable)

    cost_basis_values = []
    for r in usable:
        size, avg_price = r["size"], r["avg_price"]
        if size is not None and avg_price is not None:
            cost_basis_values.append(abs(float(size) * float(avg_price)))
    total_cost_basis = sum(cost_basis_values)

    realized_roi = (total_realized_pnl / total_cost_basis) if total_cost_basis > 0 else None

    win_count = sum(1 for r in usable if float(r["realized_pnl"]) > 0)
    loss_count = sum(1 for r in usable if float(r["realized_pnl"]) < 0)
    win_rate = (win_count / len(usable)) if usable else None

    if not rows:
        note = "no closed positions ingested yet (run ingest_closed_positions first)"
    elif missing_pnl_count == len(rows):
        note = "closed positions exist but realized_pnl was missing from the API for all of them"
    elif total_cost_basis == 0:
        note = "realized_pnl available but cost basis (size * avg_price) could not be computed - ROI unavailable"
    else:
        note = f"based on {len(usable)}/{len(rows)} resolved positions with usable data"

    return ResolvedPnlStats(
        wallet=wallet.lower(),
        resolved_trade_count=len(rows),
        total_realized_pnl=total_realized_pnl,
        total_realized_cost_basis=total_cost_basis,
        realized_roi=realized_roi,
        win_count=win_count,
        loss_count=loss_count,
        win_rate=win_rate,
        missing_pnl_count=missing_pnl_count,
        data_note=note,
    )


@dataclass
class UnrealizedPnlStats:
    """Open-position PnL, for display only. Never fed into wallet scoring."""

    wallet: str
    open_position_count: int
    total_unrealized_pnl: float


def compute_unrealized_pnl_stats(wallet: str, engine: Engine | None = None) -> UnrealizedPnlStats:
    engine = engine or get_engine()
    with engine.begin() as conn:
        rows = conn.execute(
            text("""
                SELECT cash_pnl
                FROM wallet_positions
                WHERE lower(wallet) = lower(:wallet)
            """),
            {"wallet": wallet},
        ).mappings().all()

    values = [float(r["cash_pnl"]) for r in rows if r["cash_pnl"] is not None]
    return UnrealizedPnlStats(
        wallet=wallet.lower(),
        open_position_count=len(rows),
        total_unrealized_pnl=sum(values),
    )
