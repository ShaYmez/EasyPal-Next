"""HamDRM WFTxt routing smoke tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np

from easypal_next.config.schema import AppConfig
from easypal_next.core.events import EventBus
from easypal_next.modem.hamdrm_backend import HamDrmBackend


def test_transmit_waterfall_text_loopback_plays_pcm():
    cfg = AppConfig()
    cfg.transfer.loopback_mode = True
    backend = HamDrmBackend(cfg, EventBus(), MagicMock(), radio=None)
    with patch("easypal_next.modem.hamdrm_backend.play_pcm_blocking") as play:
        with patch(
            "easypal_next.modem.hamdrm_backend.encode_waterfall_text",
            return_value=np.zeros(4800, dtype=np.int16),
        ):
            backend.transmit_waterfall_text("TEST")
    play.assert_called_once()


def test_hamdrm_backend_exposes_transmit_waterfall_text():
    assert hasattr(HamDrmBackend, "transmit_waterfall_text")
