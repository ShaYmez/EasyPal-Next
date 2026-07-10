"""Tests for meta codec and file assembler."""

from easypal_next.fec.file_assembler import FileMeta
from easypal_next.fec.meta_codec import pack_file_meta, pack_fec_shard, unpack_fec_shard, unpack_file_meta


def test_file_meta_roundtrip():
    meta = FileMeta(
        filename="test.jpg",
        file_size=12345,
        sha256="ab" * 32,
        chunk_count=3,
        fec_k=4,
        fec_m=6,
    )
    packed = pack_file_meta(meta, chunk_size=1024)
    restored, chunk_size = unpack_file_meta(packed)
    assert restored.filename == meta.filename
    assert restored.file_size == meta.file_size
    assert restored.sha256 == meta.sha256
    assert chunk_size == 1024


def test_fec_shard_roundtrip():
    payload = pack_fec_shard(2, 5, b"shard-data")
    chunk_id, shard_index, data = unpack_fec_shard(payload)
    assert chunk_id == 2
    assert shard_index == 5
    assert data == b"shard-data"
