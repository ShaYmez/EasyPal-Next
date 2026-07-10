"""Reassemble chunked file from FEC shards."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from easypal_next.config.schema import FecConfig
from easypal_next.fec.decoder import FecDecoder


@dataclass
class FileMeta:
    filename: str
    file_size: int
    sha256: str
    chunk_count: int
    fec_k: int
    fec_m: int


@dataclass
class FileAssembler:
    meta: FileMeta | None = None
    chunk_size: int = 1024
    _chunks: dict[int, bytes] = field(default_factory=dict)
    _shards: dict[tuple[int, int], bytes] = field(default_factory=dict)
    _decoder: FecDecoder | None = None

    def set_meta(self, meta: FileMeta, chunk_size: int = 1024) -> None:
        self.meta = meta
        self.chunk_size = chunk_size
        self._chunks.clear()
        self._shards.clear()
        self._decoder = FecDecoder(
            FecConfig(k=meta.fec_k, m=meta.fec_m, chunk_size=chunk_size)
        )

    def add_shard(self, chunk_id: int, shard_index: int, data: bytes) -> bool:
        self._shards[(chunk_id, shard_index)] = data
        if self.meta is None or self._decoder is None:
            return False
        indices = sorted(idx for (cid, idx) in self._shards if cid == chunk_id)
        if len(indices) < self.meta.fec_k:
            return False
        blocks = [self._shards[(chunk_id, idx)] for idx in indices[: self.meta.fec_k]]
        sharenums = indices[: self.meta.fec_k]
        original_len = self.chunk_size
        if chunk_id == self.meta.chunk_count - 1 and self.meta.file_size % self.chunk_size:
            original_len = self.meta.file_size % self.chunk_size
        try:
            chunk_data = self._decoder.decode_chunk(blocks, sharenums, original_len)
        except (ValueError, Exception):
            return False
        self._chunks[chunk_id] = chunk_data
        return True

    def add_chunk(self, chunk_id: int, data: bytes) -> None:
        self._chunks[chunk_id] = data

    def is_complete(self) -> bool:
        if self.meta is None:
            return False
        return len(self._chunks) >= self.meta.chunk_count

    def write_file(self, output_path: Path) -> Path:
        if not self.is_complete() or self.meta is None:
            raise RuntimeError("File assembly incomplete")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("wb") as handle:
            for chunk_id in range(self.meta.chunk_count):
                handle.write(self._chunks[chunk_id])
        digest = hashlib.sha256(output_path.read_bytes()).hexdigest()
        if digest != self.meta.sha256:
            raise ValueError("SHA256 mismatch after assembly")
        return output_path
