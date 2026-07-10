"""Tests for zfec encode/decode."""

import pytest

zfec = pytest.importorskip("zfec")

from easypal_next.config.schema import FecConfig
from easypal_next.fec.decoder import FecDecoder
from easypal_next.fec.encoder import FecEncoder


def test_fec_roundtrip():
    config = FecConfig(k=4, m=6, chunk_size=32)
    encoder = FecEncoder(config)
    decoder = FecDecoder(config)
    chunk = b"perfect-mode-test-payload!!!!!"
    shards = encoder.encode_chunk(chunk)
    decoded = decoder.decode_chunk(
        [shards[0], shards[2], shards[4], shards[5]],
        [0, 2, 4, 5],
        len(chunk),
    )
    assert decoded == chunk
