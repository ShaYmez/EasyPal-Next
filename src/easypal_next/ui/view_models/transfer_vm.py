"""Transfer view model with Qt signals."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from easypal_next.core.events import EventBus, SessionStateChangedEvent, TransferProgressEvent


class TransferViewModel(QObject):
    progress_changed = Signal(float, int, int)
    state_changed = Signal(str)

    def __init__(self, event_bus: EventBus) -> None:
        super().__init__()
        event_bus.subscribe(TransferProgressEvent, self._on_progress)
        event_bus.subscribe(SessionStateChangedEvent, self._on_state)

    def _on_progress(self, event: TransferProgressEvent) -> None:
        self.progress_changed.emit(event.pct, event.bytes_done, event.bytes_total)

    def _on_state(self, event: SessionStateChangedEvent) -> None:
        self.state_changed.emit(event.state.value)
