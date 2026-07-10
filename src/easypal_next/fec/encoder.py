"""zfec shard generation."""

from __future__ import annotations

import math

from easypal_next.config.schema import FecConfig

try:
    import zfec
except ImportError as exc:  # pragma: no cover - platform / Python version dependent
    zfec = None  # type: ignore[assignment]
    _ZFEC_IMPORT_ERROR = exc
else:
    _ZFEC_IMPORT_ERROR = None


class FecEncoder:
    def __init__(self, config: FecConfig) -> None:
        if zfec is None:
            raise ImportError(
                "zfec is required for FEC. Use Python 3.11–3.12 and install zfec, "
                "or install Microsoft C++ Build Tools to compile from source."
            ) from _ZFEC_IMPORT_ERROR
        if config.k >= config.m:
            raise ValueError("FEC k must be less than m")
        self._k = config.k
        self._m = config.m
        self._chunk_size = config.chunk_size
        self._encoder = zfec.Encoder(config.k, config.m)

    def encode_chunk(self, chunk: bytes) -> list[bytes]:
        padded = chunk.ljust(self._chunk_size, b"\x00")
        block_size = math.ceil(len(padded) / self._k)
        blocks = [
            padded[i * block_size : (i + 1) * block_size].ljust(block_size, b"\x00")
            for i in range(self._k)
        ]
        return self._encoder.encode(blocks)

    @property
    def k(self) -> int:
        return self._k

    @property
    def m(self) -> int:
        return self._m
