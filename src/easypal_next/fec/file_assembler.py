"""Reassemble chunked file from FEC shards."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path


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
    _chunks: dict[int, bytes] = field(default_factory=dict)
    _shards: dict[tuple[int, int], bytes] = field(default_factory=dict)

    def set_meta(self, meta: FileMeta) -> None:
        self.meta = meta
        self._chunks.clear()
        self._shards.clear()

    def add_shard(self, chunk_id: int, shard_index: int, data: bytes) -> bool:
        self._shards[(chunk_id, shard_index)] = data
        if self.meta is None:
            return False
        indices = [idx for (cid, idx) in self._shards if cid == chunk_id]
        if len(indices) < self.meta.fec_k:
            return False
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
