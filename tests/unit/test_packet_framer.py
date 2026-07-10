"""Tests for application packet framing."""

from easypal_next.fec.packet import PacketType, frame_packet, parse_packet


def test_packet_roundtrip():
    payload = b"hello-easypal-next"
    framed = frame_packet(PacketType.FEC_SHARD, seq=3, total=10, payload=payload)
    ptype, seq, total, parsed = parse_packet(framed)
    assert ptype == PacketType.FEC_SHARD
    assert seq == 3
    assert total == 10
    assert parsed == payload
