"""Live waterfall spectrum display."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from easypal_next.config.schema import WaterfallConfig
from easypal_next.core.events import EventBus, SpectrumEvent
from easypal_next.core.session import SessionState


class _SpectrumBridge(QWidget):
    spectrum_received = Signal(list)

    def __init__(self, event_bus: EventBus) -> None:
        super().__init__()
        event_bus.subscribe(SpectrumEvent, self._on_spectrum)

    def _on_spectrum(self, event: SpectrumEvent) -> None:
        self.spectrum_received.emit(event.bins)


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
        self._active = False
        self._waterfall_image: QImage | None = None

        self._band_label = QLabel(
            f"{config.freq_min_hz}–{config.freq_max_hz} Hz · live spectrum"
        )

        self._label = QLabel()
        self._label.setObjectName("waterfallDisplay")
        self._label.setMinimumSize(120, 80)
        self._label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._update_idle_text()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        layout.addWidget(self._band_label)
        layout.addWidget(self._label, stretch=1)

        self._bridge = _SpectrumBridge(event_bus)
        self._bridge.spectrum_received.connect(self._append_spectrum)

    def update_config(self, config: WaterfallConfig) -> None:
        self._config = config
        self._band_label.setText(
            f"{config.freq_min_hz}–{config.freq_max_hz} Hz · live spectrum"
        )

    def set_session_context(self, state: SessionState, loopback: bool) -> None:
        self._session_state = state
        self._loopback = loopback
        if not self._active:
            self._update_idle_text()

    def _update_idle_text(self) -> None:
        if self._session_state == SessionState.RX_LISTEN:
            text = (
                "Listening for signal…"
                if not self._loopback
                else "RX armed — waterfall activates during transmit"
            )
        elif self._loopback:
            text = "Waterfall activates during transmit (loopback)"
        else:
            text = "Waterfall — waiting for spectrum"
        self._label.setText(text)
        self._label.setPixmap(QPixmap())

    def _level_to_color(self, level: float) -> QColor:
        level = max(0.0, min(1.0, level))
        cmap = self._config.colormap
        if cmap == "grayscale":
            v = int(level * 255)
            return QColor(v, v, v)
        if cmap == "heat":
            return QColor(int(level * 255), int(level * 180), int((1.0 - level) * 80))
        green = int(level * 255)
        return QColor(0, green, int(level * 128))

    def _db_to_level(self, db: float) -> float:
        span = self._config.max_db - self._config.min_db
        if span <= 0:
            return 0.0
        return (db - self._config.min_db) / span

    @Slot(list)
    def _append_spectrum(self, bins: list[float]) -> None:
        if not bins:
            return
        self._active = True
        cols = len(bins)
        row = QImage(cols, 1, QImage.Format.Format_RGB32)
        for col, db in enumerate(bins):
            level = self._db_to_level(db)
            row.setPixelColor(col, 0, self._level_to_color(level))

        label_w = max(1, self._label.width())
        label_h = max(1, self._label.height())

        if self._waterfall_image is None or self._waterfall_image.width() != label_w:
            self._waterfall_image = QImage(label_w, label_h, QImage.Format.Format_RGB32)
            self._waterfall_image.fill(QColor(10, 10, 18))

        assert self._waterfall_image is not None
        painter = QPainter(self._waterfall_image)
        painter.drawImage(0, label_h - 1, self._waterfall_image, 0, label_h - 2, label_w, label_h - 1)
        scaled_row = row.scaled(label_w, 1, Qt.AspectRatioMode.IgnoreAspectRatio)
        painter.drawImage(0, 0, scaled_row)
        painter.end()

        self._label.setPixmap(QPixmap.fromImage(self._waterfall_image))
        self._label.setText("")

    def resizeEvent(self, event) -> None:  # noqa: ANN001, N802
        super().resizeEvent(event)
        self._waterfall_image = None
