"""Main application window."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QCloseEvent, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from easypal_next import __version__
from easypal_next.app.bootstrap import AppContext
from easypal_next.app.paths import brand_icon_path, brand_logo_path
from easypal_next.config.loader import save_config
from easypal_next.core.events import GalleryUpdatedEvent, LogEvent
from easypal_next.core.session import SessionState
from easypal_next.network.util import preferred_gallery_url
from easypal_next.ui.menus import build_menus, build_toolbar
from easypal_next.ui.session_relay import SessionStateRelay
from easypal_next.ui.theme import apply_theme
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
        self.setMinimumSize(960, 600)

        self._gallery_url = preferred_gallery_url(context.config.network.port)
        self._actions = build_menus(self, self._gallery_url)
        build_toolbar(self, self._actions)

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(6, 4, 6, 4)
        root.setSpacing(4)

        transfer_box = QGroupBox("Transfer")
        transfer_layout = QVBoxLayout(transfer_box)
        transfer_layout.setContentsMargins(6, 4, 6, 4)
        transfer_layout.setSpacing(2)
        self._file_label = QLabel("No file selected")
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setVisible(False)
        transfer_layout.addWidget(self._file_label)
        transfer_layout.addWidget(self._progress)
        gallery_row = QHBoxLayout()
        gallery_row.setSpacing(6)
        self._gallery_btn = self._gallery_button("Open Gallery", self._gallery_url)
        gallery_row.addWidget(self._gallery_btn)
        gallery_row.addStretch()
        transfer_layout.addLayout(gallery_row)
        transfer_box.setMaximumHeight(80)
        root.addWidget(transfer_box)

        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setChildrenCollapsible(False)

        gallery_box = QGroupBox("Gallery")
        gallery_layout = QVBoxLayout(gallery_box)
        gallery_layout.setContentsMargins(4, 4, 4, 4)
        self._rx_pane = RxPane(context.gallery)
        gallery_layout.addWidget(self._rx_pane)
        main_splitter.addWidget(gallery_box)

        waterfall_box = QGroupBox("Waterfall")
        waterfall_layout = QVBoxLayout(waterfall_box)
        waterfall_layout.setContentsMargins(4, 4, 4, 4)
        self._waterfall = WaterfallWidget(context.event_bus, context.config.waterfall)
        waterfall_layout.addWidget(self._waterfall)
        main_splitter.addWidget(waterfall_box)
        main_splitter.setStretchFactor(0, 45)
        main_splitter.setStretchFactor(1, 55)

        footer_splitter = QSplitter(Qt.Orientation.Horizontal)
        footer_splitter.setChildrenCollapsible(False)
        footer_splitter.setMaximumHeight(100)

        wftxt_box = QGroupBox("WFTxt")
        wftxt_layout = QVBoxLayout(wftxt_box)
        wftxt_layout.setContentsMargins(6, 4, 6, 4)
        self._wftxt = WaterfallTextEditor(context.config.waterfall)
        wftxt_layout.addWidget(self._wftxt)
        footer_splitter.addWidget(wftxt_box)

        log_box = QGroupBox("Log")
        log_layout = QVBoxLayout(log_box)
        log_layout.setContentsMargins(6, 4, 6, 4)
        self._log_panel = LogPanel(
            context.event_bus,
            dark=context.config.ui.theme == "dark",
        )
        log_layout.addWidget(self._log_panel)
        footer_splitter.addWidget(log_box)
        footer_splitter.setStretchFactor(0, 1)
        footer_splitter.setStretchFactor(1, 1)

        body_splitter = QSplitter(Qt.Orientation.Vertical)
        body_splitter.setChildrenCollapsible(False)
        body_splitter.addWidget(main_splitter)
        body_splitter.addWidget(footer_splitter)
        body_splitter.setStretchFactor(0, 1)
        body_splitter.setStretchFactor(1, 0)
        root.addWidget(body_splitter, stretch=1)

        self.setCentralWidget(central)
        self._build_status_bar()
        self._connect_actions()
        self._sync_theme_checks()
        self._actions.waterfall_tx_on_file.setChecked(context.config.waterfall.enabled)
        self._actions.live_waterfall.setChecked(context.config.waterfall.live_enabled)
        self._actions.auto_rx.setChecked(context.config.transfer.auto_rx)
        self._sync_auto_rx_action_state()
        self._waterfall.set_session_context(
            SessionState.IDLE,
            context.config.transfer.loopback_mode,
            context.config.transfer.radio_emission,
        )
        self._update_tune_action_state()
        self._update_status_text()

        context.event_bus.subscribe(LogEvent, self._on_log)
        context.event_bus.subscribe(GalleryUpdatedEvent, self._on_gallery_updated)
        self._state_relay = SessionStateRelay(context.event_bus, self)
        self._state_relay.state_changed.connect(
            self._on_state_changed,
            Qt.ConnectionType.QueuedConnection,
        )
        self._vm.progress_changed.connect(self._on_progress)
        self._vm.state_changed.connect(self._on_vm_state)

        if not context.config.transfer.loopback_mode:
            try:
                engine = getattr(context.transfer_backend, "engine_name", "freedv")
                # HamDRM owns WinMM capture; FreeDV uses PortAudio via TransferEngine.
                if engine == "freedv":
                    context.transfer_engine.start_audio_monitor()
                if context.config.transfer.auto_rx:
                    context.transfer_backend.start_always_on_rx()
                    self._actions.auto_rx.setChecked(True)
            except Exception as exc:
                self.statusBar().showMessage(f"Audio monitor / Auto RX failed: {exc}", 8000)
            if context.hamdrm_fell_back and context.hamdrm_unavailable_reason:
                self.statusBar().showMessage(
                    f"HamDRM unavailable — using FreeDV. {context.hamdrm_unavailable_reason}",
                    12000,
                )
            elif getattr(context.transfer_backend, "engine_name", "") == "hamdrm":
                self.statusBar().showMessage("HamDRM engine active", 6000)

        self._fit_to_screen()

    def _gallery_button(self, label: str, url: str) -> QPushButton:
        btn = QPushButton(label)
        btn.setObjectName("galleryButton")
        btn.setToolTip(url)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(url)))
        return btn

    def _build_status_bar(self) -> None:
        bar = QStatusBar()
        self.setStatusBar(bar)
        self._status_main = QLabel()
        bar.addWidget(self._status_main, stretch=1)
        bar.addPermanentWidget(self._gallery_button("Open Gallery", self._gallery_url))

    def _connect_actions(self) -> None:
        a = self._actions
        a.load_pic.triggered.connect(self._load_pic)
        a.preferences.triggered.connect(self._open_settings)
        a.exit_app.triggered.connect(self.close)
        a.transmit.triggered.connect(self._transmit)
        a.receive.triggered.connect(self._receive)
        a.tune.toggled.connect(self._toggle_tune)
        a.abort.triggered.connect(self._abort)
        a.send_wftxt.triggered.connect(self._send_wftxt)
        a.waterfall_tx_on_file.toggled.connect(self._on_waterfall_toggled)
        a.live_waterfall.toggled.connect(self._on_live_waterfall_toggled)
        a.auto_rx.toggled.connect(self._on_auto_rx_toggled)
        a.theme_light.triggered.connect(lambda: self._set_theme("light"))
        a.theme_dark.triggered.connect(lambda: self._set_theme("dark"))
        a.open_gallery.triggered.connect(
            lambda: QDesktopServices.openUrl(QUrl(self._gallery_url))
        )
        a.about.triggered.connect(self._show_about)
        self._wftxt.send_requested.connect(self._send_wftxt)

    def _sync_auto_rx_action_state(self) -> None:
        loopback = self._context.config.transfer.loopback_mode
        self._actions.auto_rx.setEnabled(not loopback)
        if loopback:
            self._actions.auto_rx.setToolTip("Auto RX requires on-air mode")
        else:
            self._actions.auto_rx.setToolTip(
                "Always-on RX — listen continuously like original EasyPal (pictures arrive automatically)"
            )

    def _on_live_waterfall_toggled(self, checked: bool) -> None:
        self._context.config.waterfall.live_enabled = checked
        save_config(self._context.config)
        self._waterfall.set_live_enabled(checked)

    def _on_auto_rx_toggled(self, checked: bool) -> None:
        if self._context.config.transfer.loopback_mode:
            self._actions.auto_rx.setChecked(False)
            QMessageBox.warning(
                self,
                "Auto RX",
                "Auto RX requires on-air mode. Disable loopback in Settings and restart.",
            )
            return
        self._context.config.transfer.auto_rx = checked
        save_config(self._context.config)
        if checked:
            try:
                self._context.transfer_backend.start_always_on_rx()
            except Exception as exc:
                self._actions.auto_rx.setChecked(False)
                QMessageBox.critical(self, "Auto RX", str(exc))
        else:
            try:
                self._context.transfer_backend.stop_rx()
            except Exception:
                if self._context.transfer_engine.state == SessionState.RX_LISTEN:
                    self._context.transfer_engine.abort()

    def _update_tune_action_state(self) -> None:
        loopback = self._context.config.transfer.loopback_mode
        state = self._context.transfer_engine.state
        tuning = state == SessionState.TUNING
        self._actions.tune.setEnabled(
            not loopback and state in (SessionState.IDLE, SessionState.TUNING)
        )
        self._actions.tune.blockSignals(True)
        self._actions.tune.setChecked(tuning)
        self._actions.tune.blockSignals(False)
        emission = self._context.config.transfer.radio_emission.upper()
        if loopback:
            tip = "Tune requires on-air mode — disable loopback in Settings"
        else:
            tip = f"F8 — loop modem preamble on-air ({emission}) to align audio levels"
        self._actions.tune.setToolTip(tip)

    def _toggle_tune(self, checked: bool) -> None:
        if self._context.config.transfer.loopback_mode:
            self._actions.tune.setChecked(False)
            QMessageBox.warning(
                self,
                "Tune",
                "Tune is only available in on-air mode. Disable loopback in Settings and restart.",
            )
            return
        state = self._context.transfer_engine.state
        if checked:
            if state != SessionState.IDLE:
                self._actions.tune.setChecked(False)
                return
            try:
                self._context.transfer_engine.start_tune()
            except Exception as exc:
                self._actions.tune.setChecked(False)
                QMessageBox.critical(self, "Tune", str(exc))
        elif state == SessionState.TUNING:
            self._context.transfer_engine.stop_tune()

    def _fit_to_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            self.showMaximized()
            return
        geo = screen.availableGeometry()
        self.setGeometry(geo)
        self.showMaximized()

    def _sync_theme_checks(self) -> None:
        is_light = self._context.config.ui.theme == "light"
        self._actions.theme_light.setChecked(is_light)
        self._actions.theme_dark.setChecked(not is_light)

    def _set_theme(self, theme: str) -> None:
        self._context.config.ui.theme = theme
        save_config(self._context.config)
        app = QApplication.instance()
        if app is not None:
            apply_theme(app, theme)
        self._log_panel.set_dark(theme == "dark")
        self._sync_theme_checks()

    def _update_status_text(self) -> None:
        cfg = self._context.config
        mode = "loopback" if cfg.transfer.loopback_mode else "on-air"
        state = self._context.transfer_engine.state.value
        backend_engine = getattr(self._context.transfer_backend, "engine_name", cfg.modem.engine)
        engine = backend_engine
        if self._context.hamdrm_fell_back:
            engine = f"{engine} (HamDRM fallback)"
        listening = (
            not cfg.transfer.loopback_mode
            and cfg.transfer.auto_rx
            and (
                state in ("idle", "rx_listen", "rx_assembling")
                or backend_engine == "hamdrm"
            )
        )
        listen = " · listening" if listening else ""
        sync = ""
        if backend_engine == "hamdrm" and not self._context.hamdrm_fell_back:
            try:
                s = self._context.transfer_backend.get_sync_state()
                parts = []
                if s.snr_db is not None:
                    parts.append(f"SNR {s.snr_db:.0f} dB")
                if s.fac:
                    parts.append("FAC")
                if s.msc:
                    parts.append("MSC")
                if parts:
                    sync = " · " + " ".join(parts)
            except Exception:
                pass
        file_part = f" · {self._selected_file.name}" if self._selected_file else ""
        self._status_main.setText(
            f"{cfg.callsign} · {engine} · {cfg.modem.mode} · {mode} · {state}{listen}{sync}{file_part}"
        )

    def _persist_waterfall_config(self) -> None:
        self._wftxt.apply_to_config(self._context.config.waterfall)
        self._context.config.waterfall.enabled = self._actions.waterfall_tx_on_file.isChecked()
        save_config(self._context.config)

    def _on_waterfall_toggled(self, checked: bool) -> None:
        self._context.config.waterfall.enabled = checked
        save_config(self._context.config)

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self._context, self)
        if dialog.exec():
            cfg = self._context.config
            loopback_before = cfg.transfer.loopback_mode
            audio_before = (
                cfg.audio.input_device,
                cfg.audio.output_device,
                cfg.audio.sample_rate,
                cfg.audio.block_size,
            )
            waterfall_before = (
                cfg.waterfall.fft_size,
                cfg.waterfall.fft_overlap,
                cfg.waterfall.fft_window,
            )
            config = dialog.apply()
            loopback_after = config.transfer.loopback_mode
            audio_after = (
                config.audio.input_device,
                config.audio.output_device,
                config.audio.sample_rate,
                config.audio.block_size,
            )
            waterfall_after = (
                config.waterfall.fft_size,
                config.waterfall.fft_overlap,
                config.waterfall.fft_window,
            )
            needs_audio_refresh = (
                loopback_before != loopback_after
                or not loopback_after
                or audio_before != audio_after
                or waterfall_before != waterfall_after
            )
            if needs_audio_refresh:
                self._context.refresh_modem_bridge()
            else:
                self._context.transfer_engine.reload_spectrum_tap()
            self._wftxt.sync_from_config(config.waterfall)
            self._waterfall.update_config(config.waterfall)
            self._actions.waterfall_tx_on_file.setChecked(config.waterfall.enabled)
            self._actions.live_waterfall.setChecked(config.waterfall.live_enabled)
            self._waterfall.set_live_enabled(config.waterfall.live_enabled)
            self._actions.auto_rx.setChecked(config.transfer.auto_rx)
            self._sync_auto_rx_action_state()
            if config.transfer.auto_rx and not config.transfer.loopback_mode:
                self._context.transfer_backend.start_always_on_rx()
            self._update_tune_action_state()
            if config.ui.theme != self._context.config.ui.theme:
                self._set_theme(config.ui.theme)
            self._update_status_text()
            QMessageBox.information(
                self,
                "Settings",
                "Settings saved. Restart for engine, loopback/on-air, and path changes.",
            )

    def _load_pic(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "LoadPic — select image or file",
            "",
            "Images (*.png *.jpg *.jpeg *.gif);;All files (*.*)",
        )
        if path:
            self._selected_file = Path(path)
            self._file_label.setText(self._selected_file.name)
            self._update_status_text()

    def _transmit(self) -> None:
        if self._selected_file is None:
            QMessageBox.warning(self, "Transmit", "LoadPic first — select a file to transmit.")
            return
        backend = self._context.transfer_backend
        if getattr(backend, "engine_name", "") == "hamdrm":
            self._persist_waterfall_config()
            try:
                backend.transmit_file(self._selected_file)
                self.statusBar().showMessage(f"HamDRM TX: {self._selected_file.name}", 5000)
                self._update_status_text()
            except Exception as exc:
                QMessageBox.critical(self, "Transmit", str(exc))
            return
        if self._context.transfer_engine.state != SessionState.IDLE:
            QMessageBox.warning(self, "Transmit", "Transfer already in progress.")
            return
        self._persist_waterfall_config()
        try:
            self._context.transfer_engine.start_tx(self._selected_file)
        except Exception as exc:
            QMessageBox.critical(self, "Transmit", str(exc))

    def _send_wftxt(self) -> None:
        if self._context.transfer_engine.state != SessionState.IDLE:
            QMessageBox.warning(self, "Send WFTxt", "Transfer already in progress.")
            return
        self._persist_waterfall_config()
        message = self._wftxt.begin_message()
        if not message.strip():
            QMessageBox.warning(self, "Send WFTxt", "Enter a message in the WFTxt field.")
            return
        self._wftxt.set_transmitting(True)
        try:
            self._context.transfer_engine.start_waterfall_tx(message)
        except Exception as exc:
            self._wftxt.set_transmitting(False)
            QMessageBox.critical(self, "Send WFTxt", str(exc))

    def _receive(self) -> None:
        if self._context.config.transfer.loopback_mode:
            QMessageBox.warning(
                self,
                "Receive",
                "Receive / always-on RX requires on-air mode. Disable loopback in Settings.",
            )
            return
        if self._context.transfer_engine.state not in (SessionState.IDLE, SessionState.RX_LISTEN):
            QMessageBox.warning(self, "Receive", "Transfer already in progress.")
            return
        try:
            self._context.config.transfer.auto_rx = True
            save_config(self._context.config)
            self._actions.auto_rx.setChecked(True)
            self._context.transfer_backend.start_always_on_rx()
            self.statusBar().showMessage("Listening for incoming transfers…", 5000)
            self._update_status_text()
        except Exception as exc:
            QMessageBox.critical(self, "Receive", str(exc))

    def _abort(self) -> None:
        try:
            self._context.transfer_backend.abort()
        except Exception:
            self._context.transfer_engine.abort()

    def _show_about(self) -> None:
        logo = brand_logo_path()
        icon = brand_icon_path()
        QMessageBox.about(
            self,
            "About EasyPal-Next",
            f"<b>EasyPal-Next</b> v{__version__}<br>"
            "Digital SSTV successor — Shane Daley M0VUB (ShaYmez)<br><br>"
            f"Gallery: {self._gallery_url}",
        )

    def _on_state_changed(self, state: SessionState) -> None:
        self._waterfall.set_session_context(
            state,
            self._context.config.transfer.loopback_mode,
            self._context.config.transfer.radio_emission,
        )
        if state == SessionState.IDLE:
            self._wftxt.set_transmitting(False)
        self._update_tune_action_state()
        self._update_status_text()
        self.statusBar().showMessage(f"State → {state.value}", 4000)

    def _on_vm_state(self, state: str) -> None:
        self._update_status_text()

    def _on_log(self, event: LogEvent) -> None:
        self.statusBar().showMessage(event.message, 6000)

    def _on_progress(self, pct: float, done: int, total: int) -> None:
        visible = pct > 0 or total > 0
        self._progress.setVisible(visible)
        self._progress.setValue(int(pct))
        if visible:
            self.statusBar().showMessage(f"Progress: {done}/{total} ({pct:.1f}%)", 3000)

    def _on_gallery_updated(self, event: GalleryUpdatedEvent) -> None:
        self._rx_pane.add_entry(event.image_id)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        self._context.transfer_engine.abort()
        super().closeEvent(event)
