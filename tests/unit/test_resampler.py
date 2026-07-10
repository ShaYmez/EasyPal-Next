"""Tests for audio resampler."""

import numpy as np
import pytest

from easypal_next.audio.resampler import downsample_to_modem, upsample_from_modem


def test_resample_roundtrip_length():
    src = np.arange(4800, dtype=np.int16)
    down = downsample_to_modem(src, 48000, 8000)
    up = upsample_from_modem(down, 8000, 48000)
    assert len(up) == pytest.approx(len(src), rel=0.1)
