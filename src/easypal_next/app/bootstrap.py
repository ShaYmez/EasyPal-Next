"""Application bootstrap and dependency wiring."""

from __future__ import annotations

from pathlib import Path

from easypal_next.app.paths import user_gallery_dir
from easypal_next.audio.modem_bridge import ModemBridge
from easypal_next.audio.sounddevice_engine import SoundDeviceEngine
from easypal_next.community.null_client import NullCommunityClient
from easypal_next.config.loader import load_config
from easypal_next.config.schema import AppConfig
from easypal_next.core.events import EventBus, SpectrumEvent
from easypal_next.core.transfer_engine import TransferEngine
from easypal_next.modem.factory import create_modem
from easypal_next.network.gallery_store import GalleryStore
from easypal_next.network.server import NetworkServer
from easypal_next.radio.factory import create_radio_controller
from easypal_next.waterfall.encoder import SpectrumPainterEncoder


class AppContext:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.event_bus = EventBus()
        self.audio_engine = SoundDeviceEngine()
        self.tx_modem = create_modem(config.modem)
        self.rx_modem = create_modem(config.modem)
        self.radio = create_radio_controller(config)
        self.waterfall = SpectrumPainterEncoder(config.waterfall)
        self.community_client = NullCommunityClient()
        gallery_dir = (
            Path(config.network.gallery_dir).expanduser()
            if config.network.gallery_dir
            else user_gallery_dir()
        )
        self.gallery = GalleryStore(gallery_dir)
        self.modem_bridge: ModemBridge | None = None
        if not config.transfer.loopback_mode:
            self.modem_bridge = ModemBridge(
                self.audio_engine,
                self.rx_modem,
                config.audio.sample_rate,
                config.modem.sample_rate,
                on_spectrum=lambda bins: self.event_bus.publish(SpectrumEvent(bins=bins)),
            )
        self.transfer_engine = TransferEngine(
            config,
            self.event_bus,
            self.tx_modem,
            self.rx_modem,
            self.radio,
            self.waterfall,
            self.gallery,
            self.modem_bridge,
        )
        self.network_server = NetworkServer(
            config.network,
            self.event_bus,
            self.transfer_engine,
            self.gallery,
            config.callsign,
            config.modem.mode,
        )


def build_context() -> AppContext:
    config = load_config()
    return AppContext(config)
