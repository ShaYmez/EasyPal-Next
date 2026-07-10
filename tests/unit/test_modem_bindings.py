"""Unit smoke test for FreeDV ctypes modem bindings."""

from __future__ import annotations

import pytest

from easypal_next.app.paths import resolve_libcodec2
from easypal_next.modem.ctypes_backend import CtypesFreeDvModem

requires_codec2 = pytest.mark.skipif(
    resolve_libcodec2(None) is None,
    reason="libcodec2.dll not available",
)


@requires_codec2
def test_modem_bindings_smoke():
    modem = CtypesFreeDvModem(resolve_libcodec2(None))
    modem.open("DATAC3", 8000)
    assert modem.modem_sample_rate == 8000
    assert 100 <= modem.frame_payload_size <= 256
    modem.close()
