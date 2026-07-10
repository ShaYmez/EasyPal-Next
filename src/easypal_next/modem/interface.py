"""Modem abstract interface for Codec2/FreeDV integration."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable

import numpy as np

ModemFrameCallback = Callable[[bytes], None]


class ModemInterface(ABC):
    @abstractmethod
    def open(self, mode: str, sample_rate: int, advanced: dict | None = None) -> None: ...

    @abstractmethod
    def close(self) -> None: ...

    @abstractmethod
    def encode_frame(self, payload: bytes) -> np.ndarray: ...

    @abstractmethod
    def decode_samples(self, samples: np.ndarray) -> int: ...

    @abstractmethod
    def set_frame_rx_callback(self, cb: ModemFrameCallback) -> None: ...

    @property
    @abstractmethod
    def modem_sample_rate(self) -> int: ...

    @property
    @abstractmethod
    def frame_payload_size(self) -> int: ...
