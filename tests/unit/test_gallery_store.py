"""Tests for gallery thumbnail generation."""

from pathlib import Path

from PIL import Image

from easypal_next.network.gallery_store import GalleryStore, _is_image_path


def test_is_image_path():
    assert _is_image_path(Path("photo.jpg"))
    assert not _is_image_path(Path("data.txt"))


def test_gallery_jpeg_thumb(tmp_path: Path):
    src = tmp_path / "test.jpg"
    Image.new("RGB", (200, 100), color=(255, 0, 0)).save(src)
    store = GalleryStore(tmp_path / "gallery")
    entry = store.add_image(src, callsign="M0VUB", direction="tx")
    assert Path(entry.thumb_path).is_file()
    with Image.open(entry.thumb_path) as thumb:
        assert thumb.size[0] <= 320


def test_gallery_rgba_png_thumb(tmp_path: Path):
    src = tmp_path / "alpha.png"
    Image.new("RGBA", (120, 120), color=(0, 128, 255, 128)).save(src)
    store = GalleryStore(tmp_path / "gallery")
    entry = store.add_image(src, callsign="M0VUB")
    with Image.open(entry.thumb_path) as thumb:
        assert thumb.mode == "RGB"


def test_gallery_non_image_placeholder(tmp_path: Path):
    src = tmp_path / "loopback.txt"
    src.write_text("hello", encoding="utf-8")
    store = GalleryStore(tmp_path / "gallery")
    entry = store.add_image(src, callsign="M0VUB")
    assert Path(entry.thumb_path).is_file()
    assert entry.direction == "rx"
