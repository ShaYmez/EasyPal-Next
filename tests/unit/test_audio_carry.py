"""Tests for sounddevice TX carry buffer."""

import numpy as np

from easypal_next.audio.sounddevice_engine import SoundDeviceEngine


def test_tx_carry_preserves_long_frame():
    engine = SoundDeviceEngine()
    engine.open(None, None, 48000, 1024)
    engine._tx_carry = np.array([], dtype=np.int16)  # noqa: SLF001
    long_frame = np.arange(6000, dtype=np.int16)
    engine.write_tx(long_frame)

    outdata = np.zeros((1024, 1), dtype=np.float32)
    engine._output_callback(outdata, 1024, None, None)  # noqa: SLF001
    assert len(engine._tx_carry) == 6000 - 1024  # noqa: SLF001
    assert np.any(outdata[:, 0] != 0)

    outdata2 = np.zeros((1024, 1), dtype=np.float32)
    engine._output_callback(outdata2, 1024, None, None)  # noqa: SLF001
    assert len(engine._tx_carry) == 6000 - 2048  # noqa: SLF001
