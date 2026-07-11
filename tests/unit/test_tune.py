"""Tests for on-air Tune feature."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from easypal_next.config.schema import AppConfig
from easypal_next.core.events import EventBus
from easypal_next.core.session import SessionState
from easypal_next.core.transfer_engine import TransferEngine


def _minimal_engine(*, loopback: bool = True) -> TransferEngine:
    config = AppConfig()
    config.transfer.loopback_mode = loopback
    return TransferEngine(
        config,
        EventBus(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
    )


def test_start_tune_rejects_loopback():
    engine = _minimal_engine(loopback=True)
    with pytest.raises(RuntimeError, match="loopback"):
        engine.start_tune()


def test_start_tune_rejects_non_idle_state():
    engine = _minimal_engine(loopback=False)
    engine._state = SessionState.TX_ACTIVE
    with pytest.raises(RuntimeError, match="Cannot start Tune"):
        engine.start_tune()


def test_stop_tune_noop_when_not_tuning():
    engine = _minimal_engine(loopback=False)
    assert engine.state == SessionState.IDLE
    engine.stop_tune()


def test_stop_tune_halts_audio_when_tuning():
    bridge = MagicMock()
    engine = TransferEngine(
        AppConfig(),
        EventBus(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        modem_bridge=bridge,
    )
    config = engine._config  # noqa: SLF001
    config.transfer.loopback_mode = False
    engine._state = SessionState.TUNING
    engine._worker = MagicMock()
    engine._worker.is_alive.return_value = False

    engine.stop_tune()

    bridge.cancel_tx.assert_called()
    assert engine.state == SessionState.IDLE
