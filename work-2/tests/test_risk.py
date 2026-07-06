from polyalgo.strategy.risk import estimate_taker_fee, position_size


def test_fee_formula_positive():
    fee = estimate_taker_fee(shares=100, price=0.5, fee_rate=0.04)
    assert fee == 1.0


def test_position_size_zero_edge():
    assert position_size(1000, edge=0, loss_if_wrong=0.5, confidence=1, liquidity_multiplier=1, resolution_multiplier=1) == 0


def test_position_size_positive():
    size = position_size(1000, edge=0.05, loss_if_wrong=0.5, confidence=1, liquidity_multiplier=1, resolution_multiplier=1)
    assert size > 0

