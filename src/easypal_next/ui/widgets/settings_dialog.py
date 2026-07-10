"""Application settings dialog."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from easypal_next.app.bootstrap import AppContext
from easypal_next.config.loader import save_config
from easypal_next.config.schema import AppConfig, CatRadioConfig, SerialPttConfig, VoxManualConfig


class SettingsDialog(QDialog):
    def __init__(self, context: AppContext, parent=None) -> None:
        super().__init__(parent)
        self._context = context
        self.setWindowTitle("EasyPal-Next Settings")

        self._callsign = QLineEdit(context.config.callsign)
        self._loopback = QCheckBox("Loopback mode (no PTT / sound card for modem test)")
        self._loopback.setChecked(context.config.transfer.loopback_mode)

        self._input_device = QComboBox()
        self._output_device = QComboBox()
        self._populate_devices()

        self._radio_profile = QComboBox()
        self._radio_profile.addItem("VOX / Manual PTT", "vox")
        self._radio_profile.addItem("Serial PTT", "serial")
        self._radio_profile.addItem("Hamlib CAT", "cat")
        current = getattr(context.config.radio, "profile", "vox")
        for i in range(self._radio_profile.count()):
            if self._radio_profile.itemData(i) == current:
                self._radio_profile.setCurrentIndex(i)

        self._serial_port = QLineEdit(
            context.config.radio.port if isinstance(context.config.radio, SerialPttConfig) else "COM4"
        )

        form = QFormLayout()
        form.addRow("Callsign:", self._callsign)
        form.addRow(self._loopback)
        form.addRow("Audio input:", self._input_device)
        form.addRow("Audio output:", self._output_device)
        form.addRow("Radio profile:", self._radio_profile)
        form.addRow("Serial PTT port:", self._serial_port)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _populate_devices(self) -> None:
        cfg = self._context.config.audio
        self._input_device.addItem("Default", None)
        self._output_device.addItem("Default", None)
        for dev in self._context.audio_engine.list_devices():
            label = f"{dev['index']}: {dev['name']}"
            if dev["max_input_channels"] > 0:
                self._input_device.addItem(label, dev["index"])
            if dev["max_output_channels"] > 0:
                self._output_device.addItem(label, dev["index"])
        self._select_device(self._input_device, cfg.input_device)
        self._select_device(self._output_device, cfg.output_device)

    def _select_device(self, combo: QComboBox, device_id: int | None) -> None:
        if device_id is None:
            combo.setCurrentIndex(0)
            return
        for i in range(combo.count()):
            if combo.itemData(i) == device_id:
                combo.setCurrentIndex(i)
                return

    def apply(self) -> AppConfig:
        config = self._context.config
        config.callsign = self._callsign.text().strip() or "N0CALL"
        config.transfer.loopback_mode = self._loopback.isChecked()
        config.audio.input_device = self._input_device.currentData()
        config.audio.output_device = self._output_device.currentData()

        profile = self._radio_profile.currentData()
        if profile == "serial":
            config.radio = SerialPttConfig(port=self._serial_port.text())
        elif profile == "cat":
            if isinstance(config.radio, CatRadioConfig):
                config.radio.port = self._serial_port.text()
            else:
                config.radio = CatRadioConfig(port=self._serial_port.text())
        elif profile == "vox":
            pre = getattr(config.radio, "pre_tx_delay_ms", 300)
            post = getattr(config.radio, "post_tx_delay_ms", 200)
            config.radio = VoxManualConfig(pre_tx_delay_ms=pre, post_tx_delay_ms=post)

        save_config(config)
        return config
