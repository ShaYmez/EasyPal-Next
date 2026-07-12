"""Marshal spectrum events from audio threads onto the Qt main thread."""

from __future__ import annotations

import threading
from collections import deque

from PySide6.QtCore import QObject, QTimer, Signal

from easypal_next.core.events import EventBus, SpectrumEvent


class SpectrumRelay(QObject):
    """Coalesce spectrum rows and deliver them on the GUI thread."""

    spectrum_received = Signal(object, int, str, float, object)

    def __init__(
        self,
        event_bus: EventBus,
        interval_ms: int = 33,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._lock = threading.Lock()
        self._pending: deque[SpectrumEvent] = deque(maxlen=16)
        event_bus.subscribe(SpectrumEvent, self._enqueue)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._flush)
        self.set_interval_ms(interval_ms)

    def set_interval_ms(self, interval_ms: int) -> None:
        interval_ms = max(16, min(500, interval_ms))
        self._timer.setInterval(interval_ms)
        if not self._timer.isActive():
            self._timer.start()

    def _enqueue(self, event: SpectrumEvent) -> None:
        with self._lock:
            self._pending.append(event)

    def _flush(self) -> None:
        with self._lock:
            while self._pending:
                event = self._pending.popleft()
                peak_db = max(event.bins) if event.bins else -120.0
                self.spectrum_received.emit(
                    event.bins,
                    event.sample_rate,
                    event.source,
                    peak_db,
                    event.level_pct,
                )
