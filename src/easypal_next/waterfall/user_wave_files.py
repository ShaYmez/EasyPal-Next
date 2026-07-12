"""Locate EasyPal UserWaveFiles libraries for WFPic / reverse cinema."""

from __future__ import annotations

from pathlib import Path

from easypal_next.app.paths import user_data_dir


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
