"""Radio controller factory."""

from __future__ import annotations

from easypal_next.config.schema import AppConfig, CatRadioConfig, SerialPttConfig, VoxManualConfig
from easypal_next.radio.cat_hamlib import CatHamlibController
from easypal_next.radio.controller import RadioController
from easypal_next.radio.serial_ptt import SerialPttController
from easypal_next.radio.vox_manual import VoxManualController


def create_radio_controller(config: AppConfig) -> RadioController:
    radio = config.radio
    if isinstance(radio, CatRadioConfig):
        return CatHamlibController(radio)
    if isinstance(radio, SerialPttConfig):
        return SerialPttController(radio)
    if isinstance(radio, VoxManualConfig):
        return VoxManualController(radio)
    raise ValueError(f"Unknown radio profile: {radio}")
