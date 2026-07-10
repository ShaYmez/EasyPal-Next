"""Full transfer loopback integration test."""

from __future__ import annotations

import hashlib
import tempfile
import time
from pathlib import Path

import pytest

from easypal_next.app.paths import resolve_libcodec2
from easypal_next.config.loader import load_config
from easypal_next.core.events import EventBus
from easypal_next.core.transfer_engine import TransferEngine
from easypal_next.modem.factory import create_modem
from easypal_next.network.gallery_store import GalleryStore
from easypal_next.radio.vox_manual import VoxManualController
from easypal_next.waterfall.encoder import SpectrumPainterEncoder

pytestmark = pytest.mark.integration

requires_codec2 = pytest.mark.skipif(
    resolve_libcodec2(None) is None,
    reason="libcodec2.dll not available",
)


@requires_codec2
def test_transfer_loopback_sha256():
    config = load_config()
    config.transfer.loopback_mode = True
    config.waterfall.enabled = True

    event_bus = EventBus()
    tx_modem = create_modem(config.modem)
    rx_modem = create_modem(config.modem)
    radio = VoxManualController(config.radio)  # type: ignore[arg-type]
    waterfall = SpectrumPainterEncoder(config.waterfall)

    with tempfile.TemporaryDirectory() as tmp:
        gallery = GalleryStore(Path(tmp) / "gallery")
        engine = TransferEngine(
            config, event_bus, tx_modem, rx_modem, radio, waterfall, gallery
        )
        test_file = Path(tmp) / "test.bin"
        data = b"EasyPal-Next integration loopback " * 10
        test_file.write_bytes(data)
        expected = hashlib.sha256(data).hexdigest()

        engine.start_tx(test_file)
        for _ in range(300):
            if engine.state.value == "idle":
                break
            time.sleep(0.05)

        entries = gallery.list_entries()
        assert entries, "expected gallery entry after RX"
        out_path = Path(entries[0].path)
        assert hashlib.sha256(out_path.read_bytes()).hexdigest() == expected
