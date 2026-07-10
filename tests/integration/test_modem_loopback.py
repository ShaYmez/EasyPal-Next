"""Modem ctypes smoke and loopback tests."""

from __future__ import annotations

import numpy as np
import pytest

from easypal_next.app.paths import resolve_libcodec2
from easypal_next.modem.ctypes_backend import CtypesFreeDvModem

pytestmark = pytest.mark.integration

requires_codec2 = pytest.mark.skipif(
    resolve_libcodec2(None) is None,
    reason="libcodec2.dll not available",
)


@requires_codec2
def test_modem_open_close():
    modem = CtypesFreeDvModem(resolve_libcodec2(None))
    modem.open("DATAC3", 8000)
    assert modem.modem_sample_rate == 8000
    assert modem.frame_payload_size > 0
    modem.close()


@requires_codec2
def test_modem_loopback_frame():
    tx = CtypesFreeDvModem(resolve_libcodec2(None))
    rx = CtypesFreeDvModem(resolve_libcodec2(None))
    tx.open("DATAC3", 8000)
    rx.open("DATAC3", 8000)
    received: list[bytes] = []
    rx.set_frame_rx_callback(received.append)

    payload = b"EPNX-loopback-test!!" + b"\x00" * 80
    payload = payload[: rx.frame_payload_size]
    audio = tx.encode_preamble()
    audio = np.concatenate([audio, tx.encode_frame(payload), tx.encode_postamble()])
    silence = np.zeros(tx.modem_sample_rate, dtype=np.int16)
    rx.decode_samples(np.concatenate([silence, audio, silence]))

    assert received, "expected at least one RX frame"
    tx.close()
    rx.close()
