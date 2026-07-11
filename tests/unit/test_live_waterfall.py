"""Tests for live waterfall configuration gating."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np

from easypal_next.config.schema import AppConfig
from easypal_next.core.events import EventBus
from easypal_next.core.transfer_engine import TransferEngine


def test_feed_spectrum_skipped_when_live_disabled():
    config = AppConfig()
    config.waterfall.live_enabled = False
    engine = TransferEngine(
        config,
        EventBus(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
    )
    engine._feed_spectrum(np.ones(128, dtype=np.int16))  # noqa: SLF001
    assert engine._spectrum_tap is None  # noqa: SLF001
