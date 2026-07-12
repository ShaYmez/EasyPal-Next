"""Marshal HamDRM sync status events onto the Qt main thread."""

from __future__ import annotations

import threading
from collections import deque

from PySide6.QtCore import QObject, QTimer, Signal

from easypal_next.core.events import EventBus, SyncStatusEvent


class SyncStatusRelay(QObject):
    sync_received = Signal(object)

    def __init__(
        self,
        event_bus: EventBus,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._lock = threading.Lock()
        self._pending: deque[SyncStatusEvent] = deque(maxlen=4)
        event_bus.subscribe(SyncStatusEvent, self._enqueue)
        self._timer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._flush)
        self._timer.start()

    def _enqueue(self, event: SyncStatusEvent) -> None:
        with self._lock:
            self._pending.append(event)

    def _flush(self) -> None:
        with self._lock:
            if not self._pending:
                return
            event = self._pending.pop()
            self._pending.clear()
        self.sync_received.emit(event)
