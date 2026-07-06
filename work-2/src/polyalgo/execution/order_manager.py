from __future__ import annotations

from polyalgo.config import get_settings


class OrderManager:
    """
    Live execution is intentionally disabled.

    Future live module requirements:
    - py-clob-client-v2,
    - isolated private keys,
    - dry-run mode,
    - risk engine before every order,
    - cancel/replace logic,
    - stale-data kill switch,
    - tiny limit orders only.
    """

    def place_order(self, *args, **kwargs):
        settings = get_settings()
        if settings.trading_mode != "live":
            raise RuntimeError("Live order placement disabled. Current mode is paper.")

        raise NotImplementedError(
            "Live CLOB execution intentionally not implemented in this starter framework."
        )

