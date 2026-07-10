"""Transfer view model (Qt signal bridge stub)."""

from __future__ import annotations

from easypal_next.core.events import EventBus, TransferProgressEvent


class TransferViewModel:
    def __init__(self, event_bus: EventBus) -> None:
        self._last_progress: TransferProgressEvent | None = None
        event_bus.subscribe(TransferProgressEvent, self._on_progress)

    def _on_progress(self, event: TransferProgressEvent) -> None:
        self._last_progress = event

    @property
    def last_progress(self) -> TransferProgressEvent | None:
        return self._last_progress
