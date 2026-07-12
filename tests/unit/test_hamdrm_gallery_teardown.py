"""Tests for HamDRM gallery ingest and LAN gallery subprocess."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from PIL import Image

from easypal_next.config.schema import AppConfig
from easypal_next.core.events import EventBus, GalleryUpdatedEvent
from easypal_next.modem.hamdrm_backend import HamDrmBackend
from easypal_next.network.gallery_store import GalleryStore


def _backend(tmp_path: Path) -> tuple[HamDrmBackend, GalleryStore, list]:
    gallery = GalleryStore(tmp_path / "gallery", received_dir=tmp_path / "received")
    bus = EventBus()
    events: list = []
    bus.subscribe(GalleryUpdatedEvent, events.append)
    cfg = AppConfig(callsign="M0VUB")
    backend = HamDrmBackend(cfg, bus, gallery, radio=None)
    return backend, gallery, events


def test_ingest_rx_does_not_blacklist_missing_file(tmp_path: Path):
    backend, gallery, events = _backend(tmp_path)
    assert backend._ingest_rx_file("missing-nope.jpg") is False
    assert "missing-nope.jpg" not in backend._seen_rx
    assert events == []
    assert gallery.list_entries() == []


def test_ingest_rx_adds_gallery_and_returns_true(tmp_path: Path):
    backend, gallery, events = _backend(tmp_path)
    src = tmp_path / "rxshot.png"
    Image.new("RGB", (32, 32), color=(10, 20, 30)).save(src)
    assert backend._ingest_rx_file(str(src)) is True
    entries = gallery.list_entries()
    assert len(entries) == 1
    assert entries[0].direction == "rx"
    assert len(events) == 1


def test_poll_rx_spectrum_skipped_while_tx_busy(tmp_path: Path):
    backend, _, _ = _backend(tmp_path)
    backend._rx_active = True
    backend._tx_busy = True
    backend._config.waterfall.live_enabled = True
    backend._lib = MagicMock()
    backend.poll_rx_spectrum()
    backend._lib.GetSpectrum.assert_not_called()


def test_stop_file_tx_adds_gallery_entry(tmp_path: Path):
    backend, gallery, events = _backend(tmp_path)
    tx = tmp_path / "Pic-logo.jpg"
    Image.new("RGB", (40, 20), color=(200, 40, 40)).save(tx, format="JPEG")
    backend._tx_busy = True
    backend._tx_active = True
    backend._tx_gallery_path = tx
    backend._lib = MagicMock()
    backend._rx_active = False
    backend._rx_paused_for_pcm = False

    with patch.object(backend, "_ptt_off"), patch.object(backend, "_stop_tx_poll"), patch(
        "easypal_next.modem.hamdrm_backend.time.sleep", return_value=None
    ):
        backend._stop_file_tx(aborted=False)

    entries = gallery.list_entries()
    assert len(entries) == 1
    assert entries[0].direction == "tx"
    assert len(events) == 1
    assert backend._tx_busy is False
    assert backend._tx_gallery_path is None


def test_stop_file_tx_aborted_skips_gallery(tmp_path: Path):
    backend, gallery, events = _backend(tmp_path)
    tx = tmp_path / "Pic-logo.jpg"
    Image.new("RGB", (40, 20), color=(200, 40, 40)).save(tx, format="JPEG")
    backend._tx_busy = True
    backend._tx_active = True
    backend._tx_gallery_path = tx
    backend._lib = MagicMock()

    with patch.object(backend, "_ptt_off"), patch.object(backend, "_stop_tx_poll"), patch(
        "easypal_next.modem.hamdrm_backend.time.sleep", return_value=None
    ):
        backend._stop_file_tx(aborted=True)

    assert gallery.list_entries() == []
    assert events == []


def test_gallery_subprocess_module_builds_app(tmp_path: Path):
    from easypal_next.network.gallery_subprocess import build_gallery_app

    gdir = tmp_path / "gallery"
    rdir = tmp_path / "received"
    app = build_gallery_app(
        gallery_dir=gdir,
        received_dir=rdir,
        callsign="M0VUB",
        modem_mode="hamdrm",
    )
    assert app.title == "EasyPal-Next Gallery"


def test_gallery_store_reload_from_disk(tmp_path: Path):
    gdir = tmp_path / "gallery"
    writer = GalleryStore(gdir)
    img = tmp_path / "shot.png"
    Image.new("RGB", (16, 16), color=(1, 2, 3)).save(img)
    writer.add_image(img, callsign="M0VUB", direction="tx")

    reader = GalleryStore(gdir, reload_from_disk=True)
    assert len(reader.list_entries()) == 1
    assert reader.list_entries()[0].direction == "tx"
