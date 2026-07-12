"""Tests for HamDRM spectrum dB conversion and callsign helpers."""

from __future__ import annotations

import math

from easypal_next.config.schema import AppConfig
from easypal_next.modem.callsign_tx import DEFAULT_CALLSIGN, effective_callsign
from easypal_next.modem.hamdrm_backend import linear_spectrum_to_db


def test_linear_spectrum_to_db_converts_magnitudes():
    bins = linear_spectrum_to_db([1.0, 0.1, 0.0])
    assert abs(bins[0] - 0.0) < 1e-6
    assert abs(bins[1] - (-20.0)) < 1e-6
    assert bins[2] < -200.0


def test_linear_spectrum_quiet_not_zero_db():
    """Tiny linear values must not map near 0 dB (that pegged the yellow waterfall)."""
    bins = linear_spectrum_to_db([1e-6, 1e-4])
    assert bins[0] < -100.0
    assert bins[1] < -70.0
    assert all(math.isfinite(x) for x in bins)


def test_effective_callsign_blank_becomes_n0call():
    cfg = AppConfig(callsign="  ")
    assert effective_callsign(cfg) == DEFAULT_CALLSIGN
    assert effective_callsign("") == DEFAULT_CALLSIGN
    assert effective_callsign(None) == DEFAULT_CALLSIGN


def test_effective_callsign_uppercases():
    assert effective_callsign("m0vub") == "M0VUB"
    cfg = AppConfig(callsign="m0vub")
    assert effective_callsign(cfg) == "M0VUB"


def test_require_callsign_header_default_true():
    assert AppConfig().transfer.require_callsign_wftxt_header is True


def test_drm_callsign_requires_letter_and_digit():
    from easypal_next.core.events import EventBus
    from easypal_next.modem.hamdrm_backend import HamDrmBackend
    from unittest.mock import MagicMock

    backend = HamDrmBackend(AppConfig(), EventBus(), MagicMock(), MagicMock())
    assert backend._drm_callsign_ok("N0CALL")
    assert backend._drm_callsign_ok("M0VUB")
    assert not backend._drm_callsign_ok("NOCALL")
    assert not backend._drm_callsign_ok("TEST")
    assert not backend._drm_callsign_ok("")


def test_hamdrm_specocc_default_23():
    assert AppConfig().modem.hamdrm_specocc == "2.3"
