"""Main application window."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from easypal_next.app.bootstrap import AppContext
from easypal_next.app.paths import brand_icon_path, brand_logo_path
from easypal_next.core.events import GalleryUpdatedEvent, LogEvent, SessionStateChangedEvent
from easypal_next.core.session import SessionState
from easypal_next.network.util import gallery_urls
from easypal_next.ui.view_models.transfer_vm import TransferViewModel
from easypal_next.ui.widgets.log_panel import LogPanel
from easypal_next.ui.widgets.rx_pane import RxPane
from easypal_next.ui.widgets.settings_dialog import SettingsDialog
from easypal_next.ui.widgets.waterfall_text_editor import WaterfallTextEditor
from easypal_next.ui.widgets.waterfall_widget import WaterfallWidget


class MainWindow(QMainWindow):
    def __init__(self, context: AppContext) -> None:
        super().__init__()
        self._context = context
        self._selected_file: Path | None = None
        self._vm = TransferViewModel(context.event_bus)
        self.setWindowTitle("EasyPal-Next")
        self.setMinimumSize(880, 560)
        self._fit_to_available_screen()
        self.setStyleSheet(
            "QMainWindow { background-color: #0f1419; }"
            "QLabel { color: #e7ecf3; }"
            "QToolBar { background: #1a3a5c; spacing: 8px; }"
            "QProgressBar::chunk { background-color: #f5c518; }"
        )

        central = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        layout = QVBoxLayout(central)

        brand_row = QHBoxLayout()
        logo_path = brand_logo_path()
        icon_path = brand_icon_path()
        if logo_path.is_file():
            logo_label = QLabel()
            logo_label.setPixmap(
                QPixmap(str(logo_path)).scaledToHeight(
                    48, Qt.TransformationMode.SmoothTransformation
                )
            )
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            brand_row.addWidget(logo_label)
        elif icon_path.is_file():
            icon_label = QLabel()
            icon_label.setPixmap(
                QPixmap(str(icon_path)).scaled(
                    64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
                )
            )
            brand_row.addWidget(icon_label)
            title = QLabel("EasyPal-Next")
            title.setStyleSheet("font-size: 28px; font-weight: bold; color: #f5c518;")
            brand_row.addWidget(title)
        brand_row.addStretch()
        layout.addLayout(brand_row)

        header = QLabel(
            f"{context.config.callsign} · {context.config.modem.mode}"
            f" · {'loopback' if context.config.transfer.loopback_mode else 'on-air'}"
        )
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        local_url, lan_url = gallery_urls(context.config.network.port)
        gallery_lines = [f"Laptop gallery: {local_url}"]
        if lan_url:
            gallery_lines.append(f"Phone/tablet: {lan_url}")
        self._gallery_info = QLabel(" · ".join(gallery_lines))
        self._gallery_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._gallery_info.setWordWrap(True)
        layout.addWidget(self._gallery_info)

        self._status_label = QLabel("Session: idle")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status_label)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        layout.addWidget(self._progress)

        self._file_label = QLabel("No file selected")
        self._file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._file_label)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        self._rx_pane = RxPane(context.gallery)
        self._waterfall = WaterfallWidget(context.event_bus)
        splitter.addWidget(self._rx_pane)
        splitter.addWidget(self._waterfall)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([1, 1])
        layout.addWidget(splitter, stretch=1)

        bottom = QHBoxLayout()
        self._wftxt = WaterfallTextEditor(context.config.waterfall)
        self._wftxt.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        bottom.addWidget(self._wftxt, stretch=1)
        self._log_panel = LogPanel(context.event_bus)
        self._log_panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        bottom.addWidget(self._log_panel, stretch=2)
        layout.addLayout(bottom)

        scroll.setWidget(central)
        self.setCentralWidget(scroll)
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready")

        toolbar = QToolBar("Main")
        self.addToolBar(toolbar)
        toolbar.addAction("LoadPic", self._load_pic)
        toolbar.addAction("Transmit", self._transmit)
        toolbar.addAction("Receive", self._receive)
        toolbar.addAction("Abort", self._abort)
        toolbar.addAction("Settings", self._open_settings)

        context.event_bus.subscribe(SessionStateChangedEvent, self._on_state_changed)
        context.event_bus.subscribe(LogEvent, self._on_log)
        context.event_bus.subscribe(GalleryUpdatedEvent, self._on_gallery_updated)
        self._vm.progress_changed.connect(self._on_progress)
        self._vm.state_changed.connect(lambda s: self._status_label.setText(f"Session: {s}"))

    def _fit_to_available_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            self.resize(1024, 700)
            return
        available = screen.availableGeometry()
        width = min(1100, max(880, int(available.width() * 0.92)))
        height = min(820, max(560, int(available.height() * 0.88)))
        self.resize(width, height)
        frame = self.frameGeometry()
        frame.moveCenter(available.center())
        self.move(frame.topLeft())

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self._context, self)
        if dialog.exec():
            config = dialog.apply()
            self._wftxt.apply_to_config(config.waterfall)
            self._status_label.setText(
                f"Session: idle · {'loopback' if config.transfer.loopback_mode else 'on-air'}"
            )
            QMessageBox.information(
                self,
                "Settings",
                "Settings saved. Restart the app for loopback/on-air mode changes to take full effect.",
            )

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
        self._wftxt.apply_to_config(self._context.config.waterfall)
        try:
            self._context.transfer_engine.start_tx(self._selected_file)
        except Exception as exc:
            QMessageBox.critical(self, "Transmit", str(exc))

    def _receive(self) -> None:
        if self._context.transfer_engine.state != SessionState.IDLE:
            QMessageBox.warning(self, "Receive", "Transfer already in progress.")
            return
        out_dir = self._context.gallery.received_dir()
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

    def _on_gallery_updated(self, event: GalleryUpdatedEvent) -> None:
        self._rx_pane.add_entry(event.image_id)
