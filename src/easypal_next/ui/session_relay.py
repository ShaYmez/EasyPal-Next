"""Marshal session state events onto the Qt main thread."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from easypal_next.core.events import EventBus, SessionStateChangedEvent
from easypal_next.core.session import SessionState


class SessionStateRelay(QObject):
    """Deliver session state changes on the GUI thread."""

    state_changed = Signal(object)

    def __init__(self, event_bus: EventBus, parent: QObject | None = None) -> None:
        super().__init__(parent)
        event_bus.subscribe(SessionStateChangedEvent, self._on_event)

    def _on_event(self, event: SessionStateChangedEvent) -> None:
        self.state_changed.emit(event.state)
