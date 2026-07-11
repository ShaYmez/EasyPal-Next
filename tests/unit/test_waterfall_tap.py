"""Tests for WaterfallTap FFT processing."""

from __future__ import annotations

import numpy as np

from easypal_next.audio.waterfall_tap import WaterfallTap, make_fft_window


def test_make_fft_window_shapes():
    assert len(make_fft_window("hann", 1024)) == 1024
    assert len(make_fft_window("none", 512)) == 512


def test_waterfall_tap_emits_on_tone():
    emitted: list[list[float]] = []
    tap = WaterfallTap(fft_size=256, overlap=0.5, window="hann", on_spectrum=emitted.append)
    t = np.arange(4096, dtype=np.float32)
    tone = (0.5 * np.sin(2 * np.pi * 1000 * t / 48000)).astype(np.float32)
    tap.feed((tone * 32767).astype(np.int16))
    assert len(emitted) >= 1
    assert len(emitted[0]) == 129
    assert max(emitted[0]) > -40.0


def test_waterfall_tap_overlap_produces_multiple_rows():
    emitted: list[list[float]] = []
    tap = WaterfallTap(fft_size=256, overlap=0.5, window="none", on_spectrum=emitted.append)
    noise = np.random.randint(-2000, 2000, 2048, dtype=np.int16)
    tap.feed(noise)
    assert len(emitted) >= 2
