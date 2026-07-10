"""Waterfall text editor — compact row with Send WFTxt."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QWidget,
)

from easypal_next.config.schema import WaterfallConfig


class WaterfallTextEditor(QWidget):
    send_requested = Signal()

    def __init__(self, config: WaterfallConfig, parent=None) -> None:
        super().__init__(parent)
        self._config = config

        self._begin = QLineEdit(config.begin_message)
        self._font = QComboBox()
        self._font.setEditable(True)
        self._font.addItems(["DejaVu Sans Mono", "Consolas", "Courier New", "Arial"])
        idx = self._font.findText(config.default_font)
        if idx >= 0:
            self._font.setCurrentIndex(idx)
        else:
            self._font.setCurrentText(config.default_font)
        self._font_size = QSpinBox()
        self._font_size.setRange(8, 48)
        self._font_size.setValue(config.default_font_size)
        self._font_size.setFixedWidth(56)

        self._send_btn = QPushButton("Send WFTxt")
        self._send_btn.setObjectName("primaryButton")
        self._send_btn.clicked.connect(self.send_requested.emit)

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        row.addWidget(QLabel("Message:"))
        row.addWidget(self._begin, stretch=1)
        row.addWidget(QLabel("Font:"))
        row.addWidget(self._font)
        row.addWidget(QLabel("Size:"))
        row.addWidget(self._font_size)
        row.addWidget(self._send_btn)

    def set_transmitting(self, active: bool) -> None:
        self._send_btn.setEnabled(not active)

    def begin_message(self) -> str:
        return self._begin.text()

    def apply_to_config(self, config: WaterfallConfig) -> None:
        config.begin_message = self._begin.text()
        config.default_font = self._font.currentText()
        config.default_font_size = self._font_size.value()

    def sync_from_config(self, config: WaterfallConfig) -> None:
        self._begin.setText(config.begin_message)
        font_idx = self._font.findText(config.default_font)
        if font_idx >= 0:
            self._font.setCurrentIndex(font_idx)
        else:
            self._font.setCurrentText(config.default_font)
        self._font_size.setValue(config.default_font_size)
