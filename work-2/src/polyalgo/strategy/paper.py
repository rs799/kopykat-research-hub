from __future__ import annotations

from sqlalchemy import text
from polyalgo.db import get_engine
from polyalgo.strategy.risk import check_signal_risk
from polyalgo.strategy.signals import latest_candidate_signals


class PaperBroker:
    def __init__(self, bankroll: float = 1000.0):
        self.bankroll = bankroll

    def execute_latest(self, limit: int = 20) -> int:
        engine = get_engine()
        signals = latest_candidate_signals(limit=limit)
        executed = 0

        with engine.begin() as conn:
            for signal in signals:
                decision = check_signal_risk(signal, bankroll=self.bankroll)
                status = "filled" if decision.allowed else "rejected"

                fill_price = signal.entry_price if decision.allowed else None
                filled_size = decision.size_usd if decision.allowed else 0.0

                conn.execute(text("""
                    INSERT INTO paper_orders (
                        signal_id, market_id, token_id, side, limit_price,
                        requested_size_usd, fill_price, filled_size_usd,
                        status, reason
                    )
                    VALUES (
                        NULL, :market_id, :token_id, :side, :limit_price,
                        :requested_size_usd, :fill_price, :filled_size_usd,
                        :status, :reason
                    )
                """), {
                    "market_id": signal.market_id,
                    "token_id": signal.token_id,
                    "side": signal.side,
                    "limit_price": signal.entry_price,
                    "requested_size_usd": signal.size_usd,
                    "fill_price": fill_price,
                    "filled_size_usd": filled_size,
                    "status": status,
                    "reason": decision.reason,
                })

                if decision.allowed:
                    shares = filled_size / fill_price if fill_price else 0.0
                    conn.execute(text("""
                        INSERT INTO paper_positions (
                            market_id, token_id, side, shares,
                            avg_entry, mark_price, realized_pnl,
                            unrealized_pnl, status
                        )
                        VALUES (
                            :market_id, :token_id, :side, :shares,
                            :avg_entry, :mark_price, 0, 0, 'open'
                        )
                    """), {
                        "market_id": signal.market_id,
                        "token_id": signal.token_id,
                        "side": signal.side,
                        "shares": shares,
                        "avg_entry": fill_price,
                        "mark_price": fill_price,
                    })
                    executed += 1

        return executed

