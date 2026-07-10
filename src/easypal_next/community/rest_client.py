"""REST community server client (future implementation)."""

from __future__ import annotations

from pathlib import Path

import httpx

from easypal_next.community.client import CommunityServerClient
from easypal_next.config.schema import CommunityServerConfig


class RestCommunityClient(CommunityServerClient):
    def __init__(self, config: CommunityServerConfig) -> None:
        if not config.base_url:
            raise ValueError("community.base_url is required")
        self._base_url = config.base_url.rstrip("/")
        self._api_key = config.api_key
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=30.0)

    async def upload_image(self, path: Path, metadata: dict) -> str:
        headers = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        with path.open("rb") as handle:
            response = await self._client.post(
                "/api/v1/images",
                files={"file": (path.name, handle)},
                data=metadata,
                headers=headers,
            )
        response.raise_for_status()
        return response.json()["image_id"]

    async def fetch_image(self, image_id: str, dest: Path) -> Path:
        response = await self._client.get(f"/api/v1/images/{image_id}")
        response.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(response.content)
        return dest

    async def health_check(self) -> bool:
        try:
            response = await self._client.get("/api/v1/health")
            return response.status_code == 200
        except httpx.HTTPError:
            return False
