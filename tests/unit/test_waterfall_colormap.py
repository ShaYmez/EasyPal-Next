"""Tests for SDR-style waterfall colormap and history buffer."""

from __future__ import annotations

import numpy as np

from easypal_next.config.schema import WaterfallConfig
from easypal_next.ui.waterfall_colormap import apply_colormap, db_to_levels, history_to_rgb


def test_db_to_levels_uses_fixed_range():
    db = np.array([-80.0, -40.0, 0.0], dtype=np.float32)
    levels = db_to_levels(db, -80.0, 0.0)
    assert levels.tolist() == [0.0, 0.5, 1.0]


def test_history_to_rgb_shape():
    cfg = WaterfallConfig()
    hist = np.full((8, 16), -50.0, dtype=np.float32)
    hist[0, 8] = -10.0
    rgb = history_to_rgb(hist, cfg)
    assert rgb.shape == (8, 16, 3)
    assert rgb.dtype == np.uint8
    assert rgb[0, 8, 1] > rgb[4, 4, 1]


def test_green_colormap_dark_for_silence():
    levels = np.array([[0.0, 0.5, 1.0]], dtype=np.float32)
    rgb = apply_colormap(levels, "green")
    assert rgb[0, 0].sum() < rgb[0, 2].sum()
