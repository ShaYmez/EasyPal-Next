"""Audio engine abstract interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable

import numpy as np

AudioChunkCallback = Callable[[np.ndarray], None]


class AudioEngine(ABC):
    @abstractmethod
    def list_devices(self) -> list[dict]: ...

    @abstractmethod
    def open(
        self,
        input_device: int | None,
        output_device: int | None,
        sample_rate: int,
        block_size: int,
    ) -> None: ...

    @abstractmethod
    def start(self, on_rx: AudioChunkCallback) -> None: ...

    @abstractmethod
    def write_tx(self, samples: np.ndarray) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...

    @abstractmethod
    def close(self) -> None: ...

    @property
    @abstractmethod
    def is_running(self) -> bool: ...
