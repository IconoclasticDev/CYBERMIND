from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from fastapi import WebSocket

from app.core.logging import log


class ConnectionHub:
    """Fan-out of typed live-feed messages to connected UI clients."""

    def __init__(self) -> None:
        self.clients: set[WebSocket] = set()
        self._loop: asyncio.AbstractEventLoop | None = None

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.clients.add(ws)
        self._loop = asyncio.get_running_loop()
        log.info("ws client connected (%d total)", len(self.clients))

    def disconnect(self, ws: WebSocket) -> None:
        self.clients.discard(ws)

    async def _send(self, ws: WebSocket, message: dict[str, Any]) -> None:
        try:
            await ws.send_text(json.dumps(message, default=str))
        except Exception:  # noqa: BLE001
            self.disconnect(ws)

    async def broadcast(self, message: dict[str, Any]) -> None:
        message = {**message, "ts": time.time()}
        for ws in list(self.clients):
            await self._send(ws, message)

    def broadcast_sync(self, message: dict[str, Any]) -> None:
        """Broadcast from sync context (routes run in threadpool workers)."""
        if not self.clients:
            return
        if self._loop is None or self._loop.is_closed():
            return
        asyncio.run_coroutine_threadsafe(self.broadcast(message), self._loop)


hub = ConnectionHub()
