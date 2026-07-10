"""Hybrid mode orchestration (future)."""

from __future__ import annotations

from easypal_next.community.client import CommunityServerClient
from easypal_next.fec.packet import PacketType, frame_packet


def build_hybrid_ref_packet(image_id: str, seq: int = 0) -> bytes:
    payload = image_id.encode("ascii", errors="ignore")[:8].ljust(8, b"\x00")
    return frame_packet(PacketType.HYBRID_REF, seq=seq, total=1, payload=payload)


async def fetch_hybrid_image(client: CommunityServerClient, image_id: str, dest):
    return await client.fetch_image(image_id.strip(), dest)
