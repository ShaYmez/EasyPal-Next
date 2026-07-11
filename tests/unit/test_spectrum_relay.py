"""Tests for SpectrumRelay timer behaviour."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from easypal_next.core.events import EventBus, SpectrumEvent
from easypal_next.ui.spectrum_relay import SpectrumRelay


def _app() -> QApplication:
    return QApplication.instance() or QApplication(sys.argv)


def test_spectrum_relay_starts_timer():
    _app()
    bus = EventBus()
    relay = SpectrumRelay(bus, interval_ms=40)
    assert relay._timer.isActive()
    assert relay._timer.interval() == 40


def test_spectrum_relay_flushes_events():
    _app()
    bus = EventBus()
    relay = SpectrumRelay(bus, interval_ms=20)
    received: list[tuple] = []
    relay.spectrum_received.connect(lambda *args: received.append(args))
    bus.publish(SpectrumEvent(bins=[-20.0, -30.0], sample_rate=48000, source="rx"))
    relay._flush()
    assert received
    assert received[0][3] == -20.0
