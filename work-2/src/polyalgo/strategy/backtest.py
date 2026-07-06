from __future__ import annotations


class BacktestEngine:
    """
    Backtest placeholder.

    Required before live trading:
    - historical book replay,
    - bid/ask fills,
    - wallet-signal delay,
    - partial fills,
    - fee model,
    - slippage,
    - resolution outcomes,
    - CLV measurement.
    """

    def run(self):
        raise NotImplementedError(
            "Backtest engine scaffold only. Implement event-time replay before using live capital."
        )

