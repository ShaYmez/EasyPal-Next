"""FFT tap for live waterfall display."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

SpectrumCallback = Callable[[list[float]], None]


class WaterfallTap:
    def __init__(self, fft_size: int = 1024, on_spectrum: SpectrumCallback | None = None) -> None:
        self._fft_size = fft_size
        self._on_spectrum = on_spectrum
        self._buffer = np.zeros(fft_size, dtype=np.float32)

    def _to_float(self, samples: np.ndarray) -> np.ndarray:
        chunk = samples.astype(np.float32, copy=False)
        peak = float(np.max(np.abs(chunk))) if len(chunk) else 0.0
        if peak > 1.5:
            chunk = chunk / 32768.0
        return chunk

    def feed(self, samples: np.ndarray) -> None:
        chunk = self._to_float(samples)
        if len(chunk) >= self._fft_size:
            window = chunk[-self._fft_size :]
        else:
            self._buffer = np.roll(self._buffer, -len(chunk))
            self._buffer[-len(chunk) :] = chunk
            window = self._buffer
        spectrum = np.abs(np.fft.rfft(window))
        bins = (20 * np.log10(spectrum + 1e-12)).tolist()
        if self._on_spectrum:
            self._on_spectrum(bins)
