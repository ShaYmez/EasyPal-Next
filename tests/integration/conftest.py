"""Integration tests requiring libcodec2."""

from __future__ import annotations

import pytest

from easypal_next.app.paths import resolve_libcodec2

pytestmark = pytest.mark.integration

requires_codec2 = pytest.mark.skipif(
    resolve_libcodec2(None) is None,
    reason="libcodec2.dll not available",
)
