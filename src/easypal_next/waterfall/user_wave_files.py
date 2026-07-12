"""Locate EasyPal UserWaveFiles libraries for WFPic / reverse cinema."""

from __future__ import annotations

from pathlib import Path

from easypal_next.app.paths import user_data_dir

_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".jp2"}
_WAV_SUFFIXES = {".wav"}


def easypal_user_wave_dirs(*, cinema_scroll: bool = False) -> list[Path]:
    """Return UserWaveFiles search dirs.

    EasyPal: ``UserWaveFiles`` = reverse/cinema (bottom→top),
    ``UserWaveFiles-N`` = normal scroll. Prefer the matching library first.
    """
    roaming = Path.home() / "AppData" / "Roaming" / "EasyPal"
    reverse = roaming / "UserWaveFiles"
    normal = roaming / "UserWaveFiles-N"
    local_rev = user_data_dir() / "wav" / "user_reverse"
    local_norm = user_data_dir() / "wav" / "user_normal"
    if cinema_scroll:
        ordered = [reverse, local_rev, normal, local_norm]
    else:
        ordered = [normal, local_norm, reverse, local_rev]
    seen: set[Path] = set()
    out: list[Path] = []
    for folder in ordered:
        try:
            key = folder.resolve()
        except OSError:
            key = folder
        if key in seen:
            continue
        seen.add(key)
        out.append(folder)
    return out


def default_wfpic_start_dir(*, cinema_scroll: bool = False) -> Path | None:
    for folder in easypal_user_wave_dirs(cinema_scroll=cinema_scroll):
        if folder.is_dir():
            return folder
    return None


def list_user_wave_images(*, cinema_scroll: bool = False) -> list[Path]:
    found: list[Path] = []
    for folder in easypal_user_wave_dirs(cinema_scroll=cinema_scroll):
        if not folder.is_dir():
            continue
        for path in sorted(folder.iterdir()):
            if path.is_file() and path.suffix.lower() in _IMAGE_SUFFIXES:
                found.append(path)
    return found


def list_user_wave_wavs(*, cinema_scroll: bool = False) -> list[Path]:
    found: list[Path] = []
    for folder in easypal_user_wave_dirs(cinema_scroll=cinema_scroll):
        if not folder.is_dir():
            continue
        for path in sorted(folder.iterdir()):
            if path.is_file() and path.suffix.lower() in _WAV_SUFFIXES:
                found.append(path)
    return found
