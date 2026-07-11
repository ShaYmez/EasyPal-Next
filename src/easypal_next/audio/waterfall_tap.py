"""FFT tap for live waterfall display."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

import numpy as np

SpectrumCallback = Callable[[list[float]], None]

FftWindow = Literal["none", "hann", "hamming", "blackman"]


def make_fft_window(name: FftWindow, fft_size: int) -> np.ndarray:
    if name == "hann":
        return np.hanning(fft_size).astype(np.float32)
    if name == "hamming":
        return np.hamming(fft_size).astype(np.float32)
    if name == "blackman":
        return np.blackman(fft_size).astype(np.float32)
    return np.ones(fft_size, dtype=np.float32)


class WaterfallTap:
    """Compute overlapping FFT rows for live spectrum / waterfall feeds."""

    def __init__(
        self,
        fft_size: int = 1024,
        overlap: float = 0.5,
        window: FftWindow = "hann",
        on_spectrum: SpectrumCallback | None = None,
    ) -> None:
        self._fft_size = max(64, fft_size)
        self._overlap = max(0.0, min(0.875, overlap))
        self._hop = max(1, int(self._fft_size * (1.0 - self._overlap)))
        self._window_coef = make_fft_window(window, self._fft_size)
        self._on_spectrum = on_spectrum
        self._buffer = np.zeros(self._fft_size, dtype=np.float32)
        self._fill = 0

    @property
    def fft_size(self) -> int:
        return self._fft_size

    def _to_float(self, samples: np.ndarray) -> np.ndarray:
        chunk = samples.astype(np.float32, copy=False)
        peak = float(np.max(np.abs(chunk))) if len(chunk) else 0.0
        if peak > 1.5:
            chunk = chunk / 32768.0
        return chunk

    def _emit_fft(self) -> None:
        windowed = self._buffer * self._window_coef
        spectrum = np.abs(np.fft.rfft(windowed))
        bins = (20 * np.log10(spectrum + 1e-12)).tolist()
        if self._on_spectrum:
            self._on_spectrum(bins)

    def feed(self, samples: np.ndarray) -> None:
        chunk = self._to_float(samples)
        offset = 0
        while offset < len(chunk):
            need = self._fft_size - self._fill
            take = min(need, len(chunk) - offset)
            self._buffer[self._fill : self._fill + take] = chunk[offset : offset + take]
            self._fill += take
            offset += take
            if self._fill < self._fft_size:
                continue
            self._emit_fft()
            if self._hop >= self._fft_size:
                self._buffer.fill(0.0)
                self._fill = 0
            else:
                remain = self._fft_size - self._hop
                self._buffer[:remain] = self._buffer[self._hop : self._fft_size]
                self._buffer[remain:] = 0.0
                self._fill = remain
