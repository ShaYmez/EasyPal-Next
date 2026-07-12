"""Async LAN web server."""

from __future__ import annotations

import asyncio
import socket
import subprocess
import threading
import time
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
        self._process: subprocess.Popen | None = None
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

    def _announce_ready(self) -> None:
        from easypal_next.network.util import gallery_urls

        _, lan_url = gallery_urls(self._config.port)
        if lan_url:
            self._event_bus.publish(
                LogEvent(
                    level="info",
                    message=f"LAN gallery ready for phone/tablet: {lan_url}",
                )
            )

    def start(self) -> None:
        """Start gallery HTTP in this process (safe for FreeDV / PortAudio)."""
        if not self._config.enabled or self._thread or self._process:
            return

        self._announce_ready()

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

    def start_subprocess(self) -> None:
        """Start gallery HTTP in a child process (required when HamDRM is loaded)."""
        if not self._config.enabled or self._thread or self._process:
            return

        from easypal_next.network.gallery_subprocess import spawn_gallery_server

        # Prior crashes can leave orphan gallery children holding the port.
        self._kill_orphan_gallery_children()
        self._announce_ready()
        try:
            self._process = spawn_gallery_server(
                host=self._config.host,
                port=self._config.port,
                gallery_dir=self._gallery.gallery_dir,
                received_dir=self._gallery.received_dir(),
                callsign=self._callsign,
                modem_mode=self._modem_mode,
            )
        except OSError as exc:
            self._process = None
            self._event_bus.publish(
                LogEvent(
                    level="error",
                    message=f"LAN gallery subprocess failed on port {self._config.port}: {exc}",
                )
            )
            return

        self._event_bus.publish(
            LogEvent(
                level="info",
                message=(
                    f"LAN gallery starting in subprocess on port {self._config.port} "
                    f"(pid {self._process.pid})"
                ),
            )
        )

    def _kill_orphan_gallery_children(self) -> None:
        """Best-effort cleanup of leftover ``gallery_subprocess`` processes."""
        import os
        import signal
        import sys

        me = os.getpid()
        # Prefer a CommandLine filter — listing every python.exe often returns
        # blank CommandLine columns on this Windows host.
        queries = [
            "CommandLine like '%gallery_subprocess%'",
            "Name='python.exe'",
            "Name='pythonw.exe'",
        ]
        lines: list[str] = []
        for where in queries:
            try:
                out = subprocess.check_output(
                    [
                        "wmic",
                        "process",
                        "where",
                        where,
                        "get",
                        "ProcessId,CommandLine",
                    ],
                    text=True,
                    stderr=subprocess.DEVNULL,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
                    if sys.platform == "win32"
                    else 0,
                )
                lines.extend(out.splitlines())
            except (OSError, subprocess.CalledProcessError):
                continue
        seen: set[int] = set()
        for line in lines:
            if "gallery_subprocess" not in line.lower():
                continue
            parts = line.strip().rsplit(None, 1)
            if len(parts) < 2 or not parts[-1].isdigit():
                continue
            pid = int(parts[-1])
            if pid == me or pid in seen:
                continue
            seen.add(pid)
            try:
                if sys.platform == "win32":
                    subprocess.run(
                        ["taskkill", "/F", "/PID", str(pid)],
                        capture_output=True,
                        check=False,
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    )
                else:
                    os.kill(pid, signal.SIGTERM)
            except OSError:
                pass
        time.sleep(0.4)

    def stop(self) -> None:
        proc = self._process
        self._process = None
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                proc.kill()
                try:
                    proc.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    pass
        self._kill_orphan_gallery_children()

    @property
    def is_running(self) -> bool:
        if self._process is not None and self._process.poll() is None:
            return True
        if self._thread is not None and self._thread.is_alive():
            return True
        return self._port_is_open()

    def _port_is_open(self) -> bool:
        if not self._config.enabled:
            return False
        try:
            with socket.create_connection(
                ("127.0.0.1", int(self._config.port)),
                timeout=0.2,
            ):
                return True
        except OSError:
            return False
