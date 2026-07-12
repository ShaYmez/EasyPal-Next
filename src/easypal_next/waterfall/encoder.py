"""Spectrum painter encoder — continuous-phase additive sines (EasyPal WFTxt)."""

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
        """Paint bitmap columns as continuous-phase multi-tones in freq_min–freq_max."""
        gray = image.convert("L")
        pixels = np.array(gray, dtype=np.float64) / 255.0
        height, width = pixels.shape[0], pixels.shape[1]
        pixels = np.where(pixels < 0.08, 0.0, pixels)

        repeats = max(1, int(self._config.line_repeats))
        if repeats > 1:
            pixels = np.repeat(pixels, repeats, axis=1)
            width = pixels.shape[1]

        sample_rate = int(self._config.sample_rate)
        samples_per_col = max(
            64,
            int(round(sample_rate * self._config.line_time_ms / 1000.0)),
        )
        freqs = np.linspace(
            float(self._config.freq_max_hz),
            float(self._config.freq_min_hz),
            num=height,
            dtype=np.float64,
        )
        valid = (freqs > 40.0) & (freqs < sample_rate * 0.45)
        freqs = np.where(valid, freqs, 0.0)
        pixels = pixels * valid[:, None]

        dphi = 2.0 * np.pi * freqs / float(sample_rate)
        phase = np.zeros(height, dtype=np.float64)
        prev_amp = np.zeros(height, dtype=np.float64)
        # Cosine crossfade reduces column-edge clicks vs linear ramp.
        ramp = 0.5 - 0.5 * np.cos(np.linspace(0.0, np.pi, samples_per_col, dtype=np.float64))
        ramp = ramp[:, None]
        pieces: list[np.ndarray] = []

        for col in range(width):
            target = pixels[:, col].copy()
            amp = prev_amp[None, :] * (1.0 - ramp) + target[None, :] * ramp
            # Normalize per sample by active tone count so dense columns don't clip-grit.
            active = np.maximum(np.sum(amp > 0.05, axis=1, keepdims=True), 1.0)
            amp = amp / np.sqrt(active)
            idx = np.arange(1, samples_per_col + 1, dtype=np.float64)[:, None]
            phi = phase[None, :] + idx * dphi[None, :]
            col_wave = np.sum(amp * np.sin(phi), axis=1)
            pieces.append(col_wave)
            phase = (phase + samples_per_col * dphi) % (2.0 * np.pi)
            prev_amp = target

        if width > 0 and float(np.max(prev_amp)) > 0.0:
            target = np.zeros(height, dtype=np.float64)
            amp = prev_amp[None, :] * (1.0 - ramp)
            active = np.maximum(np.sum(amp > 0.05, axis=1, keepdims=True), 1.0)
            amp = amp / np.sqrt(active)
            idx = np.arange(1, samples_per_col + 1, dtype=np.float64)[:, None]
            phi = phase[None, :] + idx * dphi[None, :]
            pieces.append(np.sum(amp * np.sin(phi), axis=1))

        if not pieces:
            return np.zeros(0, dtype=np.int16)

        audio = np.concatenate(pieces)
        peak = float(np.max(np.abs(audio)))
        if peak > 1e-9:
            audio = audio * (0.65 / peak)
        return np.clip(audio * 32767.0, -32767, 32767).astype(np.int16)

    def text_to_audio(
        self,
        text: str,
        *,
        font: str,
        font_size: int,
        min_columns: int = 80,
    ) -> np.ndarray:
        bitmap = render_text_bitmap(
            text,
            font_name=font,
            font_size=font_size,
            freq_min_hz=self._config.freq_min_hz,
            freq_max_hz=self._config.freq_max_hz,
            negative=bool(getattr(self._config, "negative_paint", False)),
            min_columns=min_columns,
        )
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
