"""Spectrum painter encoder (IFFT column painting)."""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np
from PIL import Image

from easypal_next.config.schema import WaterfallConfig
from easypal_next.waterfall.painter import WaterfallPainter
from easypal_next.waterfall.text_renderer import render_text_bitmap


class SpectrumPainterEncoder(WaterfallPainter):
    def __init__(self, config: WaterfallConfig) -> None:
        self._config = config

    def _bitmap_to_audio(self, image: Image.Image) -> np.ndarray:
        gray = image.convert("L")
        width, height = gray.size
        pixels = np.array(gray, dtype=np.float32) / 255.0
        samples_per_col = int(self._config.sample_rate * self._config.line_time_ms / 1000.0)
        freq_bins = np.linspace(
            self._config.freq_min_hz,
            self._config.freq_max_hz,
            num=height,
        )
        output: list[np.ndarray] = []
        for col in range(width):
            column = pixels[:, col]
            for _ in range(self._config.line_repeats):
                spectrum = np.zeros(samples_per_col // 2 + 1, dtype=np.complex64)
                for row, intensity in enumerate(column):
                    if intensity <= 0.01:
                        continue
                    bin_index = int(row * len(spectrum) / height)
                    bin_index = min(bin_index, len(spectrum) - 1)
                    spectrum[bin_index] = intensity
                time_domain = np.fft.irfft(spectrum, n=samples_per_col)
                time_domain = time_domain / (np.max(np.abs(time_domain)) + 1e-9) * 0.8
                output.append((time_domain * 32767).astype(np.int16))
        if not output:
            return np.zeros(0, dtype=np.int16)
        return np.concatenate(output)

    def text_to_audio(self, text: str, *, font: str, font_size: int) -> np.ndarray:
        bitmap = render_text_bitmap(text, font_name=font, font_size=font_size)
        return self._bitmap_to_audio(bitmap)

    def image_to_audio(self, image_path: Path) -> np.ndarray:
        return self._bitmap_to_audio(Image.open(image_path))

    def save_wav(self, samples: np.ndarray, path: Path, sample_rate: int) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(path), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(sample_rate)
            handle.writeframes(samples.tobytes())
        return path

    def load_wav(self, path: Path) -> np.ndarray:
        with wave.open(str(path), "rb") as handle:
            frames = handle.readframes(handle.getnframes())
        return np.frombuffer(frames, dtype=np.int16)
