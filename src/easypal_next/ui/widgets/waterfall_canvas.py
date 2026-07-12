"""2D scrolling FFT waterfall canvas (SDR-style spectrogram)."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QSizePolicy, QWidget

from easypal_next.config.schema import WaterfallConfig
from easypal_next.ui.waterfall_colormap import history_to_rgb
from easypal_next.waterfall.cue_wav import TUNE_FREQS_HZ


class WaterfallCanvas(QWidget):
    """Frequency on X, time scrolling down on Y; newest spectrum at the top."""

    def __init__(self, config: WaterfallConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._config = config
        self._history: np.ndarray | None = None
        self._active = False
        self._idle_text = ""
        self.setMinimumSize(120, 80)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setObjectName("waterfallDisplay")

    def set_idle_text(self, text: str) -> None:
        self._idle_text = text
        if not self._active:
            self.update()

    def reset(self) -> None:
        self._history = None
        self._active = False
        self.update()

    def update_config(self, config: WaterfallConfig) -> None:
        self._config = config
        self._history = None
        self.update()

    def append_row(self, db_bins: list[float]) -> None:
        if not db_bins:
            return
        cols = len(db_bins)
        rows = max(32, self._config.history_rows)
        row = np.asarray(db_bins, dtype=np.float32)
        if self._history is None or self._history.shape[1] != cols:
            self._history = np.full((rows, cols), self._config.min_db - 30.0, dtype=np.float32)

        scroll = max(1, self._config.scroll_pixels)
        if bool(getattr(self._config, "cinema_scroll", False)):
            # EasyPal cinema: newest at bottom (scroll upward in buffer terms).
            self._history = np.roll(self._history, -scroll, axis=0)
            for i in range(scroll):
                self._history[-(i + 1)] = row
        else:
            self._history = np.roll(self._history, scroll, axis=0)
            for i in range(scroll):
                self._history[i] = row
        self._active = True
        self.update()

    def _draw_tune_markers(self, painter: QPainter) -> None:
        lo = float(self._config.freq_min_hz)
        hi = float(self._config.freq_max_hz)
        span_hz = max(hi - lo, 1.0)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 220, 70))
        for freq in TUNE_FREQS_HZ:
            if freq < lo or freq > hi:
                continue
            x = int(round((float(freq) - lo) / span_hz * (self.width() - 1)))
            painter.drawRect(x - 3, 0, 6, 6)

    def paintEvent(self, event) -> None:  # noqa: ANN001, N802
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(10, 10, 18))
        if not self._active or self._history is None:
            painter.setPen(QColor(136, 136, 136))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._idle_text)
            self._draw_tune_markers(painter)
            return

        rgb = np.ascontiguousarray(history_to_rgb(self._history, self._config))
        h, w, _ = rgb.shape
        image = QImage(rgb.data, w, h, w * 3, QImage.Format.Format_RGB888).copy()
        scaled = image.scaled(
            self.width(),
            self.height(),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        painter.drawImage(0, 0, scaled)
        self._draw_tune_markers(painter)
