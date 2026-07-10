"""Local RX/TX gallery index for LAN mobile dashboard."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image


@dataclass
class GalleryEntry:
    id: str
    path: str
    thumb_path: str
    callsign: str
    created_at: str
    direction: str


class GalleryStore:
    def __init__(self, gallery_dir: Path) -> None:
        self._dir = gallery_dir
        self._dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self._dir / "index.json"
        self._entries: list[GalleryEntry] = self._load()

    def _load(self) -> list[GalleryEntry]:
        if not self._index_path.is_file():
            return []
        data = json.loads(self._index_path.read_text(encoding="utf-8"))
        return [GalleryEntry(**item) for item in data]

    def _save(self) -> None:
        self._index_path.write_text(
            json.dumps([asdict(entry) for entry in self._entries], indent=2),
            encoding="utf-8",
        )

    @property
    def gallery_dir(self) -> Path:
        return self._dir

    def received_dir(self) -> Path:
        path = self._dir.parent / "received"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def add_image(
        self,
        image_path: Path,
        *,
        callsign: str,
        direction: str = "rx",
    ) -> GalleryEntry:
        image_id = uuid.uuid4().hex[:12]
        thumb_path = self._dir / f"{image_id}_thumb.jpg"
        try:
            with Image.open(image_path) as image:
                image.thumbnail((320, 320))
                image.save(thumb_path, "JPEG", quality=85)
        except Exception:
            placeholder = Image.new("RGB", (320, 240), color=(30, 77, 140))
            placeholder.save(thumb_path, "JPEG", quality=85)
        entry = GalleryEntry(
            id=image_id,
            path=str(image_path),
            thumb_path=str(thumb_path),
            callsign=callsign,
            created_at=datetime.now(timezone.utc).isoformat(),
            direction=direction,
        )
        self._entries.insert(0, entry)
        self._save()
        return entry

    def list_entries(self, limit: int = 50) -> list[GalleryEntry]:
        return self._entries[:limit]

    def get_entry(self, image_id: str) -> GalleryEntry | None:
        for entry in self._entries:
            if entry.id == image_id:
                return entry
        return None
