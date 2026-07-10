"""TX/RX orchestration state machine."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from easypal_next.config.schema import AppConfig
from easypal_next.core.events import EventBus, LogEvent, SessionStateChangedEvent
from easypal_next.core.session import SessionState


@dataclass
class TransferProgress:
    pct: float = 0.0
    bytes_done: int = 0
    bytes_total: int = 0


class TransferEngine:
    def __init__(self, config: AppConfig, event_bus: EventBus) -> None:
        self._config = config
        self._event_bus = event_bus
        self._state = SessionState.IDLE
        self._progress = TransferProgress()

    @property
    def state(self) -> SessionState:
        return self._state

    def get_progress(self) -> TransferProgress:
        return self._progress

    def _set_state(self, state: SessionState) -> None:
        self._state = state
        self._event_bus.publish(SessionStateChangedEvent(state=state))

    def start_tx(self, file_path: Path) -> None:
        if self._state != SessionState.IDLE:
            raise RuntimeError(f"Cannot start TX from state {self._state}")
        self._event_bus.publish(LogEvent(level="info", message=f"TX armed: {file_path}"))
        if self._config.waterfall.enabled:
            self._set_state(SessionState.TX_WATERFALL_HEADER)
        else:
            self._set_state(SessionState.TX_ARMED)
        # TODO: waterfall header → modem TX → optional footer
        self._set_state(SessionState.TX_ACTIVE)

    def start_rx(self, output_dir: Path) -> None:
        if self._state != SessionState.IDLE:
            raise RuntimeError(f"Cannot start RX from state {self._state}")
        output_dir.mkdir(parents=True, exist_ok=True)
        self._event_bus.publish(LogEvent(level="info", message=f"RX listening: {output_dir}"))
        self._set_state(SessionState.RX_LISTEN)

    def abort(self) -> None:
        self._event_bus.publish(LogEvent(level="warning", message="Transfer aborted"))
        self._set_state(SessionState.IDLE)
