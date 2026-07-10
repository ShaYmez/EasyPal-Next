"""Serialize/deserialize FILE_META and FEC_SHARD payloads."""

from __future__ import annotations

import struct

from easypal_next.fec.file_assembler import FileMeta

def pack_file_meta(meta: FileMeta, chunk_size: int) -> bytes:
    name_bytes = meta.filename.encode("utf-8")[:512]
    sha = bytes.fromhex(meta.sha256)
    if len(sha) != 32:
        raise ValueError("sha256 must be 64 hex chars")
    return struct.pack(
        ">H",
        len(name_bytes),
    ) + name_bytes + struct.pack(
        ">32sQIBBH",
        sha,
        meta.file_size,
        meta.chunk_count,
        meta.fec_k,
        meta.fec_m,
        chunk_size,
    )


def unpack_file_meta(payload: bytes) -> tuple[FileMeta, int]:
    if len(payload) < 2:
        raise ValueError("FILE_META too short")
    name_len = struct.unpack(">H", payload[:2])[0]
    offset = 2 + name_len
    rest = payload[offset:]
    sha, file_size, chunk_count, fec_k, fec_m, chunk_size = struct.unpack(">32sQIBBH", rest)
    filename = payload[2 : 2 + name_len].decode("utf-8")
    return (
        FileMeta(
            filename=filename,
            file_size=file_size,
            sha256=sha.hex(),
            chunk_count=chunk_count,
            fec_k=fec_k,
            fec_m=fec_m,
        ),
        chunk_size,
    )


def pack_fec_shard(chunk_id: int, shard_index: int, data: bytes) -> bytes:
    return struct.pack(">IH", chunk_id, shard_index) + data


def unpack_fec_shard(payload: bytes) -> tuple[int, int, bytes]:
    chunk_id, shard_index = struct.unpack(">IH", payload[:6])
    return chunk_id, shard_index, payload[6:]
