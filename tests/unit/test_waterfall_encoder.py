"""Tests for waterfall text encoder."""

import numpy as np

from easypal_next.config.schema import WaterfallConfig
from easypal_next.waterfall.encoder import SpectrumPainterEncoder


def test_waterfall_text_produces_audio():
    painter = SpectrumPainterEncoder(
        WaterfallConfig(line_time_ms=20.0, line_repeats=1, sample_rate=25000)
    )
    audio = painter.text_to_audio("VK4AES", font="Tahoma", font_size=24)
    assert isinstance(audio, np.ndarray)
    assert audio.dtype == np.int16
    assert len(audio) > 0
    # EasyPal-like pace: short callsign should be around 1+ seconds, not a flash.
    assert len(audio) / 25000.0 > 0.8


def test_waterfall_text_energy_stays_in_configured_band():
    """Glyph energy must land in freq_min–freq_max, not across full Nyquist."""
    cfg = WaterfallConfig(
        sample_rate=48000,
        freq_min_hz=100,
        freq_max_hz=2500,
        line_time_ms=8.0,
        line_repeats=1,
    )
    painter = SpectrumPainterEncoder(cfg)
    audio = painter.text_to_audio("M0VUB", font=cfg.default_font, font_size=cfg.default_font_size)
    assert len(audio) > 0

    n = int(cfg.sample_rate * cfg.line_time_ms / 1000.0)
    # Use the second half of a loud column (after amp crossfade settles).
    loud = None
    for i in range(0, len(audio) - n + 1, n):
        chunk = audio[i : i + n].astype(np.float64)
        if np.max(np.abs(chunk)) > 1000:
            loud = chunk[n // 2 :]
            break
    assert loud is not None, "expected non-silent glyph columns"

    spec = np.abs(np.fft.rfft(loud * np.hanning(len(loud))))
    freqs = np.fft.rfftfreq(len(loud), 1.0 / cfg.sample_rate)
    inband = float(spec[(freqs >= 80) & (freqs <= 2600)].sum())
    outband = float(spec[(freqs > 3500)].sum())
    total = float(spec.sum()) + 1e-12
    assert inband / total > 0.75
    assert outband / total < 0.15


def test_waterfall_text_has_multiple_tones_not_single_chirp():
    """A letter column should excite several frequencies (readable glyph)."""
    cfg = WaterfallConfig(line_time_ms=8.0, line_repeats=1)
    audio = SpectrumPainterEncoder(cfg).text_to_audio(
        "H", font=cfg.default_font, font_size=cfg.default_font_size
    )
    n = int(cfg.sample_rate * cfg.line_time_ms / 1000.0)
    for i in range(0, len(audio) - n + 1, n):
        chunk = audio[i : i + n].astype(np.float64)
        if np.max(np.abs(chunk)) < 1000:
            continue
        spec = np.abs(np.fft.rfft(chunk))
        freqs = np.fft.rfftfreq(n, 1.0 / cfg.sample_rate)
        band = (freqs >= 100) & (freqs <= 2500)
        peaks = int(np.sum(spec[band] > (spec[band].max() * 0.2)))
        assert peaks >= 2
        return
    raise AssertionError("no loud glyph column found")
