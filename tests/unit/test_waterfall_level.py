"""Tests for waterfall level meter helpers."""

from __future__ import annotations

from easypal_next.ui.widgets.waterfall_widget import peak_db_to_level_pct


def test_peak_db_to_level_pct_maps_range():
    assert peak_db_to_level_pct(-80.0, -80.0, 0.0) == 0
    assert peak_db_to_level_pct(0.0, -80.0, 0.0) == 100
    assert peak_db_to_level_pct(-40.0, -80.0, 0.0) == 50


def test_peak_db_to_level_pct_clamps():
    assert peak_db_to_level_pct(-120.0, -80.0, 0.0) == 0
    assert peak_db_to_level_pct(10.0, -80.0, 0.0) == 100
