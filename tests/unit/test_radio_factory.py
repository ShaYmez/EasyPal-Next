"""Tests for radio controller factory."""

from easypal_next.config.schema import AppConfig, SerialPttConfig, VoxManualConfig
from easypal_next.radio.factory import create_radio_controller
from easypal_next.radio.serial_ptt import SerialPttController
from easypal_next.radio.vox_manual import VoxManualController


def test_radio_factory_vox():
    config = AppConfig(radio=VoxManualConfig())
    controller = create_radio_controller(config)
    assert isinstance(controller, VoxManualController)


def test_radio_factory_serial():
    config = AppConfig(radio=SerialPttConfig(port="COM99"))
    controller = create_radio_controller(config)
    assert isinstance(controller, SerialPttController)
