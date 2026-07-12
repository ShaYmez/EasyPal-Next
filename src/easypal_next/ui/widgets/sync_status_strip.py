"""Live HamDRM sync / profile strip for the main window."""

from __future__ import annotations

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from easypal_next.core.events import EventBus, SyncStatusEvent
from easypal_next.ui.sync_status_relay import SyncStatusRelay


class SyncStatusStrip(QWidget):
    """IO / Time / Frame / FAC / MSC indicators plus SNR and DRM profile."""

    def __init__(self, event_bus: EventBus, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("syncStatusStrip")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 0, 2, 0)
        layout.setSpacing(8)

        self._leds: dict[str, QLabel] = {}
        for key in ("IO", "Time", "Frame", "FAC", "MSC"):
            led = QLabel(key)
            led.setObjectName("syncLedOff")
            led.setAlignment(Qt.AlignmentFlag.AlignCenter)
            led.setMinimumWidth(40)
            self._leds[key] = led
            layout.addWidget(led)

        self._snr = QLabel("SNR —")
        self._snr.setObjectName("syncSnrLabel")
        layout.addWidget(self._snr)

        self._profile = QLabel("")
        self._profile.setObjectName("syncProfileLabel")
        layout.addWidget(self._profile, stretch=1)

        self._tx = QLabel("")
        self._tx.setObjectName("syncTxLabel")
        layout.addWidget(self._tx)

        self._relay = SyncStatusRelay(event_bus, self)
        self._relay.sync_received.connect(self._on_sync, Qt.ConnectionType.QueuedConnection)

    def _set_led(self, key: str, on: bool) -> None:
        led = self._leds[key]
        led.setObjectName("syncLedOn" if on else "syncLedOff")
        led.style().unpolish(led)
        led.style().polish(led)

    @Slot(object)
    def _on_sync(self, event: SyncStatusEvent) -> None:
        self._set_led("IO", event.io)
        self._set_led("Time", event.time)
        self._set_led("Frame", event.frame)
        self._set_led("FAC", event.fac)
        self._set_led("MSC", event.msc)
        if event.snr_db is not None:
            self._snr.setText(f"SNR {event.snr_db:.1f} dB")
        else:
            self._snr.setText("SNR —")
        parts = []
        if event.callsign:
            parts.append(event.callsign)
        if event.mode:
            parts.append(event.mode)
        if event.dc_freq is not None:
            parts.append(f"DC {event.dc_freq} Hz")
        self._profile.setText(" · ".join(parts))
        if event.percent_tx is not None:
            seg = f" seg {event.seg_pos}" if event.seg_pos is not None else ""
            self._tx.setText(f"TX {event.percent_tx}%{seg}")
        else:
            self._tx.setText("")
