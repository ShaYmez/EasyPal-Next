"""VOX / manual PTT — no hardware keying."""

from __future__ import annotations

import time

from easypal_next.config.schema import VoxManualConfig
from easypal_next.radio.controller import RadioController


class VoxManualController(RadioController):
    def __init__(self, config: VoxManualConfig) -> None:
        self._config = config
        self._connected = False
        self._ptt_active = False

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False
        self._ptt_active = False

    def ptt_on(self) -> None:
        if self._config.pre_tx_delay_ms:
            time.sleep(self._config.pre_tx_delay_ms / 1000.0)
        self._ptt_active = True

    def ptt_off(self) -> None:
        if self._config.post_tx_delay_ms:
            time.sleep(self._config.post_tx_delay_ms / 1000.0)
        self._ptt_active = False

    def get_frequency_hz(self) -> int | None:
        return None

    @property
    def is_connected(self) -> bool:
        return self._connected
