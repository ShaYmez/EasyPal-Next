"""PortAudio-free PCM playback via Windows winsound (WinMM).

HamDRM already owns WinMM on the radio device. Opening PortAudio on the same
output hard-crashes; ``winsound`` plays a temp WAV through the system mapper
after RX is paused and avoids the PortAudio path entirely.
"""

from __future__ import annotations

import tempfile
import threading
import time
import wave
from pathlib import Path

import numpy as np


def write_temp_wav(samples: np.ndarray, sample_rate: int) -> Path:
    """Write mono int16 PCM to a temp ``.wav``; caller must unlink when done."""
    pcm = np.asarray(samples, dtype=np.int16)
    fd, name = tempfile.mkstemp(prefix="easypal-wftxt-", suffix=".wav")
    path = Path(name)
    try:
        with open(fd, "wb") as handle:
            with wave.open(handle, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(int(sample_rate))
                wav.writeframes(pcm.tobytes())
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return path


def play_wav_winmm(
    path: Path,
    *,
    duration_s: float,
    stop_event: threading.Event | None = None,
) -> None:
    """Play ``path`` with winsound; honour ``stop_event`` via purge."""
    import winsound

    flags = winsound.SND_FILENAME | winsound.SND_NODEFAULT
    if stop_event is None:
        winsound.PlaySound(str(path), flags | winsound.SND_SYNC)
        return

    winsound.PlaySound(str(path), flags | winsound.SND_ASYNC)
    deadline = time.monotonic() + max(0.05, float(duration_s) + 0.15)
    try:
        while time.monotonic() < deadline:
            if stop_event.is_set():
                winsound.PlaySound(None, winsound.SND_PURGE)
                return
            time.sleep(0.05)
        # Drain any remaining async buffer.
        time.sleep(0.05)
    finally:
        if stop_event.is_set():
            try:
                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:  # noqa: BLE001
                pass


def play_pcm_winmm(
    samples: np.ndarray,
    *,
    sample_rate: int,
    stop_event: threading.Event | None = None,
) -> None:
    """Write a temp WAV and play it via WinMM/winsound (no PortAudio)."""
    if samples is None or len(samples) == 0:
        return
    path = write_temp_wav(samples, sample_rate)
    try:
        duration_s = len(samples) / float(sample_rate)
        play_wav_winmm(path, duration_s=duration_s, stop_event=stop_event)
    finally:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
