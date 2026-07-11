"""Session and transfer state."""

from __future__ import annotations

from enum import Enum


class SessionState(str, Enum):
    IDLE = "idle"
    TX_ARMED = "tx_armed"
    TX_WATERFALL_HEADER = "tx_waterfall_header"
    TX_ACTIVE = "tx_active"
    TX_WATERFALL_FOOTER = "tx_waterfall_footer"
    TX_DONE = "tx_done"
    RX_LISTEN = "rx_listen"
    RX_SYNC = "rx_sync"
    RX_ASSEMBLING = "rx_assembling"
    RX_DONE = "rx_done"
    TUNING = "tuning"
    ERROR = "error"
