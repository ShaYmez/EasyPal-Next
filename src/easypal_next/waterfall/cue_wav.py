"""Load EasyPal program cue WAVs (tune.wav, etc.)."""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

from easypal_next.app.paths import app_root, package_root, user_data_dir

# EasyPal green Tune markers = on-air check tones (same Hz as ``tune.wav`` peaks).
# Remote ops align these clean lines to verify you're on frequency.
TUNE_FREQS_HZ: tuple[float, float, float] = (720.0, 1466.0, 1840.0)
TUNE_MAX_SECONDS = 5.0


def resolve_tune_wav() -> Path | None:
    """Prefer bundled tune.wav, then original EasyPal programwavfiles."""
    candidates = [
        app_root() / "resources" / "wav" / "tune.wav",
        package_root() / "resources" / "wav" / "tune.wav",
        user_data_dir() / "wav" / "tune.wav",
        Path.home() / "AppData" / "Roaming" / "EasyPal" / "programwavfiles" / "tune.wav",
        Path(r"C:\Users") / Path.home().name / "AppData" / "Roaming" / "EasyPal" / "programwavfiles" / "tune.wav",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


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
    # Soft edges avoid PTT/VOX clicks.
    fade = min(int(sample_rate * 0.02), n // 10)
    if fade > 1:
        wave[:fade] *= np.linspace(0.0, 1.0, fade)
        wave[-fade:] *= np.linspace(1.0, 0.0, fade)
    return np.clip(wave * 32767.0, -32767, 32767).astype(np.int16)


def load_tune_pcm(output_rate: int, duration_s: float = TUNE_MAX_SECONDS) -> np.ndarray:
    """Build the three-tone Tune at ``output_rate``, capped at 5 seconds."""
    return synthesize_easypal_tune(
        output_rate, duration_s=min(float(duration_s), TUNE_MAX_SECONDS)
    )
