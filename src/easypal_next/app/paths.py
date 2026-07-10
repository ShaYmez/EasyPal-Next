"""Frozen vs development path resolution."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def app_root() -> Path:
    """Install directory containing the main executable."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parents[3]


def package_root() -> Path:
    """Source package root (easypal_next/)."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", app_root()))
    return Path(__file__).resolve().parents[1]


def user_data_dir() -> Path:
    """Per-user writable data directory."""
    base = os.environ.get("APPDATA") or os.environ.get("HOME") or "~"
    path = Path(base).expanduser() / "EasyPal-Next"
    path.mkdir(parents=True, exist_ok=True)
    return path


def user_config_path() -> Path:
    return user_data_dir() / "config.yaml"


def user_gallery_dir() -> Path:
    path = user_data_dir() / "gallery"
    path.mkdir(parents=True, exist_ok=True)
    return path


def user_logs_dir() -> Path:
    path = user_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def bundled_defaults_path() -> Path:
    return app_root() / "config" / "defaults.yaml"


def bundled_libcodec2_path() -> Path:
    return app_root() / "libcodec2.dll"


def dev_redist_libcodec2_path() -> Path:
    return app_root() / "packaging" / "windows" / "redist" / "libcodec2.dll"


def resolve_libcodec2(configured: str | None) -> Path | None:
    if configured:
        path = Path(configured).expanduser()
        if path.is_file():
            return path
    for candidate in (
        bundled_libcodec2_path(),
        dev_redist_libcodec2_path(),
        app_root() / "libcodec2.so",
    ):
        if candidate.is_file():
            return candidate
    return None
