"""Modem factory."""

from __future__ import annotations

from easypal_next.app.paths import resolve_libcodec2
from easypal_next.config.schema import ModemConfig
from easypal_next.modem.ctypes_backend import CtypesFreeDvModem
from easypal_next.modem.interface import ModemInterface


def create_modem(config: ModemConfig) -> ModemInterface:
    lib_path = resolve_libcodec2(config.libcodec2_path)
    return CtypesFreeDvModem(lib_path)
