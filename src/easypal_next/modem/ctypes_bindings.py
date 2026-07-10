"""ctypes signatures for libcodec2 FreeDV raw data API."""

from __future__ import annotations

import ctypes
from ctypes import CDLL, c_int, c_short, c_void_p
from typing import Any

# Mode constants from freedv_api.h
FREEDV_MODE_DATAC3 = 12
FREEDV_MODE_FSK_LDPC = 9


class FreeDvLibrary:
    """Typed wrapper around libcodec2 CDLL exports."""

    def __init__(self, lib: CDLL) -> None:
        self._lib = lib
        self._bind()

    def _bind(self) -> None:
        lib = self._lib
        lib.freedv_open.argtypes = [c_int]
        lib.freedv_open.restype = c_void_p
        lib.freedv_close.argtypes = [c_void_p]
        lib.freedv_close.restype = None

        lib.freedv_get_modem_sample_rate.argtypes = [c_void_p]
        lib.freedv_get_modem_sample_rate.restype = c_int
        lib.freedv_get_bits_per_modem_frame.argtypes = [c_void_p]
        lib.freedv_get_bits_per_modem_frame.restype = c_int
        lib.freedv_get_n_tx_modem_samples.argtypes = [c_void_p]
        lib.freedv_get_n_tx_modem_samples.restype = c_int
        lib.freedv_get_n_max_modem_samples.argtypes = [c_void_p]
        lib.freedv_get_n_max_modem_samples.restype = c_int
        lib.freedv_get_n_tx_preamble_modem_samples.argtypes = [c_void_p]
        lib.freedv_get_n_tx_preamble_modem_samples.restype = c_int
        lib.freedv_get_n_tx_postamble_modem_samples.argtypes = [c_void_p]
        lib.freedv_get_n_tx_postamble_modem_samples.restype = c_int

        lib.freedv_nin.argtypes = [c_void_p]
        lib.freedv_nin.restype = c_int

        lib.freedv_gen_crc16.argtypes = [ctypes.c_char_p, c_int]
        lib.freedv_gen_crc16.restype = ctypes.c_uint16

        lib.freedv_rawdatatx.argtypes = [c_void_p, ctypes.POINTER(c_short), ctypes.c_char_p]
        lib.freedv_rawdatatx.restype = None
        lib.freedv_rawdatarx.argtypes = [c_void_p, ctypes.c_char_p, ctypes.POINTER(c_short)]
        lib.freedv_rawdatarx.restype = c_int
        lib.freedv_rawdatapreambletx.argtypes = [c_void_p, ctypes.POINTER(c_short)]
        lib.freedv_rawdatapreambletx.restype = c_int
        lib.freedv_rawdatapostambletx.argtypes = [c_void_p, ctypes.POINTER(c_short)]
        lib.freedv_rawdatapostambletx.restype = c_int

        lib.freedv_set_frames_per_burst.argtypes = [c_void_p, c_int]
        lib.freedv_set_frames_per_burst.restype = None

        lib.freedv_get_modem_extended_stats.argtypes = [c_void_p, c_void_p]
        lib.freedv_get_modem_extended_stats.restype = None

    @property
    def lib(self) -> CDLL:
        return self._lib

    def open(self, mode: int) -> c_void_p:
        handle = self._lib.freedv_open(mode)
        if not handle:
            raise RuntimeError(f"freedv_open failed for mode {mode}")
        return handle

    def close(self, handle: c_void_p) -> None:
        self._lib.freedv_close(handle)


def load_library(path: str) -> FreeDvLibrary:
    import os
    from pathlib import Path

    dll_path = Path(path).resolve()
    dll_dir = str(dll_path.parent)
    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(dll_dir)
    return FreeDvLibrary(CDLL(str(dll_path)))
