"""Pic/QSL compose dialog — EasyPal Layer backgrounds + callsign."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from easypal_next.ui.qsl_compose import compose_qsl, list_qsl_templates


class PicQslDialog(QDialog):
    def __init__(self, *, callsign: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Pic / QSL")
        self._result_path: Path | None = None
        self._callsign = callsign
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self._templates = QComboBox()
        for path in list_qsl_templates():
            self._templates.addItem(path.name, str(path))
        if self._templates.count() == 0:
            layout.addWidget(
                QLabel(
                    "No QSL templates found.\n"
                    "Place PNG/JPG files in %APPDATA%\\EasyPal\\Layer "
                    "or %APPDATA%\\EasyPal-Next\\qsl\\"
                )
            )
        self._extra = QLineEdit()
        self._extra.setPlaceholderText("Optional extra line (name, QTH, …)")
        form.addRow("Template:", self._templates)
        form.addRow("Extra text:", self._extra)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._compose)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @property
    def composed_path(self) -> Path | None:
        return self._result_path

    def _compose(self) -> None:
        raw = self._templates.currentData()
        if not raw:
            QMessageBox.warning(self, "Pic / QSL", "No template selected.")
            return
        try:
            self._result_path = compose_qsl(
                Path(raw),
                callsign=self._callsign,
                extra_text=self._extra.text(),
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Pic / QSL", str(exc))
            return
        self.accept()
