from __future__ import annotations

"""
strategy/backtest.py is currently a skeleton - there is no real backtesting
engine producing ROI/drawdown/fill-rate numbers yet. Returning an empty list
rather than fabricated backtest results, per the hard rule against faking
backend results.
"""

from fastapi import APIRouter

from polyalgo.api.schemas import Backtest

router = APIRouter()


@router.get("/api/backtests", response_model=list[Backtest])
def list_backtests() -> list[Backtest]:
    # TODO: implement once strategy/backtest.py is a real engine
    # (CLAUDE_UPDATE_KOPYKAT_API_BRIDGE.md section 10, item 8).
    return []
