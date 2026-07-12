"""PySide6 application entry."""

from __future__ import annotations

import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from easypal_next.app.bootstrap import build_context
from easypal_next.app.paths import brand_icon_path, init_native_library_dirs
from easypal_next.ui.main_window import MainWindow
from easypal_next.ui.theme import apply_theme


def run_application(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv
    init_native_library_dirs()
    app = QApplication(args)
    app.setApplicationName("EasyPal-Next")
    app.setOrganizationName("EasyPal-Next")
    app.setApplicationDisplayName("EasyPal-Next")

    context = build_context()
    apply_theme(app, context.config.ui.theme)

    icon_path = brand_icon_path()
    if icon_path.is_file():
        app.setWindowIcon(QIcon(str(icon_path)))

    # uvicorn + HamDRM (WinMM/MinGW DLL) currently segfaults on Windows when both
    # run in-process. Keep the LAN gallery for FreeDV; HamDRM stays UI-local.
    if getattr(context.transfer_backend, "engine_name", "") != "hamdrm":
        context.network_server.start()
    else:
        from easypal_next.core.events import LogEvent

        context.event_bus.publish(
            LogEvent(
                level="info",
                message="LAN gallery deferred while HamDRM is active (stability)",
            )
        )

    window = MainWindow(context)
    if icon_path.is_file():
        window.setWindowIcon(QIcon(str(icon_path)))
    window.show()
    window.raise_()
    window.activateWindow()
    return app.exec()
