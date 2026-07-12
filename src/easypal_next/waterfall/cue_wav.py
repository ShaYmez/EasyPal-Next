"""Load EasyPal program cue WAVs (tune.wav, fileok, bsr, etc.)."""

from __future__ import annotations

import threading
import wave
from pathlib import Path

import numpy as np

from easypal_next.app.paths import app_root, package_root, user_data_dir

# EasyPal green Tune markers = on-air check tones (same Hz as ``tune.wav`` peaks).
TUNE_FREQS_HZ: tuple[float, float, float] = (720.0, 1466.0, 1840.0)
TUNE_MAX_SECONDS = 5.0


def _easypal_program_dirs() -> list[Path]:
    return [
        user_data_dir() / "wav",
        package_root() / "resources" / "wav",
        app_root() / "resources" / "wav",
        Path.home() / "AppData" / "Roaming" / "EasyPal" / "programwavfiles",
        Path.home() / "AppData" / "Roaming" / "EasyPal" / "UserWaveFiles-N",
        Path.home() / "AppData" / "Roaming" / "EasyPal" / "UserWaveFiles",
    ]


def resolve_program_cue(name: str | None, *, negative: bool = False) -> Path | None:
    """Resolve an EasyPal cue stem (e.g. ``fileok``, ``bsr``) to a WAV path.

    When ``negative`` is True, prefer the ``-n`` variant (EasyPal white-on-black cues).
    """
    raw = (name or "").strip()
    if not raw:
        return None
    direct = Path(raw).expanduser()
    if direct.is_file():
        return direct

    stem = Path(raw).stem
    names: list[str] = []
    if negative:
        names.append(f"{stem}-n.wav")
    names.append(f"{stem}.wav")
    if not negative:
        names.append(f"{stem}-n.wav")

    for folder in _easypal_program_dirs():
        if not folder.is_dir():
            continue
        for filename in names:
            path = folder / filename
            if path.is_file():
                return path
    return None


def resolve_tune_wav() -> Path | None:
    """Prefer bundled tune.wav, then original EasyPal programwavfiles."""
    return resolve_program_cue("tune", negative=False)


def load_wav_int16(path: Path) -> tuple[np.ndarray, int]:
    """Return mono int16 samples and sample rate."""
    with wave.open(str(path), "rb") as handle:
        channels = handle.getnchannels()
        sample_rate = handle.getframerate()
        width = handle.getsampwidth()
        frames = handle.readframes(handle.getnframes())
    if width == 1:
        raw = np.frombuffer(frames, dtype=np.uint8).astype(np.float64) - 128.0
        samples = (raw / 128.0 * 32767.0).astype(np.int16)
    elif width == 2:
        samples = np.frombuffer(frames, dtype=np.int16).copy()
    else:
        raise ValueError(f"Unsupported WAV sample width: {width}")
    if channels > 1:
        samples = samples.reshape(-1, channels)[:, 0].copy()
    return samples, int(sample_rate)


def resample_int16(samples: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
    if src_rate == dst_rate or len(samples) == 0:
        return samples
    audio = samples.astype(np.float64)
    n_out = max(1, int(round(len(audio) * float(dst_rate) / float(src_rate))))
    x_old = np.linspace(0.0, 1.0, num=len(audio), endpoint=False)
    x_new = np.linspace(0.0, 1.0, num=n_out, endpoint=False)
    out = np.interp(x_new, x_old, audio)
    return np.clip(out, -32767, 32767).astype(np.int16)


def synthesize_easypal_tune(sample_rate: int, duration_s: float = TUNE_MAX_SECONDS) -> np.ndarray:
    """Three-tone Tune matching EasyPal ``tune.wav`` / green waterfall markers."""
    duration_s = min(float(duration_s), TUNE_MAX_SECONDS)
    n = max(1, int(sample_rate * duration_s))
    t = np.arange(n, dtype=np.float64) / float(sample_rate)
    wave = np.zeros(n, dtype=np.float64)
    for freq in TUNE_FREQS_HZ:
        wave += np.sin(2.0 * np.pi * freq * t)
    wave /= float(len(TUNE_FREQS_HZ))
    wave *= 0.55
    fade = min(int(sample_rate * 0.02), n // 10)
    if fade > 1:
        wave[:fade] *= np.linspace(0.0, 1.0, fade)
        wave[-fade:] *= np.linspace(1.0, 0.0, fade)
    return np.clip(wave * 32767.0, -32767, 32767).astype(np.int16)


def load_tune_pcm(output_rate: int, duration_s: float = TUNE_MAX_SECONDS) -> np.ndarray:
    """Prefer EasyPal/bundled ``tune.wav``, else synthesize three-tone at ``output_rate``."""
    duration_s = min(float(duration_s), TUNE_MAX_SECONDS)
    path = resolve_tune_wav()
    if path is not None:
        try:
            samples, rate = load_wav_int16(path)
            if rate != output_rate:
                samples = resample_int16(samples, rate, output_rate)
            n = max(1, int(output_rate * duration_s))
            if len(samples) > n:
                samples = samples[:n]
            elif len(samples) < n:
                pad = np.zeros(n - len(samples), dtype=np.int16)
                samples = np.concatenate([samples, pad])
            return samples
        except (OSError, ValueError):
            pass
    return synthesize_easypal_tune(output_rate, duration_s=duration_s)


def play_program_cue(
    name: str | None,
    *,
    negative: bool = False,
    stop_event: threading.Event | None = None,
) -> bool:
    """Play a program cue via WinMM. Returns False if the WAV is missing."""
    path = resolve_program_cue(name, negative=negative)
    if path is None:
        return False
    from easypal_next.waterfall.winmm_play import play_pcm_winmm

    samples, rate = load_wav_int16(path)
    play_pcm_winmm(samples, sample_rate=rate, stop_event=stop_event)
    return True
