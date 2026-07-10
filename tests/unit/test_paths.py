"""Tests for libcodec2 path resolution."""

from pathlib import Path

from easypal_next.app.paths import app_root, dev_redist_libcodec2_path, resolve_libcodec2


def test_dev_redist_path_points_to_packaging():
    expected = app_root() / "packaging" / "windows" / "redist" / "libcodec2.dll"
    assert dev_redist_libcodec2_path() == expected


def test_resolve_libcodec2_explicit_path(tmp_path: Path):
    dll = tmp_path / "libcodec2.dll"
    dll.write_bytes(b"fake")
    assert resolve_libcodec2(str(dll)) == dll
