"""Scrollable application log panel."""

from __future__ import annotations

from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QLabel, QTextEdit, QVBoxLayout, QWidget

from easypal_next.core.events import EventBus, LogEvent

_LEVEL_COLORS = {
    "debug": QColor("#888888"),
    "info": QColor("#c8c8c8"),
    "warning": QColor("#e6c200"),
    "error": QColor("#ff6666"),
}


class LogPanel(QWidget):
    def __init__(self, event_bus: EventBus, parent=None) -> None:
        super().__init__(parent)
        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setMaximumHeight(140)
        self._text.setStyleSheet("background: #111; color: #ccc; font-family: monospace;")

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Log"))
        layout.addWidget(self._text)

        event_bus.subscribe(LogEvent, self._on_log)

    def _on_log(self, event: LogEvent) -> None:
        fmt = QTextCharFormat()
        fmt.setForeground(_LEVEL_COLORS.get(event.level, QColor("#cccccc")))
        cursor = self._text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(f"[{event.level.upper()}] {event.message}\n", fmt)
        self._text.setTextCursor(cursor)
        self._text.ensureCursorVisible()
