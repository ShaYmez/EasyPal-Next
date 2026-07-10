"""Split/reassemble application packets across modem frame payloads."""

from __future__ import annotations

import struct

FRAG_HDR = ">HH"
FRAG_HDR_SIZE = struct.calcsize(FRAG_HDR)


class ModemFramer:
    """Fragment EPNX packets to fit modem frame payload size."""

    def __init__(self, max_payload: int) -> None:
        self._max_chunk = max(1, max_payload - FRAG_HDR_SIZE)
        self._total: int | None = None
        self._buffer: bytearray | None = None
        self._filled_end: int = 0

    def fragment(self, packet: bytes) -> list[bytes]:
        if len(packet) <= self._max_chunk:
            return [struct.pack(FRAG_HDR, len(packet), 0) + packet]
        fragments: list[bytes] = []
        offset = 0
        total = len(packet)
        while offset < total:
            chunk = packet[offset : offset + self._max_chunk]
            fragments.append(struct.pack(FRAG_HDR, total, offset) + chunk)
            offset += len(chunk)
        return fragments

    def feed(self, subframe: bytes) -> bytes | None:
        if len(subframe) < FRAG_HDR_SIZE:
            return None
        total, offset = struct.unpack(FRAG_HDR, subframe[:FRAG_HDR_SIZE])
        if offset >= total:
            return None
        expected = total - offset
        available = subframe[FRAG_HDR_SIZE:]
        if len(available) < expected:
            payload = available
        else:
            payload = available[:expected]
        end = offset + len(payload)
        if end > total:
            return None
        if self._total != total:
            self._total = total
            self._buffer = bytearray(total)
            self._filled_end = 0
        assert self._buffer is not None
        self._buffer[offset:end] = payload
        self._filled_end = max(self._filled_end, end)
        if self._filled_end >= total:
            packet = bytes(self._buffer)
            self.reset()
            return packet
        return None

    def reset(self) -> None:
        self._total = None
        self._buffer = None
        self._filled_end = 0
