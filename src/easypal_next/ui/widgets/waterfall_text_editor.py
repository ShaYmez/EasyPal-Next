"""Waterfall text editor widget stub."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class WaterfallTextEditor(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("WFTxt editor — waterfall text painting (coming soon)"))
