"""Radio controller abstract interface."""

from __future__ import annotations

from abc import ABC, abstractmethod


class RadioController(ABC):
    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def disconnect(self) -> None: ...

    @abstractmethod
    def ptt_on(self) -> None: ...

    @abstractmethod
    def ptt_off(self) -> None: ...

    @abstractmethod
    def get_frequency_hz(self) -> int | None: ...

    @property
    @abstractmethod
    def is_connected(self) -> bool: ...
