"""Main application window shell."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QMainWindow, QStatusBar, QVBoxLayout, QWidget

from easypal_next.app.bootstrap import AppContext
from easypal_next.core.events import LogEvent, SessionStateChangedEvent
from easypal_next.network.util import gallery_urls


class MainWindow(QMainWindow):
    def __init__(self, context: AppContext) -> None:
        super().__init__()
        self._context = context
        self.setWindowTitle("EasyPal-Next")
        self.resize(1100, 720)

        central = QWidget()
        layout = QVBoxLayout(central)

        title = QLabel("EasyPal-Next")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        subtitle = QLabel(
            "Open-source digital SSTV — in memory of Erik Sundstrup VK4AES (SK)\n"
            "Copyright © 2026 Shane Daley M0VUB (ShaYmez)"
        )
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        self._status_label = QLabel("Session: idle")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status_label)

        local_url, lan_url = gallery_urls(context.config.network.port)
        gallery_lines = [f"Laptop: {local_url}"]
        if lan_url:
            gallery_lines.append(f"Phone/tablet (same Wi‑Fi): {lan_url}")
        else:
            gallery_lines.append("Phone/tablet: connect to this PC's LAN IP on port 8765")

        info = QLabel(
            "\n".join(gallery_lines)
            + f"\nCallsign: {context.config.callsign} · Modem: {context.config.modem.mode}"
        )
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setWordWrap(True)
        layout.addWidget(info)

        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready")

        context.event_bus.subscribe(SessionStateChangedEvent, self._on_state_changed)
        context.event_bus.subscribe(LogEvent, self._on_log)

    def _on_state_changed(self, event: SessionStateChangedEvent) -> None:
        self._status_label.setText(f"Session: {event.state.value}")
        self.statusBar().showMessage(f"State → {event.state.value}", 5000)

    def _on_log(self, event: LogEvent) -> None:
        self.statusBar().showMessage(event.message, 8000)
