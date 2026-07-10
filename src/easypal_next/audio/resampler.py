"""Audio sample rate conversion between sound card and modem."""

from __future__ import annotations

import numpy as np


def resample_linear(samples: np.ndarray, input_rate: int, output_rate: int) -> np.ndarray:
    """Simple linear resampling (deterministic, no scipy dependency)."""
    if input_rate == output_rate or len(samples) == 0:
        return samples.astype(np.int16, copy=False)
    ratio = output_rate / input_rate
    output_len = max(1, int(round(len(samples) * ratio)))
    x_old = np.linspace(0.0, 1.0, num=len(samples), endpoint=False)
    x_new = np.linspace(0.0, 1.0, num=output_len, endpoint=False)
    interpolated = np.interp(x_new, x_old, samples.astype(np.float64))
    return np.clip(interpolated, -32768, 32767).astype(np.int16)


def downsample_to_modem(samples: np.ndarray, audio_rate: int, modem_rate: int) -> np.ndarray:
    return resample_linear(samples, audio_rate, modem_rate)


def upsample_from_modem(samples: np.ndarray, modem_rate: int, audio_rate: int) -> np.ndarray:
    return resample_linear(samples, modem_rate, audio_rate)
