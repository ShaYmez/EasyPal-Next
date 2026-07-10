"""Application-layer packet framing for EasyPal transport."""

from __future__ import annotations

import struct
from enum import IntEnum

MAGIC = b"EPNX"
VERSION = 1
HEADER_FMT = ">4sBBIIH"
HEADER_SIZE = struct.calcsize(HEADER_FMT)


class PacketType(IntEnum):
    FILE_META = 0x01
    FEC_SHARD = 0x02
    TX_COMPLETE = 0x03
    KEEPALIVE = 0x04
    HYBRID_REF = 0x05


def frame_packet(packet_type: PacketType, seq: int, total: int, payload: bytes) -> bytes:
    header = struct.pack(
        HEADER_FMT,
        MAGIC,
        VERSION,
        int(packet_type),
        seq,
        total,
        len(payload),
    )
    return header + payload


def parse_packet(data: bytes) -> tuple[PacketType, int, int, bytes]:
    if len(data) < HEADER_SIZE:
        raise ValueError("Packet too short")
    magic, version, ptype, seq, total, length = struct.unpack(HEADER_FMT, data[:HEADER_SIZE])
    if magic != MAGIC:
        raise ValueError("Invalid packet magic")
    if version != VERSION:
        raise ValueError(f"Unsupported packet version: {version}")
    payload = data[HEADER_SIZE : HEADER_SIZE + length]
    if len(payload) != length:
        raise ValueError("Truncated packet payload")
    return PacketType(ptype), seq, total, payload
