#!/usr/bin/env python3
"""End-to-end loopback file transfer test (no sound card or radio)."""

from __future__ import annotations

import hashlib
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from easypal_next.app.paths import resolve_libcodec2  # noqa: E402
from easypal_next.config.loader import load_config  # noqa: E402
from easypal_next.core.events import EventBus  # noqa: E402
from easypal_next.core.transfer_engine import TransferEngine  # noqa: E402
from easypal_next.modem.factory import create_modem  # noqa: E402
from easypal_next.network.gallery_store import GalleryStore  # noqa: E402
from easypal_next.radio.vox_manual import VoxManualController  # noqa: E402
from easypal_next.waterfall.encoder import SpectrumPainterEncoder  # noqa: E402


def main() -> int:
    if resolve_libcodec2(None) is None:
        print("ERROR: libcodec2.dll not found. See docs/codec2-windows-setup.md")
        return 1

    config = load_config()
    config.transfer.loopback_mode = True
    config.waterfall.enabled = False

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
        test_file = Path(tmp) / "loopback.txt"
        payload = b"EasyPal-Next loopback test payload. 73 de M0VUB"
        test_file.write_bytes(payload)
        expected = hashlib.sha256(payload).hexdigest()

        engine.start_tx(test_file)
        import time

        for _ in range(300):
            if engine.state.value == "idle":
                break
            time.sleep(0.1)

        received = gallery.list_entries()
        if not received:
            out_candidates = list(Path(tmp).glob("**/*"))
            print(f"FAIL: no gallery entry. tmp contents: {out_candidates}")
            return 1

        out_path = Path(received[0].path)
        if not out_path.is_file():
            print(f"FAIL: output missing: {out_path}")
            return 1

        actual = hashlib.sha256(out_path.read_bytes()).hexdigest()
        if actual != expected:
            print(f"FAIL: SHA256 mismatch\n  expected {expected}\n  actual   {actual}")
            return 1

        print(f"OK: loopback transfer verified ({out_path.name})")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
