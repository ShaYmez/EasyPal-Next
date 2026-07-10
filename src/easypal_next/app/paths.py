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
    """Bundled resources root (PyInstaller _MEIPASS or source easypal_next/)."""
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        internal = app_root() / "_internal"
        if internal.is_dir():
            return internal
        return app_root()
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
    if getattr(sys, "frozen", False):
        return package_root() / "config" / "defaults.yaml"
    return app_root() / "config" / "defaults.yaml"


def _frozen_libcodec2_candidates() -> list[Path]:
    root = app_root()
    pkg = package_root()
    return [
        pkg / "libcodec2.dll",
        root / "_internal" / "libcodec2.dll",
        root / "libcodec2.dll",
    ]


def bundled_libcodec2_path() -> Path:
    """Preferred libcodec2 location for the current runtime layout."""
    if getattr(sys, "frozen", False):
        for candidate in _frozen_libcodec2_candidates():
            if candidate.is_file():
                return candidate
        return _frozen_libcodec2_candidates()[0]
    return app_root() / "libcodec2.dll"


def dev_redist_libcodec2_path() -> Path:
    return app_root() / "packaging" / "windows" / "redist" / "libcodec2.dll"


def native_library_dirs() -> list[Path]:
    """Directories that may contain native DLL dependencies."""
    dirs: list[Path] = []
    if getattr(sys, "frozen", False):
        dirs.append(package_root())
        internal = app_root() / "_internal"
        if internal.is_dir():
            dirs.append(internal)
    else:
        redist = dev_redist_libcodec2_path().parent
        if redist.is_dir():
            dirs.append(redist)
    unique: list[Path] = []
    for path in dirs:
        if path.is_dir() and path not in unique:
            unique.append(path)
    return unique


def init_native_library_dirs() -> None:
    """Register Windows DLL search paths before loading libcodec2."""
    if not hasattr(os, "add_dll_directory"):
        return
    for directory in native_library_dirs():
        os.add_dll_directory(str(directory))


def brand_dir() -> Path:
    """Project brand assets (icons, logos)."""
    candidates = [
        app_root() / "resources" / "brand",
        package_root() / "resources" / "brand",
        package_root() / "network" / "static" / "brand",
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return app_root() / "resources" / "brand"


def brand_icon_path() -> Path:
    icon = brand_dir() / "easypal-next-icon.png"
    if icon.is_file():
        return icon
    fallback = brand_dir() / "icon.png"
    return fallback if fallback.is_file() else icon


def brand_logo_path() -> Path:
    logo = brand_dir() / "easypal-next-logo.png"
    if logo.is_file():
        return logo
    fallback = brand_dir() / "logo.png"
    return fallback if fallback.is_file() else logo


def resolve_libcodec2(configured: str | None) -> Path | None:
    if configured:
        path = Path(configured).expanduser()
        if path.is_file():
            return path
    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        candidates.extend(_frozen_libcodec2_candidates())
    else:
        candidates.extend(
            [
                dev_redist_libcodec2_path(),
                bundled_libcodec2_path(),
                app_root() / "libcodec2.so",
            ]
        )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None
