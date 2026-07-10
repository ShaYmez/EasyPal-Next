"""No-op community client when server integration is disabled."""

from __future__ import annotations

from pathlib import Path

from easypal_next.community.client import CommunityServerClient


class NullCommunityClient(CommunityServerClient):
    async def upload_image(self, path: Path, metadata: dict) -> str:
        raise RuntimeError("Community server integration is disabled")

    async def fetch_image(self, image_id: str, dest: Path) -> Path:
        raise RuntimeError("Community server integration is disabled")

    async def health_check(self) -> bool:
        return False
