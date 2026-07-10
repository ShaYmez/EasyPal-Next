"""Configuration loading with defaults and user overrides."""

from __future__ import annotations

from pathlib import Path

import yaml

from easypal_next.app.paths import app_root, bundled_defaults_path, user_config_path
from easypal_next.config.schema import AppConfig


def _load_yaml(path: Path) -> dict:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return data if isinstance(data, dict) else {}


def _resolve_defaults_path(explicit: Path | None) -> Path:
    if explicit and explicit.is_file():
        return explicit
    candidates = [
        bundled_defaults_path(),
        app_root() / "config" / "defaults.yaml",
        Path(__file__).resolve().parents[3] / "config" / "defaults.yaml",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return bundled_defaults_path()


def _deep_merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(
    defaults_path: Path | None = None,
    user_path: Path | None = None,
) -> AppConfig:
    defaults = _load_yaml(_resolve_defaults_path(defaults_path))
    user = _load_yaml(user_path or user_config_path())
    merged = _deep_merge(defaults, user)
    return AppConfig.model_validate(merged)
