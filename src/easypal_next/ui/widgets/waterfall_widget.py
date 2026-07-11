"""Live waterfall spectrum display."""

from __future__ import annotations

import time
from typing import Literal

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import QProgressBar, QSizePolicy, QVBoxLayout, QWidget, QLabel

from easypal_next.config.schema import WaterfallConfig
from easypal_next.core.events import EventBus
from easypal_next.core.session import SessionState
from easypal_next.ui.spectrum_relay import SpectrumRelay
from easypal_next.ui.widgets.waterfall_canvas import WaterfallCanvas

_TX_SPECTRUM_STATES = frozenset(
    {
        SessionState.TUNING,
        SessionState.TX_ARMED,
        SessionState.TX_WATERFALL_HEADER,
        SessionState.TX_ACTIVE,
        SessionState.TX_WATERFALL_FOOTER,
    }
)


def spectrum_source_accepted(
    session_state: SessionState,
    source: Literal["rx", "tx"],
) -> bool:
    """Return whether a spectrum row should be shown for the current session."""
    if session_state in _TX_SPECTRUM_STATES:
        return source == "tx"
    return source == "rx"


def peak_db_to_level_pct(peak_db: float, min_db: float, max_db: float) -> int:
    span = max_db - min_db
    if span <= 0:
        return 0
    level = (peak_db - min_db) / span
    return int(max(0.0, min(1.0, level)) * 100)


class WaterfallWidget(QWidget):
    def __init__(
        self,
        event_bus: EventBus,
        config: WaterfallConfig,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._config = config
        self._session_state = SessionState.IDLE
        self._loopback = True
        self._radio_emission = "fm"
        self._active = False
        self._last_paint = 0.0

        self._band_label = QLabel(
            f"{config.freq_min_hz}–{config.freq_max_hz} Hz · live spectrum"
        )

        self._level_bar = QProgressBar()
        self._level_bar.setObjectName("audioLevelBar")
        self._level_bar.setRange(0, 100)
        self._level_bar.setValue(0)
        self._level_bar.setTextVisible(False)
        self._level_bar.setFixedHeight(8)
        self._level_bar.setToolTip("Input level (peak dB in band)")

        self._level_label = QLabel("Input: —")
        self._level_label.setObjectName("audioLevelLabel")

        self._canvas = WaterfallCanvas(config)
        self._update_idle_text()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        layout.addWidget(self._band_label)
        level_row = QVBoxLayout()
        level_row.setSpacing(1)
        level_row.addWidget(self._level_bar)
        level_row.addWidget(self._level_label)
        layout.addLayout(level_row)
        layout.addWidget(self._canvas, stretch=1)

        self._relay = SpectrumRelay(event_bus, config.fft_interval_ms, self)
        self._relay.spectrum_received.connect(
            self._append_spectrum,
            Qt.ConnectionType.QueuedConnection,
        )

    def set_live_enabled(self, enabled: bool) -> None:
        self._config.live_enabled = enabled
        if not enabled:
            self.reset_live()

    def reset_live(self) -> None:
        """Clear scrolled spectrum and show idle / session hint text."""
        self._active = False
        self._level_bar.setValue(0)
        self._level_label.setText("Input: —")
        self._canvas.reset()
        self._update_idle_text()

    def update_config(self, config: WaterfallConfig) -> None:
        self._config = config
        self._band_label.setText(
            f"{config.freq_min_hz}–{config.freq_max_hz} Hz · live spectrum"
        )
        self._relay.set_interval_ms(config.fft_interval_ms)
        self._canvas.update_config(config)
        if not config.live_enabled:
            self.reset_live()

    def set_session_context(
        self,
        state: SessionState,
        loopback: bool,
        radio_emission: str = "fm",
    ) -> None:
        self._session_state = state
        self._loopback = loopback
        self._radio_emission = radio_emission
        if not self._active:
            self._update_idle_text()

    def _tuning_hint(self, emission: str) -> str:
        mode = emission.lower()
        if mode == "fm":
            return "Tuning (FM) — set SignaLink drive / VOX; watch waterfall for clean tone"
        if mode == "am":
            return "Tuning (AM) — use low drive; avoid over-modulation on carrier"
        if mode == "ssb":
            return "Tuning (USB) — 2.4 kHz filter; no compression; adjust MIC gain"
        return "Tuning — adjust audio drive / VOX; watch waterfall"

    def _update_idle_text(self) -> None:
        if not self._config.live_enabled:
            text = "Live waterfall disabled — enable in toolbar or Settings"
        elif self._session_state == SessionState.TUNING:
            text = self._tuning_hint(self._radio_emission)
        elif self._session_state == SessionState.RX_LISTEN:
            text = (
                "Listening for signal…"
                if not self._loopback
                else "RX armed — waterfall activates during transmit"
            )
        elif self._loopback:
            text = "Waterfall activates during transmit (loopback)"
        else:
            text = "Live input monitor — speak or tap mic; level bar should move"
        self._canvas.set_idle_text(text)

    def _slice_bins(self, bins: list[float], sample_rate: int) -> list[float]:
        if not bins or sample_rate <= 0:
            return bins
        nyquist = sample_rate / 2
        n = len(bins)
        if n < 2 or nyquist <= 0:
            return bins
        bin_hz = nyquist / (n - 1)
        i0 = max(0, int(self._config.freq_min_hz / bin_hz))
        i1 = min(n - 1, int(self._config.freq_max_hz / bin_hz))
        if i0 >= i1:
            return bins
        return bins[i0 : i1 + 1]

    def _update_level_meter(self, peak_db: float) -> None:
        pct = peak_db_to_level_pct(peak_db, self._config.min_db, self._config.max_db)
        self._level_bar.setValue(pct)
        self._level_label.setText(f"Input: {peak_db:.0f} dB")

    @Slot(object, int, str, float)
    def _append_spectrum(
        self,
        bins: list[float],
        sample_rate: int,
        source: str,
        peak_db: float,
    ) -> None:
        if not bins or not self._config.live_enabled:
            return
        if not spectrum_source_accepted(self._session_state, source):  # type: ignore[arg-type]
            return

        sliced = self._slice_bins(bins, sample_rate)
        band_peak = max(sliced) if sliced else peak_db
        self._update_level_meter(band_peak)

        now = time.monotonic()
        min_interval = self._config.fft_interval_ms / 1000.0
        if now - self._last_paint < min_interval:
            return
        self._last_paint = now

        if not sliced:
            return
        self._active = True
        self._canvas.append_row(sliced)

    def resizeEvent(self, event) -> None:  # noqa: ANN001, N802
        super().resizeEvent(event)
        self._canvas.update()
