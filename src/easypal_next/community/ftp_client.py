"""FTP auto-upload client for user-owned gallery servers."""

from __future__ import annotations

from pathlib import Path

from easypal_next.community.client import CommunityServerClient
from easypal_next.config.schema import CommunityServerConfig


class FtpCommunityClient(CommunityServerClient):
    def __init__(self, config: CommunityServerConfig) -> None:
        if not config.ftp_host or not config.ftp_user:
            raise ValueError("FTP host and user are required")
        self._config = config

    async def upload_image(self, path: Path, metadata: dict) -> str:
        raise NotImplementedError("FTP upload planned for community server integration")

    async def fetch_image(self, image_id: str, dest: Path) -> Path:
        raise NotImplementedError("FTP fetch not supported")

    async def health_check(self) -> bool:
        return False
