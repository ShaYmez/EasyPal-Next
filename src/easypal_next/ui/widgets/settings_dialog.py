"""Application settings dialog with tabbed configuration."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from easypal_next.app.bootstrap import AppContext
from easypal_next.app.paths import user_gallery_dir
from easypal_next.config.loader import save_config
from easypal_next.config.schema import AppConfig, CatRadioConfig, SerialPttConfig, VoxManualConfig
from easypal_next.radio.serial_ports import list_serial_ports


class SettingsDialog(QDialog):
    def __init__(self, context: AppContext, parent=None) -> None:
        super().__init__(parent)
        self._context = context
        self.setWindowTitle("EasyPal-Next Settings")
        self.setMinimumSize(520, 420)

        cfg = context.config
        tabs = QTabWidget()

        tabs.addTab(self._build_general_tab(cfg), "General")
        tabs.addTab(self._build_transfer_tab(cfg), "Transfer")
        tabs.addTab(self._build_audio_tab(cfg), "Audio")
        tabs.addTab(self._build_radio_tab(cfg), "Radio")
        tabs.addTab(self._build_waterfall_tab(cfg), "Waterfall")
        tabs.addTab(self._build_appearance_tab(cfg), "Appearance")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(tabs)
        layout.addWidget(buttons)

    def _build_general_tab(self, cfg: AppConfig) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)

        self._callsign = QLineEdit(cfg.callsign)
        self._loopback = QCheckBox("Loopback mode (no PTT / sound card for modem test)")
        self._loopback.setChecked(cfg.transfer.loopback_mode)

        default_gallery = str(user_gallery_dir())
        self._gallery_dir = QLineEdit(cfg.network.gallery_dir or default_gallery)
        gallery_row = QHBoxLayout()
        gallery_row.addWidget(self._gallery_dir)
        gallery_browse = QPushButton("Browse…")
        gallery_browse.clicked.connect(lambda: self._browse_dir(self._gallery_dir))
        gallery_row.addWidget(gallery_browse)

        received_default = str(Path(self._gallery_dir.text()).parent / "received")
        self._received_dir = QLineEdit(cfg.network.received_dir or received_default)
        received_row = QHBoxLayout()
        received_row.addWidget(self._received_dir)
        received_browse = QPushButton("Browse…")
        received_browse.clicked.connect(lambda: self._browse_dir(self._received_dir))
        received_row.addWidget(received_browse)

        form.addRow("Callsign:", self._callsign)
        form.addRow(self._loopback)
        form.addRow("Gallery directory:", gallery_row)
        form.addRow("Received files directory:", received_row)
        form.addRow(
            QLabel("Restart the app after changing paths or loopback mode.")
        )
        return widget

    def _build_transfer_tab(self, cfg: AppConfig) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)

        self._engine = QComboBox()
        self._engine.addItem("HamDRM (original EasyPal compatible)", "hamdrm")
        self._engine.addItem("FreeDV DATAC3 (experimental)", "freedv")
        eng_idx = self._engine.findData(cfg.modem.engine)
        if eng_idx >= 0:
            self._engine.setCurrentIndex(eng_idx)
        self._engine.setToolTip(
            "HamDRM uses EasyPal's run.dll / hamdrm.dll. Requires a 64-bit DLL "
            "(or future 32-bit bridge). Falls back to FreeDV if unavailable."
        )

        self._hamdrm_dll = QLineEdit(cfg.modem.hamdrm_dll_path or "")
        self._hamdrm_dll.setPlaceholderText(r"C:\Program Files\EasyPal\run.dll")
        dll_row = QHBoxLayout()
        dll_row.addWidget(self._hamdrm_dll)
        dll_browse = QPushButton("Browse…")
        dll_browse.clicked.connect(self._browse_hamdrm_dll)
        dll_row.addWidget(dll_browse)

        self._hamdrm_mode = QComboBox()
        for mode in ("A", "B", "E"):
            self._hamdrm_mode.addItem(f"Mode {mode}", mode)
        mode_idx = self._hamdrm_mode.findData(cfg.modem.hamdrm_mode)
        if mode_idx >= 0:
            self._hamdrm_mode.setCurrentIndex(mode_idx)

        self._hamdrm_qam = QComboBox()
        for qam in (4, 16, 64):
            self._hamdrm_qam.addItem(f"QAM {qam}", qam)
        qam_idx = self._hamdrm_qam.findData(cfg.modem.hamdrm_qam)
        if qam_idx >= 0:
            self._hamdrm_qam.setCurrentIndex(qam_idx)

        self._hamdrm_leadin = QSpinBox()
        self._hamdrm_leadin.setRange(1, 64)
        self._hamdrm_leadin.setValue(cfg.modem.hamdrm_start_delay)
        self._hamdrm_leadin.setToolTip("DRM lead-in / start delay (original default ~24)")

        form.addRow(QLabel("<b>Transfer engine</b>"))
        form.addRow("Engine:", self._engine)
        form.addRow("HamDRM DLL:", dll_row)
        form.addRow("DRM mode:", self._hamdrm_mode)
        form.addRow("QAM:", self._hamdrm_qam)
        form.addRow("Lead-in:", self._hamdrm_leadin)

        self._pace_ms = QSpinBox()
        self._pace_ms.setRange(0, 100)
        self._pace_ms.setSuffix(" ms")
        self._pace_ms.setValue(cfg.transfer.pace_ms)
        self._pace_ms.setToolTip(
            "Delay after each modem burst. 0 = fastest (recommended for loopback). "
            "Use 5–20 ms on-air only if the radio buffer overflows."
        )

        self._fec_chunk = QComboBox()
        for size in (1024, 2048, 4096, 8192):
            self._fec_chunk.addItem(f"{size} bytes", size)
        idx = self._fec_chunk.findData(cfg.fec.chunk_size)
        if idx >= 0:
            self._fec_chunk.setCurrentIndex(idx)
        else:
            self._fec_chunk.setEditText(str(cfg.fec.chunk_size))

        self._fec_preset = QComboBox()
        self._fec_preset.addItem("Standard (balanced)", "standard")
        self._fec_preset.addItem("Faster — larger chunks", "faster")
        self._fec_preset.addItem("Fastest — large chunks, pace 0", "fastest")
        self._fec_preset.currentIndexChanged.connect(self._apply_fec_preset)

        self._tune_max_seconds = QSpinBox()
        self._tune_max_seconds.setRange(1, 5)
        self._tune_max_seconds.setSuffix(" s")
        self._tune_max_seconds.setValue(min(5, cfg.transfer.tune_max_seconds))
        self._tune_max_seconds.setToolTip(
            "Maximum duration for on-air Tune (720/1466/1840 Hz three-tone). Hard-capped at 5 s."
        )

        self._radio_emission = QComboBox()
        for label, value in (
            ("FM (SignaLink / data VOX)", "fm"),
            ("AM (low drive)", "am"),
            ("SSB / USB (HF voice)", "ssb"),
        ):
            self._radio_emission.addItem(label, value)
        idx_em = self._radio_emission.findData(cfg.transfer.radio_emission)
        if idx_em >= 0:
            self._radio_emission.setCurrentIndex(idx_em)
        self._radio_emission.setToolTip(
            "Guides Tune hints on the waterfall. RF mode is set on the radio; DATAC3 modem is unchanged."
        )

        self._auto_rx = QCheckBox("Always-on Auto RX (recommended — like original EasyPal)")
        self._auto_rx.setChecked(cfg.transfer.auto_rx)
        self._auto_rx.setToolTip(
            "When enabled in on-air mode, listen continuously so pictures arrive "
            "automatically without clicking Receive."
        )

        self._callsign_header = QCheckBox(
            "Transmit callsign as WFTxt before Tune / file TX / WFTxt (on-air)"
        )
        self._callsign_header.setChecked(cfg.transfer.require_callsign_wftxt_header)
        self._callsign_header.setToolTip(
            "Paints your callsign (or N0CALL if blank) on the waterfall before "
            "Tune tone, file transmit, or WFTxt body. Matches EasyPal on-air ID habit."
        )

        form.addRow("Burst pace:", self._pace_ms)
        form.addRow("FEC chunk size:", self._fec_chunk)
        form.addRow("Speed preset:", self._fec_preset)
        form.addRow("Tune timeout:", self._tune_max_seconds)
        form.addRow("Radio emission:", self._radio_emission)
        form.addRow(self._auto_rx)
        form.addRow(self._callsign_header)
        form.addRow(
            QLabel(
                "Tips: set pace to 0, use 4096-byte chunks, and disable "
                "Waterfall TX on file for quickest transfers."
            )
        )
        return widget

    def _apply_fec_preset(self) -> None:
        preset = self._fec_preset.currentData()
        if preset == "faster":
            self._set_fec_chunk(4096)
            self._pace_ms.setValue(0)
        elif preset == "fastest":
            self._set_fec_chunk(8192)
            self._pace_ms.setValue(0)

    def _set_fec_chunk(self, size: int) -> None:
        idx = self._fec_chunk.findData(size)
        if idx >= 0:
            self._fec_chunk.setCurrentIndex(idx)

    def _build_audio_tab(self, cfg: AppConfig) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)

        self._input_device = QComboBox()
        self._output_device = QComboBox()
        self._populate_devices(cfg)

        self._sample_rate = QSpinBox()
        self._sample_rate.setRange(8000, 192000)
        self._sample_rate.setSingleStep(1000)
        self._sample_rate.setValue(cfg.audio.sample_rate)

        self._block_size = QSpinBox()
        self._block_size.setRange(256, 8192)
        self._block_size.setSingleStep(256)
        self._block_size.setValue(cfg.audio.block_size)

        form.addRow("Audio input:", self._input_device)
        form.addRow("Audio output:", self._output_device)
        form.addRow("Sample rate:", self._sample_rate)
        form.addRow("Block size:", self._block_size)
        return widget

    def _build_radio_tab(self, cfg: AppConfig) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self._radio_profile = QComboBox()
        self._radio_profile.addItem("VOX / Manual PTT", "vox")
        self._radio_profile.addItem("Serial PTT", "serial")
        self._radio_profile.addItem("Hamlib CAT", "cat")
        current = getattr(cfg.radio, "profile", "vox")
        for i in range(self._radio_profile.count()):
            if self._radio_profile.itemData(i) == current:
                self._radio_profile.setCurrentIndex(i)

        self._com_port = QComboBox()
        self._com_port.setEditable(True)
        initial_port = getattr(cfg.radio, "port", "")
        self._refresh_ports(initial_port or None)

        self._vox_pre = QSpinBox()
        self._vox_pre.setRange(0, 5000)
        self._vox_pre.setSuffix(" ms")
        self._vox_post = QSpinBox()
        self._vox_post.setRange(0, 5000)
        self._vox_post.setSuffix(" ms")

        self._serial_line = QComboBox()
        self._serial_line.addItems(["RTS", "DTR"])
        self._serial_active_low = QCheckBox("Active low")
        self._serial_baud = QSpinBox()
        self._serial_baud.setRange(1200, 115200)
        self._serial_baud.setValue(9600)

        self._cat_rig_model = QSpinBox()
        self._cat_rig_model.setRange(1, 99999)
        self._cat_rig_model.setValue(3073)
        self._cat_baud = QSpinBox()
        self._cat_baud.setRange(1200, 115200)
        self._cat_baud.setValue(115200)
        self._cat_ptt_method = QComboBox()
        self._cat_ptt_method.addItem("Data PTT", "data")
        self._cat_ptt_method.addItem("Rig PTT", "rig")

        if isinstance(cfg.radio, VoxManualConfig):
            self._vox_pre.setValue(cfg.radio.pre_tx_delay_ms)
            self._vox_post.setValue(cfg.radio.post_tx_delay_ms)
        elif isinstance(cfg.radio, SerialPttConfig):
            self._serial_line.setCurrentText(cfg.radio.line)
            self._serial_active_low.setChecked(cfg.radio.active_low)
            self._serial_baud.setValue(cfg.radio.baud)
        elif isinstance(cfg.radio, CatRadioConfig):
            self._cat_rig_model.setValue(cfg.radio.rig_model)
            self._cat_baud.setValue(cfg.radio.baud)
            idx = self._cat_ptt_method.findData(cfg.radio.ptt_method)
            if idx >= 0:
                self._cat_ptt_method.setCurrentIndex(idx)

        self._vox_group = QGroupBox("VOX timing")
        vox_form = QFormLayout(self._vox_group)
        vox_form.addRow("Pre-TX delay:", self._vox_pre)
        vox_form.addRow("Post-TX delay:", self._vox_post)

        port_row = QHBoxLayout()
        port_row.addWidget(self._com_port)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(lambda: self._refresh_ports(self._com_port.currentText()))
        port_row.addWidget(refresh_btn)
        self._port_row_widget = QWidget()
        port_form = QFormLayout(self._port_row_widget)
        port_form.addRow("COM port:", port_row)

        self._serial_group = QGroupBox("Serial PTT")
        serial_form = QFormLayout(self._serial_group)
        serial_form.addRow("PTT line:", self._serial_line)
        serial_form.addRow(self._serial_active_low)
        serial_form.addRow("Baud:", self._serial_baud)

        self._cat_group = QGroupBox("Hamlib CAT")
        cat_form = QFormLayout(self._cat_group)
        cat_form.addRow("Rig model ID:", self._cat_rig_model)
        cat_form.addRow("Baud:", self._cat_baud)
        cat_form.addRow("PTT method:", self._cat_ptt_method)

        form = QFormLayout()
        form.addRow("Radio profile:", self._radio_profile)
        profile_widget = QWidget()
        profile_widget.setLayout(form)

        layout.addWidget(profile_widget)
        layout.addWidget(self._port_row_widget)
        layout.addWidget(self._vox_group)
        layout.addWidget(self._serial_group)
        layout.addWidget(self._cat_group)
        layout.addStretch()

        self._radio_profile.currentIndexChanged.connect(self._update_radio_visibility)
        self._update_radio_visibility()
        return widget

    def _build_waterfall_tab(self, cfg: AppConfig) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)

        self._wf_enabled = QCheckBox("Enable waterfall header/footer on file TX")
        self._wf_enabled.setChecked(cfg.waterfall.enabled)
        self._wf_live = QCheckBox("Enable live waterfall spectrum display")
        self._wf_live.setChecked(cfg.waterfall.live_enabled)
        self._wf_monitor = QCheckBox("Show live spectrum during TX (Tune always shows spectrum)")
        self._wf_monitor.setChecked(cfg.waterfall.tx_monitor)
        self._wf_begin = QLineEdit(cfg.waterfall.begin_message)
        self._wf_end = QLineEdit(cfg.waterfall.end_message)
        self._wf_font = QComboBox()
        self._wf_font.setEditable(True)
        self._wf_font.addItems(["DejaVu Sans Mono", "Consolas", "Courier New", "Arial"])
        font_idx = self._wf_font.findText(cfg.waterfall.default_font)
        if font_idx >= 0:
            self._wf_font.setCurrentIndex(font_idx)
        else:
            self._wf_font.setCurrentText(cfg.waterfall.default_font)
        self._wf_font_size = QSpinBox()
        self._wf_font_size.setRange(8, 48)
        self._wf_font_size.setValue(cfg.waterfall.default_font_size)
        self._wf_colormap = QComboBox()
        self._wf_colormap.addItem("Green", "green")
        self._wf_colormap.addItem("Heat", "heat")
        self._wf_colormap.addItem("Grayscale", "grayscale")
        cmap_idx = self._wf_colormap.findData(cfg.waterfall.colormap)
        if cmap_idx >= 0:
            self._wf_colormap.setCurrentIndex(cmap_idx)
        self._wf_min_db = QDoubleSpinBox()
        self._wf_min_db.setRange(-120.0, 0.0)
        self._wf_min_db.setValue(cfg.waterfall.min_db)
        self._wf_max_db = QDoubleSpinBox()
        self._wf_max_db.setRange(-60.0, 20.0)
        self._wf_max_db.setValue(cfg.waterfall.max_db)

        self._wf_fft_size = QComboBox()
        for size in (256, 512, 1024, 2048, 4096):
            self._wf_fft_size.addItem(str(size), size)
        fft_idx = self._wf_fft_size.findData(cfg.waterfall.fft_size)
        if fft_idx >= 0:
            self._wf_fft_size.setCurrentIndex(fft_idx)

        self._wf_fft_interval = QSpinBox()
        self._wf_fft_interval.setRange(16, 200)
        self._wf_fft_interval.setSuffix(" ms")
        self._wf_fft_interval.setToolTip("How often a new waterfall row is drawn (lower = faster scroll)")
        self._wf_fft_interval.setValue(cfg.waterfall.fft_interval_ms)

        self._wf_fft_window = QComboBox()
        self._wf_fft_window.addItem("Hann (recommended)", "hann")
        self._wf_fft_window.addItem("Hamming", "hamming")
        self._wf_fft_window.addItem("Blackman", "blackman")
        self._wf_fft_window.addItem("None (rectangular)", "none")
        win_idx = self._wf_fft_window.findData(cfg.waterfall.fft_window)
        if win_idx >= 0:
            self._wf_fft_window.setCurrentIndex(win_idx)

        self._wf_fft_overlap = QDoubleSpinBox()
        self._wf_fft_overlap.setRange(0.0, 0.875)
        self._wf_fft_overlap.setSingleStep(0.125)
        self._wf_fft_overlap.setToolTip("Overlap between FFT frames — higher = smoother, more CPU")
        self._wf_fft_overlap.setValue(cfg.waterfall.fft_overlap)

        self._wf_scroll_pixels = QSpinBox()
        self._wf_scroll_pixels.setRange(1, 8)
        self._wf_scroll_pixels.setToolTip("Lines to scroll per FFT frame — higher = faster waterfall")
        self._wf_scroll_pixels.setValue(cfg.waterfall.scroll_pixels)

        self._wf_history_rows = QSpinBox()
        self._wf_history_rows.setRange(64, 1024)
        self._wf_history_rows.setSingleStep(64)
        self._wf_history_rows.setToolTip("How many FFT lines of history to keep (time depth)")
        self._wf_history_rows.setValue(cfg.waterfall.history_rows)

        self._wf_freq_min = QSpinBox()
        self._wf_freq_min.setRange(0, 24000)
        self._wf_freq_min.setSuffix(" Hz")
        self._wf_freq_min.setValue(cfg.waterfall.freq_min_hz)

        self._wf_freq_max = QSpinBox()
        self._wf_freq_max.setRange(100, 48000)
        self._wf_freq_max.setSuffix(" Hz")
        self._wf_freq_max.setValue(cfg.waterfall.freq_max_hz)

        form.addRow(self._wf_enabled)
        form.addRow(self._wf_live)
        form.addRow(self._wf_monitor)
        form.addRow(QLabel("<b>Live spectrum / FFT</b>"))
        form.addRow("FFT size:", self._wf_fft_size)
        form.addRow("Refresh interval:", self._wf_fft_interval)
        form.addRow("FFT window:", self._wf_fft_window)
        form.addRow("FFT overlap:", self._wf_fft_overlap)
        form.addRow("History depth:", self._wf_history_rows)
        form.addRow("Scroll speed:", self._wf_scroll_pixels)
        form.addRow("Freq min:", self._wf_freq_min)
        form.addRow("Freq max:", self._wf_freq_max)
        form.addRow(QLabel("<b>WFTxt / file TX</b>"))
        form.addRow("Begin message:", self._wf_begin)
        form.addRow("End message:", self._wf_end)
        form.addRow("Font:", self._wf_font)
        form.addRow("Font size:", self._wf_font_size)
        form.addRow("Colormap:", self._wf_colormap)
        form.addRow("Min dB:", self._wf_min_db)
        form.addRow("Max dB:", self._wf_max_db)
        return widget

    def _build_appearance_tab(self, cfg: AppConfig) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)
        self._theme_light = QRadioButton("Light (default)")
        self._theme_dark = QRadioButton("Dark")
        if cfg.ui.theme == "dark":
            self._theme_dark.setChecked(True)
        else:
            self._theme_light.setChecked(True)
        row = QHBoxLayout()
        row.addWidget(self._theme_light)
        row.addWidget(self._theme_dark)
        form.addRow("Theme:", row)
        form.addRow(QLabel("Yellow section titles are kept in both themes."))
        return widget

    def _browse_hamdrm_dll(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select HamDRM DLL (run.dll or hamdrm.dll)",
            self._hamdrm_dll.text() or r"C:\Program Files\EasyPal",
            "DLL (*.dll);;All files (*.*)",
        )
        if path:
            self._hamdrm_dll.setText(path)

    def _browse_dir(self, field: QLineEdit) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select directory", field.text())
        if path:
            field.setText(path)

    def _populate_devices(self, cfg: AppConfig) -> None:
        self._input_device.clear()
        self._output_device.clear()
        self._input_device.addItem("Default", None)
        self._output_device.addItem("Default", None)
        for dev in self._context.audio_engine.list_devices():
            label = f"{dev['index']}: {dev['name']}"
            if dev["max_input_channels"] > 0:
                self._input_device.addItem(label, dev["index"])
            if dev["max_output_channels"] > 0:
                self._output_device.addItem(label, dev["index"])
        self._select_device(self._input_device, cfg.audio.input_device)
        self._select_device(self._output_device, cfg.audio.output_device)

    def _select_device(self, combo: QComboBox, device_id: int | None) -> None:
        if device_id is None:
            combo.setCurrentIndex(0)
            return
        for i in range(combo.count()):
            if combo.itemData(i) == device_id:
                combo.setCurrentIndex(i)
                return

    def _refresh_ports(self, select: str | None = None) -> None:
        current = select or self._com_port.currentText()
        self._com_port.clear()
        for device, desc in list_serial_ports():
            self._com_port.addItem(f"{device} — {desc}", device)
        if current:
            idx = self._com_port.findData(current)
            if idx >= 0:
                self._com_port.setCurrentIndex(idx)
            else:
                self._com_port.setEditText(current)

    def _update_radio_visibility(self) -> None:
        profile = self._radio_profile.currentData()
        self._vox_group.setVisible(profile == "vox")
        self._serial_group.setVisible(profile == "serial")
        self._cat_group.setVisible(profile == "cat")
        self._port_row_widget.setVisible(profile in ("serial", "cat"))

    def apply(self) -> AppConfig:
        config = self._context.config
        config.callsign = self._callsign.text().strip() or "N0CALL"
        config.transfer.loopback_mode = self._loopback.isChecked()
        config.transfer.pace_ms = self._pace_ms.value()
        config.transfer.tune_max_seconds = self._tune_max_seconds.value()
        config.transfer.radio_emission = self._radio_emission.currentData() or "fm"
        config.transfer.auto_rx = self._auto_rx.isChecked()
        config.transfer.require_callsign_wftxt_header = self._callsign_header.isChecked()
        config.modem.engine = self._engine.currentData() or "hamdrm"
        dll_path = self._hamdrm_dll.text().strip()
        config.modem.hamdrm_dll_path = dll_path or None
        config.modem.hamdrm_mode = self._hamdrm_mode.currentData() or "B"
        config.modem.hamdrm_qam = int(self._hamdrm_qam.currentData() or 16)
        config.modem.hamdrm_start_delay = self._hamdrm_leadin.value()
        config.fec.chunk_size = int(
            self._fec_chunk.currentData() or self._fec_chunk.currentText()
        )
        config.network.gallery_dir = self._gallery_dir.text().strip() or None
        config.network.received_dir = self._received_dir.text().strip() or None

        config.audio.input_device = self._input_device.currentData()
        config.audio.output_device = self._output_device.currentData()
        config.audio.sample_rate = self._sample_rate.value()
        config.audio.block_size = self._block_size.value()

        port = self._com_port.currentData() or self._com_port.currentText().strip()
        profile = self._radio_profile.currentData()
        if profile == "serial":
            config.radio = SerialPttConfig(
                port=port,
                line=self._serial_line.currentText(),
                active_low=self._serial_active_low.isChecked(),
                baud=self._serial_baud.value(),
            )
        elif profile == "cat":
            config.radio = CatRadioConfig(
                rig_model=self._cat_rig_model.value(),
                port=port,
                baud=self._cat_baud.value(),
                ptt_method=self._cat_ptt_method.currentData(),
            )
        else:
            config.radio = VoxManualConfig(
                pre_tx_delay_ms=self._vox_pre.value(),
                post_tx_delay_ms=self._vox_post.value(),
            )

        config.waterfall.enabled = self._wf_enabled.isChecked()
        config.waterfall.live_enabled = self._wf_live.isChecked()
        config.waterfall.tx_monitor = self._wf_monitor.isChecked()
        config.waterfall.begin_message = self._wf_begin.text()
        config.waterfall.end_message = self._wf_end.text()
        config.waterfall.default_font = self._wf_font.currentText()
        config.waterfall.default_font_size = self._wf_font_size.value()
        config.waterfall.colormap = self._wf_colormap.currentData()
        config.waterfall.min_db = self._wf_min_db.value()
        config.waterfall.max_db = self._wf_max_db.value()
        config.waterfall.fft_size = int(self._wf_fft_size.currentData() or 1024)
        config.waterfall.fft_interval_ms = self._wf_fft_interval.value()
        config.waterfall.fft_window = self._wf_fft_window.currentData() or "hann"
        config.waterfall.fft_overlap = self._wf_fft_overlap.value()
        config.waterfall.history_rows = self._wf_history_rows.value()
        config.waterfall.scroll_pixels = self._wf_scroll_pixels.value()
        config.waterfall.freq_min_hz = self._wf_freq_min.value()
        config.waterfall.freq_max_hz = max(
            self._wf_freq_min.value() + 100, self._wf_freq_max.value()
        )
        config.ui.theme = "dark" if self._theme_dark.isChecked() else "light"

        save_config(config)
        return config

    def waterfall_config(self) -> dict[str, object]:
        """Values for syncing the main-window WFTxt editor after apply."""
        return {
            "enabled": self._wf_enabled.isChecked(),
            "begin_message": self._wf_begin.text(),
            "end_message": self._wf_end.text(),
            "default_font": self._wf_font.currentText(),
            "default_font_size": self._wf_font_size.value(),
        }
