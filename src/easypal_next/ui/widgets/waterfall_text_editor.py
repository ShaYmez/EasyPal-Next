"""Waterfall text editor for TX header/footer messages."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from easypal_next.config.schema import WaterfallConfig


class WaterfallTextEditor(QWidget):
    def __init__(self, config: WaterfallConfig, parent=None) -> None:
        super().__init__(parent)
        self._config = config

        self._begin = QLineEdit(config.begin_message)
        self._end = QLineEdit(config.end_message)
        self._font = QComboBox()
        self._font.addItems(["DejaVu Sans Mono", "Consolas", "Courier New", "Arial"])
        idx = self._font.findText(config.default_font)
        if idx >= 0:
            self._font.setCurrentIndex(idx)
        self._font_size = QSpinBox()
        self._font_size.setRange(8, 48)
        self._font_size.setValue(config.default_font_size)
        self._preview = QTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setMaximumHeight(60)
        self._preview.setPlainText(self._begin.text())

        self._begin.textChanged.connect(self._update_preview)
        form = QFormLayout()
        form.addRow("Begin message:", self._begin)
        form.addRow("End message:", self._end)
        row = QHBoxLayout()
        row.addWidget(QLabel("Font:"))
        row.addWidget(self._font)
        row.addWidget(QLabel("Size:"))
        row.addWidget(self._font_size)
        form.addRow(row)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("WFTxt — waterfall text painting"))
        layout.addLayout(form)
        layout.addWidget(QLabel("Preview:"))
        layout.addWidget(self._preview)

    def _update_preview(self) -> None:
        self._preview.setPlainText(self._begin.text())

    def apply_to_config(self, config: WaterfallConfig) -> None:
        config.begin_message = self._begin.text()
        config.end_message = self._end.text()
        config.default_font = self._font.currentText()
        config.default_font_size = self._font_size.value()
