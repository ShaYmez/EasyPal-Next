"""Hamlib CAT radio control (optional dependency)."""

from __future__ import annotations

from easypal_next.config.schema import CatRadioConfig
from easypal_next.radio.controller import RadioController

try:
    import Hamlib  # type: ignore[import-untyped]
except ImportError:
    Hamlib = None  # type: ignore[assignment,misc]


class CatHamlibController(RadioController):
    def __init__(self, config: CatRadioConfig) -> None:
        if Hamlib is None:
            raise ImportError("Hamlib bindings not installed. Use profile 'serial' or 'vox'.")
        self._config = config
        self._rig = Hamlib.Rig(config.rig_model)
        self._connected = False

    def connect(self) -> None:
        self._rig.set_conf("rig_pathname", self._config.port)
        self._rig.set_conf("serial_speed", str(self._config.baud))
        self._rig.open()
        self._connected = True

    def disconnect(self) -> None:
        if self._connected:
            self.ptt_off()
            self._rig.close()
        self._connected = False

    def ptt_on(self) -> None:
        self._rig.set_ptt(Hamlib.RIG_PTT_ON)

    def ptt_off(self) -> None:
        self._rig.set_ptt(Hamlib.RIG_PTT_OFF)

    def get_frequency_hz(self) -> int | None:
        freq = self._rig.get_freq()
        return int(freq) if freq else None

    @property
    def is_connected(self) -> bool:
        return self._connected
