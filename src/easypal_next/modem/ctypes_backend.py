"""ctypes-backed libcodec2 / FreeDV raw data modem."""

from __future__ import annotations

import ctypes
from collections import deque
from collections.abc import Callable
from pathlib import Path

import numpy as np

from easypal_next.modem.ctypes_bindings import FREEDV_MODE_DATAC3, FREEDV_MODE_FSK_LDPC, load_library
from easypal_next.modem.interface import ModemFrameCallback, ModemInterface

_MODE_MAP = {
    "DATAC3": FREEDV_MODE_DATAC3,
    "FSK_LDPC": FREEDV_MODE_FSK_LDPC,
}


class CtypesFreeDvModem(ModemInterface):
    """FreeDV raw data mode (DATAC3) via libcodec2 ctypes."""

    def __init__(self, lib_path: Path | None) -> None:
        self._lib_path = lib_path
        self._api = None
        self._handle = None
        self._rx_callback: ModemFrameCallback | None = None
        self._mode = "DATAC3"
        self._modem_sample_rate = 8000
        self._bytes_per_modem_frame = 128
        self._payload_bytes = 126
        self._n_tx_modem_samples = 0
        self._rx_pending: deque[bytes] = deque()
        self._rx_carry = np.array([], dtype=np.int16)

    def open(self, mode: str, sample_rate: int, advanced: dict | None = None) -> None:
        self._mode = mode.upper()
        if self._lib_path is None or not self._lib_path.is_file():
            raise FileNotFoundError(
                "libcodec2 not found. Install codec2 and set modem.libcodec2_path."
            )
        self._api = load_library(str(self._lib_path))
        mode_id = _MODE_MAP.get(self._mode, FREEDV_MODE_DATAC3)
        self._handle = self._api.open(mode_id)
        self._api.lib.freedv_set_frames_per_burst(self._handle, 1)

        bits_per_frame = self._api.lib.freedv_get_bits_per_modem_frame(self._handle)
        self._bytes_per_modem_frame = bits_per_frame // 8
        self._payload_bytes = self._bytes_per_modem_frame - 2
        self._modem_sample_rate = self._api.lib.freedv_get_modem_sample_rate(self._handle)
        self._n_tx_modem_samples = self._api.lib.freedv_get_n_tx_modem_samples(self._handle)

    def close(self) -> None:
        if self._api and self._handle:
            self._api.close(self._handle)
        self._handle = None
        self._api = None
        self._rx_carry = np.array([], dtype=np.int16)

    def _frame_buffer(self, payload: bytes) -> bytes:
        assert self._api is not None
        frame = bytearray(self._bytes_per_modem_frame)
        copy_len = min(len(payload), self._payload_bytes)
        frame[:copy_len] = payload[:copy_len]
        crc = self._api.lib.freedv_gen_crc16(bytes(frame[: self._payload_bytes]), self._payload_bytes)
        frame[self._bytes_per_modem_frame - 2] = (crc >> 8) & 0xFF
        frame[self._bytes_per_modem_frame - 1] = crc & 0xFF
        return bytes(frame)

    def encode_preamble(self) -> np.ndarray:
        assert self._api and self._handle
        mod_out = (ctypes.c_short * self._n_tx_modem_samples)()
        n = self._api.lib.freedv_rawdatapreambletx(self._handle, mod_out)
        return np.array(mod_out[:n], dtype=np.int16)

    def encode_postamble(self) -> np.ndarray:
        assert self._api and self._handle
        mod_out = (ctypes.c_short * self._n_tx_modem_samples)()
        n = self._api.lib.freedv_rawdatapostambletx(self._handle, mod_out)
        return np.array(mod_out[:n], dtype=np.int16)

    def encode_frame(self, payload: bytes) -> np.ndarray:
        assert self._api and self._handle
        frame = self._frame_buffer(payload)
        mod_out = (ctypes.c_short * self._n_tx_modem_samples)()
        self._api.lib.freedv_rawdatatx(self._handle, mod_out, ctypes.c_char_p(frame))
        return np.array(mod_out[: self._n_tx_modem_samples], dtype=np.int16)

    def decode_samples(self, samples: np.ndarray) -> int:
        assert self._api and self._handle
        if len(samples) == 0:
            return 0
        self._rx_carry = np.concatenate([self._rx_carry, samples.astype(np.int16)])
        consumed = 0
        bytes_out = (ctypes.c_char * self._bytes_per_modem_frame)()

        while True:
            nin = self._api.lib.freedv_nin(self._handle)
            if len(self._rx_carry) < nin:
                break
            chunk = self._rx_carry[:nin]
            self._rx_carry = self._rx_carry[nin:]
            consumed += nin
            demod = (ctypes.c_short * nin)(*chunk.tolist())
            nbytes = self._api.lib.freedv_rawdatarx(self._handle, bytes_out, demod)
            if nbytes > 2:
                payload = bytes(bytes_out[: nbytes - 2])
                if self._rx_callback:
                    self._rx_callback(payload)
                self._rx_pending.append(payload)
        return consumed

    def pop_rx_frame(self) -> bytes | None:
        if self._rx_pending:
            return self._rx_pending.popleft()
        return None

    def set_frame_rx_callback(self, cb: ModemFrameCallback) -> None:
        self._rx_callback = cb

    @property
    def modem_sample_rate(self) -> int:
        return self._modem_sample_rate

    @property
    def frame_payload_size(self) -> int:
        return self._payload_bytes

    @property
    def tx_samples_per_frame(self) -> int:
        return self._n_tx_modem_samples
