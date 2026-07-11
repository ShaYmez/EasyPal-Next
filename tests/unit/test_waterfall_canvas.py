"""Tests for waterfall canvas history scrolling."""

from __future__ import annotations

import sys

import numpy as np
from PySide6.QtWidgets import QApplication

from easypal_next.config.schema import WaterfallConfig
from easypal_next.ui.widgets.waterfall_canvas import WaterfallCanvas


def _app() -> QApplication:
    return QApplication.instance() or QApplication(sys.argv)


def test_canvas_rolls_history_down():
    _app()
    cfg = WaterfallConfig(history_rows=8, scroll_pixels=1)
    canvas = WaterfallCanvas(cfg)
    row_a = [-60.0] * 4
    row_b = [-20.0] * 4
    canvas.append_row(row_a)
    canvas.append_row(row_b)
    assert canvas._history is not None
    assert canvas._history[0, 0] == -20.0
    assert canvas._history[1, 0] == -60.0


def test_canvas_scroll_speed():
    _app()
    cfg = WaterfallConfig(history_rows=8, scroll_pixels=2)
    canvas = WaterfallCanvas(cfg)
    canvas.append_row([-50.0] * 4)
    canvas.append_row([-10.0] * 4)
    assert canvas._history[0, 0] == -10.0
    assert canvas._history[1, 0] == -10.0
    assert canvas._history[2, 0] == -50.0
