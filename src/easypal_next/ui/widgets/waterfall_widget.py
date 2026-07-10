"""Live waterfall spectrum display."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from easypal_next.core.events import EventBus, SpectrumEvent


class _SpectrumBridge(QWidget):
    """Thread-safe bridge from EventBus to Qt signals."""

    spectrum_received = Signal(list)

    def __init__(self, event_bus: EventBus) -> None:
        super().__init__()
        event_bus.subscribe(SpectrumEvent, self._on_spectrum)

    def _on_spectrum(self, event: SpectrumEvent) -> None:
        self.spectrum_received.emit(event.bins)


class WaterfallWidget(QWidget):
    def __init__(self, event_bus: EventBus, parent=None) -> None:
        super().__init__(parent)
        self._history: list[list[float]] = []
        self._max_rows = 120
        self._label = QLabel()
        self._label.setMinimumSize(160, 100)
        self._label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet("background: #0a0a12; border: 1px solid #333;")
        self._label.setText("Waterfall — start Receive for live spectrum")

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Waterfall spectrum"))
        layout.addWidget(self._label, stretch=1)

        self._bridge = _SpectrumBridge(event_bus)
        self._bridge.spectrum_received.connect(self._append_spectrum)

    @Slot(list)
    def _append_spectrum(self, bins: list[float]) -> None:
        self._history.append(bins)
        if len(self._history) > self._max_rows:
            self._history = self._history[-self._max_rows :]
        self._redraw()

    def _redraw(self) -> None:
        if not self._history:
            return
        label_w = max(1, self._label.width())
        label_h = max(1, self._label.height())
        rows = len(self._history)
        cols = len(self._history[0])
        image = QImage(cols, rows, QImage.Format.Format_RGB32)
        for row, bins in enumerate(self._history):
            for col, db in enumerate(bins[:cols]):
                level = max(0.0, min(1.0, (db + 80) / 80.0))
                green = int(level * 255)
                image.setPixelColor(col, row, QColor(0, green, int(level * 128)))
        pix = QPixmap.fromImage(image).scaled(
            label_w,
            label_h,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        self._label.setPixmap(pix)

    def resizeEvent(self, event) -> None:  # noqa: ANN001, N802
        super().resizeEvent(event)
        self._redraw()
