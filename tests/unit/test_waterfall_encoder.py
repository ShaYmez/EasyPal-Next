"""Tests for waterfall text encoder."""

import numpy as np

from easypal_next.config.schema import WaterfallConfig
from easypal_next.waterfall.encoder import SpectrumPainterEncoder


def test_waterfall_text_produces_audio():
    painter = SpectrumPainterEncoder(WaterfallConfig(line_time_ms=4.0, line_repeats=1))
    audio = painter.text_to_audio("VK4AES", font="DejaVu Sans Mono", font_size=14)
    assert isinstance(audio, np.ndarray)
    assert audio.dtype == np.int16
    assert len(audio) > 0
