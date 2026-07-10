"""Community server client abstract interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class CommunityServerClient(ABC):
    @abstractmethod
    async def upload_image(self, path: Path, metadata: dict) -> str: ...

    @abstractmethod
    async def fetch_image(self, image_id: str, dest: Path) -> Path: ...

    @abstractmethod
    async def health_check(self) -> bool: ...
