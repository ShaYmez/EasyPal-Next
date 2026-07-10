"""Local RX/TX gallery index for LAN mobile dashboard."""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tif", ".tiff"}


@dataclass
class GalleryEntry:
    id: str
    path: str
    thumb_path: str
    callsign: str
    created_at: str
    direction: str


def _is_image_path(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_SUFFIXES


class GalleryStore:
    def __init__(self, gallery_dir: Path, received_dir: Path | None = None) -> None:
        self._dir = gallery_dir
        self._dir.mkdir(parents=True, exist_ok=True)
        self._received_dir = Path(received_dir).expanduser() if received_dir else None
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
        if self._received_dir is not None:
            path = self._received_dir
        else:
            path = self._dir.parent / "received"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _save_image_thumb(self, image_path: Path, thumb_path: Path) -> None:
        with Image.open(image_path) as image:
            rgb = image.convert("RGB")
            rgb.thumbnail((320, 320))
            rgb.save(thumb_path, "PNG")

    def _save_file_placeholder(self, file_path: Path, thumb_path: Path) -> None:
        ext = file_path.suffix.upper().lstrip(".") or "FILE"
        canvas = Image.new("RGB", (320, 240), color=(40, 48, 58))
        draw = ImageDraw.Draw(canvas)
        try:
            font = ImageFont.truetype("arial.ttf", 28)
            small = ImageFont.truetype("arial.ttf", 14)
        except OSError:
            font = ImageFont.load_default()
            small = font
        draw.text((24, 90), ext[:8], fill=(245, 197, 24), font=font)
        name = file_path.name
        if len(name) > 28:
            name = name[:25] + "..."
        draw.text((24, 140), name, fill=(200, 210, 220), font=small)
        canvas.save(thumb_path, "PNG")

    def add_image(
        self,
        image_path: Path,
        *,
        callsign: str,
        direction: str = "rx",
    ) -> GalleryEntry:
        image_path = Path(image_path)
        image_id = uuid.uuid4().hex[:12]
        thumb_path = self._dir / f"{image_id}_thumb.png"
        if _is_image_path(image_path):
            try:
                self._save_image_thumb(image_path, thumb_path)
            except Exception as exc:
                logger.warning("thumbnail failed for %s: %s", image_path, exc)
                self._save_file_placeholder(image_path, thumb_path)
        else:
            self._save_file_placeholder(image_path, thumb_path)
        entry = GalleryEntry(
            id=image_id,
            path=str(image_path.resolve()),
            thumb_path=str(thumb_path),
            callsign=callsign,
            created_at=datetime.now(timezone.utc).isoformat(),
            direction=direction,
        )
        self._entries.insert(0, entry)
        self._save()
        return entry

    def list_entries(self, limit: int = 50, direction: str | None = None) -> list[GalleryEntry]:
        items = self._entries
        if direction:
            items = [e for e in items if e.direction == direction]
        return items[:limit]

    def get_entry(self, image_id: str) -> GalleryEntry | None:
        for entry in self._entries:
            if entry.id == image_id:
                return entry
        return None
