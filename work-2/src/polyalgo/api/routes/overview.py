from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.engine import Engine

from polyalgo.api.deps import get_engine_dependency
from polyalgo.api.schemas import Overview
from polyalgo.config import get_settings

router = APIRouter()


@router.get("/api/overview", response_model=Overview)
def get_overview(engine: Engine = Depends(get_engine_dependency)) -> Overview:
    settings = get_settings()

    with engine.begin() as conn:
        discovered_wallets = conn.execute(
            text("SELECT COUNT(*) AS n FROM wallet_scores")
        ).mappings().first()["n"]

        # "Qualified" here means our existing classification tier
        # (candidate_smart_wallet), computed globally rather than per-niche
        # since niche classification (per-niche wallet qualification) isn't
        # built yet - see routes/niches.py.
        qualified_wallets = conn.execute(
            text("SELECT COUNT(*) AS n FROM wallet_scores WHERE classification = 'candidate_smart_wallet'")
        ).mappings().first()["n"]

        parser_warnings = conn.execute(
            text("SELECT COUNT(*) AS n FROM wallet_activity_raw WHERE parsed_ok = 0")
        ).mappings().first()["n"]

        paper_pnl_row = conn.execute(
            text("""
                SELECT
                    COALESCE(SUM(realized_pnl), 0) AS realized,
                    COALESCE(SUM(unrealized_pnl), 0) AS unrealized
                FROM paper_positions
            """)
        ).mappings().first()
        paper_pnl = float(paper_pnl_row["realized"] or 0) + float(paper_pnl_row["unrealized"] or 0)

    return Overview(
        # Niche classification is not implemented yet (see routes/niches.py
        # TODO) - always 0 until that exists, not guessed.
        activeNiches=0,
        discoveredWallets=int(discovered_wallets),
        qualifiedWallets=int(qualified_wallets),
        # Consensus alert engine is not implemented yet - always 0.
        consensusAlerts=0,
        rejectedAlerts=0,
        paperPnl=paper_pnl,
        parserWarnings=int(parser_warnings),
        backendStatus="local",
        mode=f"{settings.trading_mode.upper()} ONLY",
    )
