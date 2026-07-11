"""Abstract transfer backend for FreeDV / HamDRM engines."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SyncState:
    io: bool = False
    time: bool = False
    frame: bool = False
    fac: bool = False
    msc: bool = False
    snr_db: float | None = None
    level: int | None = None
    dc_freq: int | None = None
    callsign: str = ""
    mode: str = ""


class TransferBackend(ABC):
    @abstractmethod
    def start_always_on_rx(self) -> None: ...

    @abstractmethod
    def stop_rx(self) -> None: ...

    @abstractmethod
    def transmit_file(self, path: Path) -> None: ...

    @abstractmethod
    def start_tune(self) -> None: ...

    @abstractmethod
    def stop_tune(self) -> None: ...

    @abstractmethod
    def abort(self) -> None: ...

    @abstractmethod
    def get_spectrum(self) -> list[float]: ...

    @abstractmethod
    def get_sync_state(self) -> SyncState: ...

    @abstractmethod
    def is_available(self) -> bool: ...

    @property
    @abstractmethod
    def engine_name(self) -> str: ...
