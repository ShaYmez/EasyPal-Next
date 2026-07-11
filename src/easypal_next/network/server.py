"""Async LAN web server."""

from __future__ import annotations

import asyncio
import threading
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from easypal_next.config.schema import NetworkConfig
from easypal_next.core.events import EventBus, LogEvent
from easypal_next.core.transfer_engine import TransferEngine
from easypal_next.network.api.routes import create_router
from easypal_next.network.gallery_store import GalleryStore
from easypal_next.network.websocket_hub import WebSocketHub


class NetworkServer:
    def __init__(
        self,
        config: NetworkConfig,
        event_bus: EventBus,
        transfer_engine: TransferEngine,
        gallery: GalleryStore,
        callsign: str,
        modem_mode: str,
    ) -> None:
        self._config = config
        self._event_bus = event_bus
        self._transfer_engine = transfer_engine
        self._gallery = gallery
        self._callsign = callsign
        self._modem_mode = modem_mode
        self._thread: threading.Thread | None = None
        self._hub = WebSocketHub(event_bus)
        self._app = self._build_app()

    def _build_app(self) -> FastAPI:
        app = FastAPI(title="EasyPal-Next", version="0.1.0")
        app.add_middleware(
            CORSMiddleware,
            allow_origins=self._config.cors_origins,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        static_dir = Path(__file__).resolve().parent / "static"
        if static_dir.is_dir():
            app.mount("/static", StaticFiles(directory=static_dir), name="static")

        @app.get("/")
        def index():
            index_path = static_dir / "index.html"
            if index_path.is_file():
                return FileResponse(index_path)
            return {"message": "EasyPal-Next LAN server running"}

        router = create_router(
            self._gallery,
            get_state=lambda: (
                self._transfer_engine.state.value,
                self._callsign,
                self._modem_mode,
            ),
            get_progress=lambda: self._transfer_engine.get_progress(),
            abort_transfer=self._transfer_engine.abort,
        )
        app.include_router(router)

        @app.websocket("/ws/v1/events")
        async def events_socket(websocket: WebSocket):
            await self._hub.connect(websocket)

        @app.on_event("startup")
        async def startup():
            asyncio.create_task(self._hub.broadcast_loop())

        return app

    def start(self) -> None:
        if not self._config.enabled or self._thread:
            return

        from easypal_next.network.util import gallery_urls

        _, lan_url = gallery_urls(self._config.port)
        if lan_url:
            self._event_bus.publish(
                LogEvent(
                    level="info",
                    message=f"LAN gallery ready for phone/tablet: {lan_url}",
                )
            )

        def run() -> None:
            try:
                uvicorn.run(
                    self._app,
                    host=self._config.host,
                    port=self._config.port,
                    log_level="warning",
                )
            except OSError as exc:
                self._event_bus.publish(
                    LogEvent(
                        level="error",
                        message=f"LAN gallery server failed on port {self._config.port}: {exc}",
                    )
                )

        self._thread = threading.Thread(target=run, name="easypal-network", daemon=True)
        self._thread.start()
        self._event_bus.publish(
            LogEvent(
                level="info",
                message=f"LAN gallery starting on port {self._config.port}",
            )
        )
