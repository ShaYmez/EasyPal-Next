"""Tests for auto RX behaviour."""

from __future__ import annotations

from unittest.mock import MagicMock

from easypal_next.config.schema import AppConfig
from easypal_next.core.events import EventBus
from easypal_next.core.session import SessionState
from easypal_next.core.transfer_engine import TransferEngine


def _engine(*, loopback: bool = False, auto_rx: bool = True) -> TransferEngine:
    config = AppConfig()
    config.transfer.loopback_mode = loopback
    config.transfer.auto_rx = auto_rx
    rx_modem = MagicMock()
    rx_modem.frame_payload_size = 126
    return TransferEngine(
        config,
        EventBus(),
        MagicMock(),
        rx_modem,
        MagicMock(),
        MagicMock(),
        MagicMock(),
    )


def test_start_auto_rx_arms_listen_on_air():
    engine = _engine()
    engine.start_auto_rx()
    assert engine.state == SessionState.RX_LISTEN


def test_start_auto_rx_ignored_in_loopback():
    engine = _engine(loopback=True)
    engine.start_auto_rx()
    assert engine.state == SessionState.IDLE
