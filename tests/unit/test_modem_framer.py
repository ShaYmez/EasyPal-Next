"""Tests for modem packet fragmentation."""

from easypal_next.modem.framer import ModemFramer


def test_framer_roundtrip_small_packet():
    framer = ModemFramer(max_payload=126)
    packet = b"EPNX" + b"\x01" * 50
    fragments = framer.fragment(packet)
    assert len(fragments) == 1
    rx = ModemFramer(126)
    assert rx.feed(fragments[0]) == packet


def test_framer_roundtrip_large_packet():
    framer = ModemFramer(max_payload=126)
    packet = b"X" * 500
    fragments = framer.fragment(packet)
    assert len(fragments) > 1
    rx = ModemFramer(126)
    result = None
    for frag in fragments:
        result = rx.feed(frag)
    assert result == packet


def test_framer_file_meta_size():
    """FILE_META with long filename must fit via fragmentation."""
    framer = ModemFramer(max_payload=126)
    name = "a_very_long_filename_for_testing.jpg"
    meta_body = b"\x00\x15" + name.encode() + b"\x00" * 60
    packet = b"EPNX\x01\x01\x00\x00\x00\x01\x00\x00\x00\x01" + len(meta_body).to_bytes(2, "big") + meta_body
    fragments = framer.fragment(packet)
    rx = ModemFramer(126)
    result = None
    for frag in fragments:
        result = rx.feed(frag)
    assert result == packet
