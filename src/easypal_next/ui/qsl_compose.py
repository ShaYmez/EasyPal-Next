"""Minimal Pic/QSL compose from EasyPal Layer backgrounds."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from easypal_next.app.paths import user_data_dir
from easypal_next.modem.embed_txt import embed_text_on_image


def qsl_template_dirs() -> list[Path]:
    return [
        user_data_dir() / "qsl",
        Path.home() / "AppData" / "Roaming" / "EasyPal" / "Layer",
        Path.home() / "AppData" / "Roaming" / "EasyPal" / "misc",
    ]


def list_qsl_templates() -> list[Path]:
    found: list[Path] = []
    for folder in qsl_template_dirs():
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("*")):
            if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".gif"}:
                found.append(path)
    return found


def compose_qsl(
    template: Path,
    *,
    callsign: str,
    extra_text: str = "",
    out_path: Path | None = None,
) -> Path:
    """Flatten template + callsign (and optional line) to a JPEG for TX."""
    call = (callsign or "N0CALL").strip().upper() or "N0CALL"
    with Image.open(template) as src:
        image = src.convert("RGB")
    line = call if not extra_text.strip() else f"{call}  {extra_text.strip()}"
    image = embed_text_on_image(image, line, font_size=max(24, image.size[1] // 18))

    dest = out_path or (user_data_dir() / "tx_staging" / f"QSL-{call}.jpg")
    dest.parent.mkdir(parents=True, exist_ok=True)
    image.save(dest, format="JPEG", quality=85, optimize=True)
    return dest
