"""Application theme loading (light default, dark optional)."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from easypal_next.app.paths import package_root


def apply_theme(app: QApplication, theme: str = "light") -> None:
    app.setStyle("Fusion")
    name = theme if theme in ("light", "dark") else "light"
    qss_path = package_root() / "ui" / "styles" / f"{name}.qss"
    if qss_path.is_file():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))
    else:
        app.setStyleSheet("")
