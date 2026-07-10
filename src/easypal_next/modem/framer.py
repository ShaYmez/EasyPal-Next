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
        self._parts: list[bytes] = []

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
        payload = subframe[FRAG_HDR_SIZE:]
        if offset + len(payload) > total:
            return None
        if offset == 0:
            self._total = total
            self._parts = []
        elif self._total != total:
            self._total = total
            self._parts = []
        self._parts.append(payload)
        reassembled = b"".join(self._parts)
        if self._total is not None and len(reassembled) >= self._total:
            packet = reassembled[: self._total]
            self._total = None
            self._parts = []
            return packet
        return None

    def reset(self) -> None:
        self._total = None
        self._parts = []
