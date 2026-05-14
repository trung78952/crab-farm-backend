from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket


class RealtimeService:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def broadcast(self, event: str, data: dict[str, Any] | None = None) -> None:
        payload = {
            "event": event,
            "data": data or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        stale: list[WebSocket] = []
        for websocket in list(self._connections):
            try:
                await websocket.send_json(payload)
            except Exception:
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(websocket)


realtime_service = RealtimeService()
