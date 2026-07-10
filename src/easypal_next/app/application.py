"""PySide6 application entry."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from easypal_next.app.bootstrap import build_context
from easypal_next.ui.main_window import MainWindow


def run_application(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv
    app = QApplication(args)
    app.setApplicationName("EasyPal-Next")
    app.setOrganizationName("EasyPal-Next")
    app.setApplicationDisplayName("EasyPal-Next")

    context = build_context()
    context.network_server.start()

    window = MainWindow(context)
    window.show()
    return app.exec()
