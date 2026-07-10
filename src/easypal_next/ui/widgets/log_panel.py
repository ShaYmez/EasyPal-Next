"""Scrollable application log panel."""

from __future__ import annotations

from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget

from easypal_next.core.events import EventBus, LogEvent

_LEVEL_COLORS = {
    "debug": QColor("#888888"),
    "info": QColor("#333333"),
    "warning": QColor("#b8860b"),
    "error": QColor("#cc3333"),
}

_LEVEL_COLORS_DARK = {
    "debug": QColor("#888888"),
    "info": QColor("#c8c8c8"),
    "warning": QColor("#e6c200"),
    "error": QColor("#ff6666"),
}


class LogPanel(QWidget):
    def __init__(self, event_bus: EventBus, parent=None, *, dark: bool = False) -> None:
        super().__init__(parent)
        self._dark = dark
        self._text = QPlainTextEdit()
        self._text.setObjectName("logView")
        self._text.setReadOnly(True)
        self._text.setMaximumBlockCount(200)
        self._text.setFixedHeight(72)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._text)

        event_bus.subscribe(LogEvent, self._on_log)

    def set_dark(self, dark: bool) -> None:
        self._dark = dark

    def _on_log(self, event: LogEvent) -> None:
        palette = _LEVEL_COLORS_DARK if self._dark else _LEVEL_COLORS
        fmt = QTextCharFormat()
        fmt.setForeground(palette.get(event.level, QColor("#cccccc")))
        cursor = self._text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(f"[{event.level.upper()}] {event.message}\n", fmt)
        self._text.setTextCursor(cursor)
