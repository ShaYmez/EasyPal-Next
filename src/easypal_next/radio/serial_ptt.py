"""Serial RTS/DTR PTT for Digirig-style interfaces."""

from __future__ import annotations

import time

import serial

from easypal_next.config.schema import SerialPttConfig
from easypal_next.radio.controller import RadioController


class SerialPttController(RadioController):
    def __init__(self, config: SerialPttConfig) -> None:
        self._config = config
        self._port: serial.Serial | None = None

    def connect(self) -> None:
        self._port = serial.Serial(
            port=self._config.port,
            baudrate=self._config.baud,
            rtscts=False,
            dsrdtr=False,
        )

    def disconnect(self) -> None:
        if self._port and self._port.is_open:
            self.ptt_off()
            self._port.close()
        self._port = None

    def _set_line(self, active: bool) -> None:
        if not self._port:
            raise RuntimeError("Serial PTT not connected")
        level = active ^ self._config.active_low
        if self._config.line == "RTS":
            self._port.rts = level
        else:
            self._port.dtr = level

    def ptt_on(self) -> None:
        self._set_line(True)
        time.sleep(0.05)

    def ptt_off(self) -> None:
        self._set_line(False)

    def get_frequency_hz(self) -> int | None:
        return None

    @property
    def is_connected(self) -> bool:
        return self._port is not None and self._port.is_open
