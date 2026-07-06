from __future__ import annotations

from dataclasses import dataclass
from polyalgo.config import get_settings
from polyalgo.models import Signal


@dataclass
class RiskDecision:
    allowed: bool
    size_usd: float
    reason: str


def estimate_taker_fee(shares: float, price: float, fee_rate: float) -> float:
    return shares * fee_rate * price * (1 - price)


def position_size(
    bankroll: float,
    edge: float,
    loss_if_wrong: float,
    confidence: float,
    liquidity_multiplier: float,
    resolution_multiplier: float,
    fractional_kelly: float = 0.15,
) -> float:
    if loss_if_wrong <= 0 or edge <= 0:
        return 0.0
    raw_kelly = edge / loss_if_wrong
    size = bankroll * raw_kelly * fractional_kelly
    size *= max(0.0, min(1.0, confidence))
    size *= max(0.0, min(1.0, liquidity_multiplier))
    size *= max(0.0, min(1.0, resolution_multiplier))
    return max(0.0, size)


def check_signal_risk(signal: Signal, bankroll: float = 1000.0) -> RiskDecision:
    settings = get_settings()

    if signal.net_edge < settings.min_net_edge:
        return RiskDecision(False, 0.0, f"net edge below threshold: {signal.net_edge:.4f}")

    if signal.entry_price <= 0 or signal.entry_price >= 1:
        return RiskDecision(False, 0.0, "invalid entry price")

    max_trade = bankroll * settings.max_risk_per_trade
    requested = min(signal.size_usd, max_trade)

    if requested <= 0:
        return RiskDecision(False, 0.0, "zero size")

    return RiskDecision(True, requested, "allowed")

