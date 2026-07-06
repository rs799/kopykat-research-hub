from __future__ import annotations

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from .utils import clean_params
from polyalgo.config import get_settings


class PolymarketClient:
    def __init__(self, timeout: float = 20.0):
        self.settings = get_settings()
        self.http = httpx.Client(timeout=timeout, headers={"User-Agent": "polyalgo-framework/0.1"})

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=5))
    def _get(self, base: str, path: str, params: dict | None = None):
        url = base.rstrip("/") + "/" + path.lstrip("/")
        resp = self.http.get(url, params=clean_params(params or {}))
        resp.raise_for_status()
        return resp.json()

    def get_markets_keyset(
        self,
        limit: int = 100,
        next_cursor: str | None = None,
        closed: bool | None = False,
        active: bool | None = True,
        order: str | None = "volume_num,liquidity_num",
        ascending: bool = False,
    ):
        params = {
            "limit": limit,
            "next_cursor": next_cursor,
            "closed": str(closed).lower() if closed is not None else None,
            "active": str(active).lower() if active is not None else None,
            "order": order,
            "ascending": str(ascending).lower(),
        }
        return self._get(self.settings.polymarket_gamma_base, "/markets/keyset", params)

    def get_orderbook(self, token_id: str):
        return self._get(self.settings.polymarket_clob_base, "/book", {"token_id": token_id})

    def get_prices_history(
        self,
        token_id: str,
        interval: str = "1h",
        start_ts: int | None = None,
        end_ts: int | None = None,
    ):
        return self._get(
            self.settings.polymarket_clob_base,
            "/prices-history",
            {"market": token_id, "interval": interval, "startTs": start_ts, "endTs": end_ts},
        )

    def get_clob_market_info(self, condition_id: str):
        return self._get(self.settings.polymarket_clob_base, f"/clob-markets/{condition_id}")

    def get_wallet_trades(
        self,
        wallet: str,
        limit: int = 1000,
        offset: int = 0,
        taker_only: bool = True,
    ):
        return self._get(
            self.settings.polymarket_data_base,
            "/trades",
            {
                "user": wallet,
                "limit": limit,
                "offset": offset,
                "takerOnly": str(taker_only).lower(),
            },
        )

    def get_wallet_positions(self, wallet: str, limit: int = 500):
        return self._get(
            self.settings.polymarket_data_base,
            "/positions",
            {"user": wallet, "limit": limit},
        )

    def get_wallet_closed_positions(
        self,
        wallet: str,
        limit: int = 500,
        sort_by: str = "REALIZEDPNL",
        sort_direction: str = "DESC",
    ):
        return self._get(
            self.settings.polymarket_data_base,
            "/closed-positions",
            {
                "user": wallet,
                "limit": limit,
                "sortBy": sort_by,
                "sortDirection": sort_direction,
            },
        )

    def get_wallet_activity(
        self,
        wallet: str,
        limit: int = 500,
        offset: int = 0,
        activity_type: str | None = None,
    ):
        """Fetch a wallet's full on-chain activity feed (TRADE, SPLIT, MERGE,
        REDEEM, and possibly other types) from the Data API's /activity
        endpoint.

        UNVERIFIED AGAINST THE LIVE API: this build environment has no
        network egress to polymarket.com, so the endpoint path, param names,
        and response shape here are our best inference from the pattern used
        by /trades and /positions above, not confirmed against a real
        response. See ingest/activity.py for how the response is parsed
        defensively regardless.
        """
        return self._get(
            self.settings.polymarket_data_base,
            "/activity",
            {
                "user": wallet,
                "limit": limit,
                "offset": offset,
                "type": activity_type,
            },
        )

