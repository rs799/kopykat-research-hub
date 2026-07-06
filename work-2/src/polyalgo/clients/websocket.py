from __future__ import annotations

import asyncio
import json
import websockets


MARKET_WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"


async def listen_market(asset_ids: list[str], on_message):
    """
    Lightweight WebSocket skeleton.

    Production needs:
    - reconnect loop,
    - heartbeat/ping handling,
    - deduplication,
    - stale-feed kill switch,
    - message persistence.
    """
    async with websockets.connect(MARKET_WS_URL) as ws:
        await ws.send(json.dumps({
            "assets_ids": asset_ids,
            "type": "market",
            "custom_feature_enabled": True,
        }))

        async def heartbeat():
            while True:
                await asyncio.sleep(10)
                try:
                    await ws.send("PING")
                except Exception:
                    return

        asyncio.create_task(heartbeat())

        async for msg in ws:
            await on_message(json.loads(msg))

