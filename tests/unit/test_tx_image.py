"""Tests for HamDRM TX image preparation."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from easypal_next.modem.tx_image import prepare_hamdrm_tx_file


def test_prepare_image_downscales_and_jpeg(tmp_path: Path):
    src = tmp_path / "huge.png"
    Image.new("RGB", (2000, 1600), color=(10, 20, 30)).save(src)
    out = prepare_hamdrm_tx_file(src, jpeg_quality=70)
    assert out.suffix.lower() == ".jpg"
    assert out.is_file()
    with Image.open(out) as im:
        assert im.size[0] <= 1280
        assert im.size[1] <= 1024


def test_prepare_non_image_passthrough(tmp_path: Path):
    src = tmp_path / "note.txt"
    src.write_text("hello", encoding="utf-8")
    assert prepare_hamdrm_tx_file(src) == src.resolve()
