"""WFTxt / Tune parity helpers against EasyPal goldens."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from easypal_next.config.schema import AppConfig, WaterfallConfig
from easypal_next.waterfall.cue_wav import TUNE_FREQS_HZ, load_tune_pcm, resolve_tune_wav
from easypal_next.waterfall.encoder import SpectrumPainterEncoder
from easypal_next.waterfall.text_renderer import PAINT_HZ_PER_PIXEL, paint_height_for_band
from easypal_next.waterfall.tx_pcm import encode_waterfall_text
from easypal_next.waterfall.winmm_play import write_temp_wav


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "wftxt_goldens" / "compare.json"


def test_paint_grid_matches_easypal_display_density():
    assert PAINT_HZ_PER_PIXEL == pytest.approx(12.0)
    height = paint_height_for_band(100, 2700)
    assert 100 <= height <= 220
    assert (2700 - 100) / height == pytest.approx(PAINT_HZ_PER_PIXEL, rel=0.05)


def test_encode_peak_near_easypal_cue_loudness():
    cfg = WaterfallConfig(line_time_ms=41.0, min_body_seconds=3.2)
    audio = SpectrumPainterEncoder(cfg).text_to_audio(
        "TEST", font=cfg.default_font, font_size=cfg.default_font_size, min_columns=8
    )
    peak = int(np.max(np.abs(audio)))
    # EasyPal cues ~9–11k; allow a band around calibrated 0.35 FS.
    assert 7000 <= peak <= 14000


def test_short_wftxt_stretched_to_cue_duration():
    app = AppConfig(waterfall=WaterfallConfig(min_body_seconds=3.2, line_time_ms=41.0))
    pcm = encode_waterfall_text(app, "HI")
    dur = len(pcm) / float(app.waterfall.sample_rate)
    assert dur >= 3.0
    assert dur <= 4.5


def test_encode_waterfall_text_slash_zeros_changes_audio():
    plain = encode_waterfall_text(
        AppConfig(waterfall=WaterfallConfig(slash_zeros=False)),
        "M0VUB 00",
    )
    slashed = encode_waterfall_text(
        AppConfig(waterfall=WaterfallConfig(slash_zeros=True)),
        "M0VUB 00",
    )
    assert not np.array_equal(plain, slashed)


def test_compare_json_targets_present():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert data["targets"]["paint_hz_per_pixel"] == 12.0
    assert data["targets"]["line_time_ms"] == 41.0
    assert data["easypal_tune"]["peaks_hz"] == [720, 1466, 1840]


def test_write_temp_wav_roundtrip():
    pcm = np.zeros(1000, dtype=np.int16)
    pcm[100:200] = 1000
    path = write_temp_wav(pcm, 25000)
    try:
        assert path.is_file()
        assert path.stat().st_size > 44
    finally:
        path.unlink(missing_ok=True)


def test_load_tune_pcm_has_easypal_marker_freqs():
    rate = 11025
    pcm = load_tune_pcm(rate, duration_s=1.0)
    assert len(pcm) == rate
    # FFT peaks near the three markers (whether from file or synth).
    spec = np.abs(np.fft.rfft(pcm.astype(np.float64) * np.hanning(len(pcm))))
    freqs = np.fft.rfftfreq(len(pcm), 1.0 / rate)
    for target in TUNE_FREQS_HZ:
        near = (freqs > target - 30) & (freqs < target + 30)
        assert float(spec[near].max()) > float(spec.max()) * 0.15


@pytest.mark.skipif(resolve_tune_wav() is None, reason="EasyPal/bundled tune.wav not installed")
def test_resolve_tune_wav_when_present():
    path = resolve_tune_wav()
    assert path is not None
    assert path.is_file()
