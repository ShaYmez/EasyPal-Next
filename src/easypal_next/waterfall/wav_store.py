"""Manage begin.wav / end.wav waterfall presets."""

from __future__ import annotations

from pathlib import Path

from easypal_next.app.paths import user_data_dir


class WavPresetStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._base = base_dir or (user_data_dir() / "waterfall")
        self._base.mkdir(parents=True, exist_ok=True)

    @property
    def begin_path(self) -> Path:
        return self._base / "begin.wav"

    @property
    def end_path(self) -> Path:
        return self._base / "end.wav"

    def resolve(self, configured: str | None, default: Path) -> Path | None:
        if configured:
            path = Path(configured).expanduser()
            if path.is_file():
                return path
        return default if default.is_file() else None
