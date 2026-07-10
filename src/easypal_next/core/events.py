"""Typed application events and pub/sub bus."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable

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
    | SessionStateChangedEvent
    | WaterfallPaintStartedEvent
    | WaterfallTextReceivedEvent
    | GalleryUpdatedEvent
)


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[type, list[Callable[[Any], None]]] = defaultdict(list)
        self._async_queue: asyncio.Queue[Event] | None = None

    def subscribe(self, event_type: type, handler: Callable[[Any], None]) -> None:
        self._subscribers[event_type].append(handler)

    def publish(self, event: Event) -> None:
        for handler in self._subscribers[type(event)]:
            handler(event)
        if self._async_queue is not None:
            try:
                self._async_queue.put_nowait(event)
            except asyncio.QueueFull:
                pass

    def bind_async_queue(self, queue: asyncio.Queue[Event]) -> None:
        self._async_queue = queue
