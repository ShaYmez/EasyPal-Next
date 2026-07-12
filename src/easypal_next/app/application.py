"""PySide6 application entry."""

from __future__ import annotations

import os
import subprocess
import sys
import time

from PySide6.QtCore import QLockFile
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from easypal_next.app.bootstrap import build_context
from easypal_next.app.paths import brand_icon_path, init_native_library_dirs, user_data_dir
from easypal_next.ui.main_window import MainWindow
from easypal_next.ui.theme import apply_theme


def _pid_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        try:
            out = subprocess.check_output(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                text=True,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.CalledProcessError):
            return False
        return str(pid) in out
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _pid_is_easypal(pid: int) -> bool:
    """True if *pid* looks like an EasyPal-Next parent (not a recycled PID)."""
    if pid <= 0 or not _pid_is_alive(pid):
        return False
    if sys.platform != "win32":
        return True
    try:
        out = subprocess.check_output(
            [
                "wmic",
                "process",
                "where",
                f"ProcessId={pid}",
                "get",
                "CommandLine",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.CalledProcessError):
        return False
    low = out.lower()
    return "-m easypal_next" in low and "gallery_subprocess" not in low


def _kill_other_easypal_parents() -> None:
    """Stop other ``-m easypal_next`` parents (not gallery children).

    A second copy (often system Python vs .venv) loading hamdrm.dll on the
    same sound device reliably segfaults. Gallery subprocesses are left alone
    here; ``NetworkServer`` cleans those on start/stop.
    """
    import re

    me = os.getpid()
    try:
        out = subprocess.check_output(
            [
                "wmic",
                "process",
                "where",
                "Name='python.exe'",
                "get",
                "ProcessId,CommandLine",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            if sys.platform == "win32"
            else 0,
        )
    except (OSError, subprocess.CalledProcessError):
        return
    # Match ``-m easypal_next`` but not ``-m easypal_next.network...``.
    parent_re = re.compile(r"-m\s+easypal_next(?:\s|$)", re.IGNORECASE)
    for line in out.splitlines():
        if not parent_re.search(line):
            continue
        parts = line.strip().rsplit(None, 1)
        if len(parts) < 2 or not parts[-1].isdigit():
            continue
        pid = int(parts[-1])
        if pid == me:
            continue
        try:
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid)],
                    capture_output=True,
                    check=False,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            else:
                os.kill(pid, 15)
        except OSError:
            pass
    time.sleep(0.5)


def run_application(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv
    init_native_library_dirs()
    app = QApplication(args)
    app.setApplicationName("EasyPal-Next")
    app.setOrganizationName("EasyPal-Next")
    app.setApplicationDisplayName("EasyPal-Next")

    # Two instances both load hamdrm.dll on the same sound device → segfaults.
    lock_path = user_data_dir() / "easypal-next.lock"
    lock = QLockFile(str(lock_path))
    # Never auto-steal a live lock (avoids .venv vs system-Python races).
    lock.setStaleLockTime(0)
    if not lock.tryLock(100):
        holder_alive = False
        holder_pid = 0
        try:
            info = lock.getLockInfo()
            # PySide6: (pid, hostname, appname)
            if isinstance(info, tuple) and info:
                holder_pid = int(info[0])
                # PID reuse: a dead EasyPal lock can point at an unrelated live process.
                holder_alive = _pid_is_easypal(holder_pid)
        except (TypeError, ValueError, AttributeError):
            holder_alive = False
        if not holder_alive:
            # removeStaleLockFile() is a no-op when staleLockTime is 0.
            try:
                lock_path.unlink(missing_ok=True)
            except OSError:
                pass
        if holder_alive or not lock.tryLock(100):
            QMessageBox.warning(
                None,
                "EasyPal-Next",
                "EasyPal-Next is already running.\n\n"
                "Close the other window first (two copies share the sound card and crash).\n"
                f"If nothing is open, delete:\n{lock_path}",
            )
            return 1

    # If a lockless second copy is already up, stop it before loading HamDRM.
    _kill_other_easypal_parents()

    context = build_context()
    apply_theme(app, context.config.ui.theme)

    icon_path = brand_icon_path()
    if icon_path.is_file():
        app.setWindowIcon(QIcon(str(icon_path)))

    # uvicorn + HamDRM (WinMM/MinGW DLL) segfaults in-process on Windows.
    # FreeDV can host the gallery in-thread; HamDRM uses a child process.
    if getattr(context.transfer_backend, "engine_name", "") == "hamdrm":
        context.network_server.start_subprocess()
    else:
        context.network_server.start()

    window = MainWindow(context)
    if icon_path.is_file():
        window.setWindowIcon(QIcon(str(icon_path)))
    window.show()
    window.raise_()
    window.activateWindow()
    try:
        return app.exec()
    finally:
        # Kill gallery child; parent segfaults can still leave orphans.
        context.network_server.stop()
        lock.unlock()
