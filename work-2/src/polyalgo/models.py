from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class BookSummary:
    token_id: str
    best_bid: float | None
    best_ask: float | None
    midpoint: float | None
    spread: float | None
    depth_1c: float
    depth_3c: float
    raw: dict[str, Any]


@dataclass
class WalletScore:
    wallet: str
    total_trades: int  # NOTE: this is the RESOLVED trade count, not raw trade count
    sample_reliability: float
    roi_estimate: float
    shrunk_roi: float
    clv_score: float
    drawdown_score: float
    timing_score: float
    niche_score: float
    penalty: float
    final_score: float
    classification: str
    # Added for CLV + resolved-PnL scoring upgrade. Defaults keep this
    # backward compatible with any code still constructing the old shape.
    realized_pnl: float = 0.0
    realized_roi: float | None = None
    resolved_trade_count: int = 0
    unrealized_pnl: float = 0.0
    open_position_count: int = 0
    liquidity_score: float = 0.5
    recency_score: float = 0.5
    exit_quality_score: float = 0.5
    clv_sample_size: int = 0
    notes: str = ""
    component_json: str = "{}"


@dataclass
class Signal:
    market_id: str
    condition_id: str | None
    token_id: str
    strategy: str
    side: str
    fair_probability: float
    entry_price: float
    gross_edge: float
    estimated_fee: float
    estimated_slippage: float
    net_edge: float
    confidence: float
    size_usd: float
    status: str
    reason: str

