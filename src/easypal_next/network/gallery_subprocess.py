"""LAN gallery HTTP server as a child process (safe beside HamDRM WinMM).

In-process uvicorn + hamdrm.dll segfaults on Windows; the desktop app starts
this module via ``python -m easypal_next.network.gallery_subprocess``.

If the parent process segfaults, this child can be left running (orphan) and
hold the gallery port until killed. ``NetworkServer.stop`` / start cleanup
best-effort taskkill orphans; a parent crash may still leave one behind.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from easypal_next.network.api.routes import create_router
from easypal_next.network.gallery_store import GalleryStore


def spawn_gallery_server(
    *,
    host: str,
    port: int,
    gallery_dir: Path,
    callsign: str,
    modem_mode: str,
    received_dir: Path | None = None,
) -> subprocess.Popen:
    """Launch the gallery HTTP server in a separate Python process."""
    cmd = [
        sys.executable,
        "-m",
        "easypal_next.network.gallery_subprocess",
        "--host",
        host,
        "--port",
        str(port),
        "--gallery-dir",
        str(Path(gallery_dir).resolve()),
        "--callsign",
        callsign,
        "--modem-mode",
        modem_mode,
    ]
    if received_dir is not None:
        cmd.extend(["--received-dir", str(Path(received_dir).resolve())])

    kwargs: dict = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if sys.platform == "win32":
        # Avoid a console flash; keep the child attached to the app job for cleanup.
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    return subprocess.Popen(cmd, **kwargs)


class _IdleProgress:
    pct: float = 0.0
    bytes_done: int = 0
    bytes_total: int = 0


def build_gallery_app(
    *,
    gallery_dir: Path,
    received_dir: Path | None,
    callsign: str,
    modem_mode: str,
) -> FastAPI:
    gallery = GalleryStore(
        gallery_dir,
        received_dir=received_dir,
        reload_from_disk=True,
    )
    app = FastAPI(title="EasyPal-Next Gallery", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
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
        return {"message": "EasyPal-Next LAN gallery"}

    idle = _IdleProgress()
    router = create_router(
        gallery,
        get_state=lambda: ("IDLE", callsign, modem_mode),
        get_progress=lambda: idle,
        abort_transfer=lambda: None,
    )
    app.include_router(router)
    return app


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="EasyPal-Next LAN gallery subprocess")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--gallery-dir", required=True)
    parser.add_argument("--received-dir", default="")
    parser.add_argument("--callsign", default="N0CALL")
    parser.add_argument("--modem-mode", default="hamdrm")
    args = parser.parse_args(argv)

    gallery_dir = Path(args.gallery_dir).expanduser()
    received = Path(args.received_dir).expanduser() if args.received_dir else None
    app = build_gallery_app(
        gallery_dir=gallery_dir,
        received_dir=received,
        callsign=args.callsign,
        modem_mode=args.modem_mode,
    )
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
