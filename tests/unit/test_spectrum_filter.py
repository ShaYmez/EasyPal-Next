"""Tests for waterfall spectrum source filtering."""

from __future__ import annotations

from easypal_next.core.session import SessionState
from easypal_next.ui.widgets.waterfall_widget import spectrum_source_accepted


def test_tune_accepts_tx_spectrum_only():
    assert spectrum_source_accepted(SessionState.TUNING, "tx") is True
    assert spectrum_source_accepted(SessionState.TUNING, "rx") is False


def test_rx_listen_accepts_rx_spectrum_only():
    assert spectrum_source_accepted(SessionState.RX_LISTEN, "rx") is True
    assert spectrum_source_accepted(SessionState.RX_LISTEN, "tx") is False


def test_tx_active_accepts_tx_spectrum_only():
    assert spectrum_source_accepted(SessionState.TX_ACTIVE, "tx") is True
    assert spectrum_source_accepted(SessionState.TX_ACTIVE, "rx") is False
