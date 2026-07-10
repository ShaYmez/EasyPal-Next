"""ctypes-backed libcodec2 / FreeDV modem (skeleton)."""

from __future__ import annotations

import ctypes
from collections.abc import Callable
from pathlib import Path

import numpy as np

from easypal_next.modem.interface import ModemFrameCallback, ModemInterface

# FreeDV API mode constants from freedv_api.h
FREEDV_MODE_DATAC3 = 12
FREEDV_MODE_FSK_LDPC = 9

_MODE_MAP = {
    "DATAC3": FREEDV_MODE_DATAC3,
    "FSK_LDPC": FREEDV_MODE_FSK_LDPC,
}


class CtypesFreeDvModem(ModemInterface):
    def __init__(self, lib_path: Path | None) -> None:
        self._lib_path = lib_path
        self._lib: ctypes.CDLL | None = None
        self._handle: ctypes.c_void_p | None = None
        self._rx_callback: ModemFrameCallback | None = None
        self._mode = "DATAC3"
        self._modem_sample_rate = 8000
        self._frame_payload_size = 126

    def open(self, mode: str, sample_rate: int, advanced: dict | None = None) -> None:
        self._mode = mode
        if self._lib_path is None or not self._lib_path.is_file():
            raise FileNotFoundError(
                "libcodec2 not found. Install codec2 and set modem.libcodec2_path."
            )
        self._lib = ctypes.CDLL(str(self._lib_path))
        self._bind_api()
        mode_id = _MODE_MAP.get(mode.upper(), FREEDV_MODE_DATAC3)
        self._handle = self._lib.freedv_open(mode_id)
        if not self._handle:
            raise RuntimeError(f"freedv_open failed for mode {mode}")
        self._modem_sample_rate = sample_rate

    def _bind_api(self) -> None:
        assert self._lib is not None
        self._lib.freedv_open.argtypes = [ctypes.c_int]
        self._lib.freedv_open.restype = ctypes.c_void_p
        self._lib.freedv_close.argtypes = [ctypes.c_void_p]
        self._lib.freedv_close.restype = None

    def close(self) -> None:
        if self._lib and self._handle:
            self._lib.freedv_close(self._handle)
        self._handle = None
        self._lib = None

    def encode_frame(self, payload: bytes) -> np.ndarray:
        raise NotImplementedError("FreeDV TX binding not yet implemented")

    def decode_samples(self, samples: np.ndarray) -> int:
        raise NotImplementedError("FreeDV RX binding not yet implemented")

    def set_frame_rx_callback(self, cb: ModemFrameCallback) -> None:
        self._rx_callback = cb

    @property
    def modem_sample_rate(self) -> int:
        return self._modem_sample_rate

    @property
    def frame_payload_size(self) -> int:
        return self._frame_payload_size
