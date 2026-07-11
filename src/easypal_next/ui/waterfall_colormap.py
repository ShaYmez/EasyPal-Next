"""Colormap helpers for live FFT waterfall display."""

from __future__ import annotations

import numpy as np

from easypal_next.config.schema import WaterfallConfig


def db_to_levels(db: np.ndarray, min_db: float, max_db: float) -> np.ndarray:
    span = max_db - min_db
    if span <= 0:
        return np.zeros_like(db, dtype=np.float32)
    return np.clip((db - min_db) / span, 0.0, 1.0).astype(np.float32)


def apply_colormap(levels: np.ndarray, cmap: str) -> np.ndarray:
    """Map normalized levels (0–1) to RGB uint8 array with shape (rows, cols, 3)."""
    levels = np.clip(levels, 0.0, 1.0)
    if cmap == "grayscale":
        v = (levels * 255).astype(np.uint8)
        return np.stack([v, v, v], axis=-1)
    if cmap == "heat":
        r = (levels * 255).astype(np.uint8)
        g = (levels * 180).astype(np.uint8)
        b = ((1.0 - levels) * 80).astype(np.uint8)
        return np.stack([r, g, b], axis=-1)
    # SDR-style green: black noise floor, green body, yellow-white peaks
    red = (np.clip((levels - 0.72) * 3.5, 0.0, 1.0) * 255).astype(np.uint8)
    green = (np.clip(levels * 1.05, 0.0, 1.0) * 255).astype(np.uint8)
    blue = (np.clip(levels * 0.35, 0.0, 1.0) * 255).astype(np.uint8)
    return np.stack([red, green, blue], axis=-1)


def history_to_rgb(history_db: np.ndarray, config: WaterfallConfig) -> np.ndarray:
    levels = db_to_levels(history_db, config.min_db, config.max_db)
    return apply_colormap(levels, config.colormap)
