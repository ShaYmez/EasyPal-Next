"""zfec shard reassembly."""

from __future__ import annotations

from easypal_next.config.schema import FecConfig

try:
    import zfec
except ImportError as exc:  # pragma: no cover
    zfec = None  # type: ignore[assignment]
    _ZFEC_IMPORT_ERROR = exc
else:
    _ZFEC_IMPORT_ERROR = None


class FecDecoder:
    def __init__(self, config: FecConfig) -> None:
        if zfec is None:
            raise ImportError(
                "zfec is required for FEC. Use Python 3.11–3.12 and install zfec."
            ) from _ZFEC_IMPORT_ERROR
        self._k = config.k
        self._m = config.m
        self._chunk_size = config.chunk_size
        self._decoder = zfec.Decoder(config.k, config.m)

    def decode_chunk(self, blocks: list[bytes], sharenums: list[int], original_len: int) -> bytes:
        if len(blocks) < self._k:
            raise ValueError(f"Need at least {self._k} shards to decode")
        data = b"".join(self._decoder.decode(blocks[: self._k], sharenums[: self._k]))
        return data[:original_len]

    @property
    def k(self) -> int:
        return self._k
