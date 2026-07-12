"""Line spectrum strip above the scrolling waterfall history."""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPolygon
from PySide6.QtWidgets import QSizePolicy, QWidget

from easypal_next.config.schema import WaterfallConfig
from easypal_next.waterfall.cue_wav import TUNE_FREQS_HZ

# EasyPal waterfall Hz legends (guide: yellow marker = 500 Hz).
EASYPAL_AXIS_HZ = (500, 1000, 1500, 2000, 2500)


def _hz_to_x(freq: float, config: WaterfallConfig, width: int) -> int:
    lo = float(config.freq_min_hz)
    hi = float(config.freq_max_hz)
    span = max(hi - lo, 1.0)
    return int(round((float(freq) - lo) / span * (width - 1)))


def _draw_tune_markers(painter: QPainter, config: WaterfallConfig, w: int, y: int) -> None:
    """EasyPal green Tune markers — same Hz as on-air three-tone Tune."""
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(0, 220, 70))
    lo = float(config.freq_min_hz)
    hi = float(config.freq_max_hz)
    for freq in TUNE_FREQS_HZ:
        if freq < lo or freq > hi:
            continue
        x = _hz_to_x(freq, config, w)
        painter.drawRect(x - 3, y, 6, 6)


def _draw_hz_axis(painter: QPainter, config: WaterfallConfig, w: int, h: int) -> None:
    """Draw 500/1000/1500/2000/2500 labels like stock EasyPal."""
    painter.setPen(QColor(170, 175, 180))
    font = painter.font()
    font.setPointSize(8)
    painter.setFont(font)
    lo = float(config.freq_min_hz)
    hi = float(config.freq_max_hz)
    for freq in EASYPAL_AXIS_HZ:
        if freq < lo or freq > hi:
            continue
        x = _hz_to_x(freq, config, w)
        painter.drawLine(x, h - 14, x, h - 8)
        label = str(int(freq))
        tw = painter.fontMetrics().horizontalAdvance(label)
        painter.drawText(x - tw // 2, h - 2, label)


class SpectrumStrip(QWidget):
    """Draw the latest FFT row as a filled line plot (EasyPal-style)."""

    def __init__(self, config: WaterfallConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._config = config
        self._bins: list[float] = []
        self.setMinimumHeight(86)
        self.setMaximumHeight(110)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setObjectName("spectrumStrip")

    def update_config(self, config: WaterfallConfig) -> None:
        self._config = config
        self.update()

    def reset(self) -> None:
        self._bins = []
        self.update()

    def set_bins(self, db_bins: list[float]) -> None:
        self._bins = list(db_bins) if db_bins else []
        self.update()

    def paintEvent(self, event) -> None:  # noqa: ANN001, N802
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(8, 10, 14))
        w = max(1, self.width())
        h = max(1, self.height())
        if len(self._bins) < 2:
            painter.setPen(QColor(100, 110, 120))
            painter.drawText(self.rect().adjusted(0, 0, 0, -16), Qt.AlignmentFlag.AlignCenter, "Spectrum")
            _draw_hz_axis(painter, self._config, w, h)
            _draw_tune_markers(painter, self._config, w, h - 22)
            return

        min_db = self._config.min_db
        max_db = self._config.max_db
        span = max(max_db - min_db, 1e-6)
        n = len(self._bins)
        plot_h = max(1, h - 18)

        # Grid
        painter.setPen(QPen(QColor(40, 48, 56), 1))
        for frac in (0.25, 0.5, 0.75):
            y = int(plot_h * frac)
            painter.drawLine(0, y, w, y)

        # Spectrum fill + line (cyan like classic EasyPal)
        line_color = QColor(0, 220, 255)
        fill_color = QColor(0, 140, 180, 90)
        points_y: list[int] = []
        for i, db in enumerate(self._bins):
            level = (float(db) - min_db) / span
            level = max(0.0, min(1.0, level))
            y = int((1.0 - level) * (plot_h - 2)) + 1
            points_y.append(y)

        for i in range(n - 1):
            x0 = int(i * (w - 1) / (n - 1))
            x1 = int((i + 1) * (w - 1) / (n - 1))
            y0 = points_y[i]
            y1 = points_y[i + 1]
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(fill_color)
            painter.drawPolygon(
                QPolygon(
                    [
                        QPoint(x0, plot_h),
                        QPoint(x0, y0),
                        QPoint(x1, y1),
                        QPoint(x1, plot_h),
                    ]
                )
            )
            painter.setPen(QPen(line_color, 1))
            painter.drawLine(x0, y0, x1, y1)

        _draw_hz_axis(painter, self._config, w, h)
        _draw_tune_markers(painter, self._config, w, h - 22)
