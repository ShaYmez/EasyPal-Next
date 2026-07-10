"""Main application window."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from easypal_next.app.bootstrap import AppContext
from easypal_next.app.paths import user_gallery_dir
from easypal_next.core.events import LogEvent, SessionStateChangedEvent
from easypal_next.core.session import SessionState
from easypal_next.network.util import gallery_urls
from easypal_next.ui.view_models.transfer_vm import TransferViewModel


class MainWindow(QMainWindow):
    def __init__(self, context: AppContext) -> None:
        super().__init__()
        self._context = context
        self._selected_file: Path | None = None
        self._vm = TransferViewModel(context.event_bus)
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
        info = QLabel(
            "\n".join(gallery_lines)
            + f"\nCallsign: {context.config.callsign} · Modem: {context.config.modem.mode}"
            + f" · Mode: {'loopback' if context.config.transfer.loopback_mode else 'on-air'}"
        )
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setWordWrap(True)
        layout.addWidget(info)

        device_row = QHBoxLayout()
        device_row.addWidget(QLabel("Audio input:"))
        self._input_device = QComboBox()
        device_row.addWidget(self._input_device)
        device_row.addWidget(QLabel("Audio output:"))
        self._output_device = QComboBox()
        device_row.addWidget(self._output_device)
        layout.addLayout(device_row)
        self._populate_devices()

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        layout.addWidget(self._progress)

        self._file_label = QLabel("No file selected")
        self._file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._file_label)

        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready")

        toolbar = QToolBar("Main")
        self.addToolBar(toolbar)
        toolbar.addAction("LoadPic", self._load_pic)
        toolbar.addAction("Transmit", self._transmit)
        toolbar.addAction("Receive", self._receive)
        toolbar.addAction("Abort", self._abort)

        context.event_bus.subscribe(SessionStateChangedEvent, self._on_state_changed)
        context.event_bus.subscribe(LogEvent, self._on_log)
        self._vm.progress_changed.connect(self._on_progress)
        self._vm.state_changed.connect(lambda s: self._status_label.setText(f"Session: {s}"))

    def _populate_devices(self) -> None:
        devices = self._context.audio_engine.list_devices()
        self._input_device.addItem("Default", None)
        self._output_device.addItem("Default", None)
        for dev in devices:
            label = f"{dev['index']}: {dev['name']}"
            if dev["max_input_channels"] > 0:
                self._input_device.addItem(label, dev["index"])
            if dev["max_output_channels"] > 0:
                self._output_device.addItem(label, dev["index"])

    def _apply_device_selection(self) -> None:
        self._context.config.audio.input_device = self._input_device.currentData()
        self._context.config.audio.output_device = self._output_device.currentData()

    def _load_pic(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select image or file",
            "",
            "Images (*.png *.jpg *.jpeg *.gif);;All files (*.*)",
        )
        if path:
            self._selected_file = Path(path)
            self._file_label.setText(self._selected_file.name)

    def _transmit(self) -> None:
        if self._selected_file is None:
            QMessageBox.warning(self, "Transmit", "Select a file with LoadPic first.")
            return
        if self._context.transfer_engine.state != SessionState.IDLE:
            QMessageBox.warning(self, "Transmit", "Transfer already in progress.")
            return
        self._apply_device_selection()
        try:
            self._context.transfer_engine.start_tx(self._selected_file)
        except Exception as exc:
            QMessageBox.critical(self, "Transmit", str(exc))

    def _receive(self) -> None:
        if self._context.transfer_engine.state != SessionState.IDLE:
            QMessageBox.warning(self, "Receive", "Transfer already in progress.")
            return
        self._apply_device_selection()
        out_dir = user_gallery_dir()
        try:
            self._context.transfer_engine.start_rx(out_dir)
        except Exception as exc:
            QMessageBox.critical(self, "Receive", str(exc))

    def _abort(self) -> None:
        self._context.transfer_engine.abort()

    def _on_state_changed(self, event: SessionStateChangedEvent) -> None:
        self._status_label.setText(f"Session: {event.state.value}")
        self.statusBar().showMessage(f"State → {event.state.value}", 5000)

    def _on_log(self, event: LogEvent) -> None:
        self.statusBar().showMessage(event.message, 8000)

    def _on_progress(self, pct: float, done: int, total: int) -> None:
        self._progress.setValue(int(pct))
        self.statusBar().showMessage(f"Progress: {done}/{total} ({pct:.1f}%)", 3000)
