"""EasyPal-style CW ID playback (Transient ID1200 / ID300 WAVs)."""

from __future__ import annotations

import logging
import threading
from pathlib import Path

import numpy as np

from easypal_next.app.paths import package_root, user_data_dir
from easypal_next.waterfall.cue_wav import load_wav_int16, resample_int16
from easypal_next.waterfall.winmm_play import play_pcm_winmm

logger = logging.getLogger(__name__)

# EasyPal: ~1200 Hz end-of-TX ID; ~300 Hz slower/idle ID.
CW_ID_1200 = "ID1200.wav"
CW_ID_300 = "ID300.wav"


def resolve_cw_id_wav(*, tone_hz: int = 1200) -> Path | None:
    name = CW_ID_1200 if int(tone_hz) >= 600 else CW_ID_300
    candidates = [
        user_data_dir() / "wav" / name,
        package_root() / "resources" / "wav" / name,
        Path.home() / "AppData" / "Roaming" / "EasyPal" / "Transient" / name,
        Path(r"C:\Users") / Path.home().name / "AppData" / "Roaming" / "EasyPal" / "Transient" / name,
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


def load_cw_id_pcm(
    *,
    tone_hz: int = 1200,
    play_rate: int | None = None,
) -> tuple[np.ndarray, int] | None:
    path = resolve_cw_id_wav(tone_hz=tone_hz)
    if path is None:
        return None
    samples, rate = load_wav_int16(path)
    if play_rate is not None and play_rate != rate:
        samples = resample_int16(samples, rate, play_rate)
        rate = play_rate
    return samples, rate


def play_cw_id(
    *,
    tone_hz: int = 1200,
    stop_event: threading.Event | None = None,
) -> bool:
    """Play CW ID via WinMM (no PortAudio). Returns False if WAV missing."""
    loaded = load_cw_id_pcm(tone_hz=tone_hz)
    if loaded is None:
        logger.warning("CW ID WAV not found (tone=%s)", tone_hz)
        return False
    samples, rate = loaded
    play_pcm_winmm(samples, sample_rate=rate, stop_event=stop_event)
    return True
