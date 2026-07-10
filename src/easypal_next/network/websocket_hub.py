"""WebSocket event hub for mobile clients."""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, is_dataclass

from fastapi import WebSocket

from easypal_next.core.events import Event, EventBus


class WebSocketHub:
    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus
        self._clients: set[WebSocket] = set()
        self._queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=256)
        event_bus.bind_async_queue(self._queue)

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._clients.add(websocket)
        try:
            while True:
                await websocket.receive_text()
        finally:
            self._clients.discard(websocket)

    async def broadcast_loop(self) -> None:
        while True:
            event = await self._queue.get()
            message = json.dumps(_event_to_dict(event))
            dead: list[WebSocket] = []
            for client in self._clients:
                try:
                    await client.send_text(message)
                except Exception:
                    dead.append(client)
            for client in dead:
                self._clients.discard(client)


def _event_to_dict(event: Event) -> dict:
    if is_dataclass(event):
        data = asdict(event)
        data["type"] = type(event).__name__
        if "state" in data:
            data["state"] = str(data["state"])
        return data
    return {"type": type(event).__name__}
