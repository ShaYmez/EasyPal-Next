"""Typed application events and pub/sub bus."""

from __future__ import annotations

import queue
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable, Literal

from easypal_next.core.session import SessionState


@dataclass(frozen=True)
class LogEvent:
    level: str
    message: str


@dataclass(frozen=True)
class TransferProgressEvent:
    pct: float
    bytes_done: int
    bytes_total: int


@dataclass(frozen=True)
class RxImageReadyEvent:
    path: str


@dataclass(frozen=True)
class SpectrumEvent:
    bins: list[float]
    sample_rate: int = 48000
    source: Literal["rx", "tx"] = "rx"
    """Optional 0–100 input level (HamDRM GetLevel). None = derive from bins."""
    level_pct: int | None = None


@dataclass(frozen=True)
class SyncStatusEvent:
    """Periodic HamDRM sync / SNR snapshot for the UI."""

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
    percent_tx: int | None = None
    seg_pos: int | None = None
    seg_total: int | None = None
    """RX GetData: total / active / position (EasyPal OK Segs strip)."""
    rx_total: int | None = None
    rx_ok: int | None = None
    rx_pos: int | None = None


@dataclass(frozen=True)
class SessionStateChangedEvent:
    state: SessionState


@dataclass(frozen=True)
class WaterfallPaintStartedEvent:
    message: str


@dataclass(frozen=True)
class WaterfallTextReceivedEvent:
    text: str


@dataclass(frozen=True)
class GalleryUpdatedEvent:
    image_id: str
    path: str


Event = (
    LogEvent
    | TransferProgressEvent
    | RxImageReadyEvent
    | SpectrumEvent
    | SyncStatusEvent
    | SessionStateChangedEvent
    | WaterfallPaintStartedEvent
    | WaterfallTextReceivedEvent
    | GalleryUpdatedEvent
)


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[type, list[Callable[[Any], None]]] = defaultdict(list)
        self._thread_queue: queue.Queue[Event] | None = None

    def subscribe(self, event_type: type, handler: Callable[[Any], None]) -> None:
        self._subscribers[event_type].append(handler)

    def publish(self, event: Event) -> None:
        for handler in self._subscribers[type(event)]:
            handler(event)
        if self._thread_queue is not None:
            # Spectrum floods the WS hub and is useless on the phone gallery.
            if type(event).__name__ == "SpectrumEvent":
                return
            try:
                self._thread_queue.put_nowait(event)
            except queue.Full:
                pass

    def bind_thread_queue(self, event_queue: queue.Queue[Event]) -> None:
        self._thread_queue = event_queue
