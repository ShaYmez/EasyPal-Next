"""Prepare images for HamDRM TX the way EasyPal LoadPIC does."""

from __future__ import annotations

import logging
from pathlib import Path

from easypal_next.app.paths import user_data_dir
from easypal_next.modem.embed_txt import embed_text_on_image

logger = logging.getLogger(__name__)

# EasyPal LoadPIC resizes large images down to 1280×1024 before JP2/JPEG TX.
_MAX_WIDTH = 1280
_MAX_HEIGHT = 1024
_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp"}


def prepare_hamdrm_tx_file(
    path: Path,
    *,
    jpeg_quality: int = 75,
    embed_text: str | None = None,
) -> Path:
    """Return a TX-ready file path (compressed JPEG for images, else original).

    EasyPal converts LoadPIC images to a compact JPEG-2000 object before DRM.
    We use JPEG (Pillow) so a large PNG is not sent raw. Optional EmbedTxt
    overlays text before compression.
    """
    src = Path(path).resolve()
    if not src.is_file():
        raise FileNotFoundError(src)
    if src.suffix.lower() not in _IMAGE_SUFFIXES:
        return src

    try:
        from PIL import Image
    except ImportError:
        logger.warning("Pillow unavailable — sending original image bytes")
        return src

    staging = user_data_dir() / "tx_staging"
    staging.mkdir(parents=True, exist_ok=True)
    out = staging / f"Pic-{src.stem[:40]}.jpg"

    with Image.open(src) as image:
        image = image.convert("RGB")
        image.thumbnail((_MAX_WIDTH, _MAX_HEIGHT), Image.Resampling.LANCZOS)
        if embed_text and embed_text.strip():
            image = embed_text_on_image(image, embed_text.strip())
        image.save(out, format="JPEG", quality=int(jpeg_quality), optimize=True)

    src_kb = src.stat().st_size / 1024.0
    out_kb = out.stat().st_size / 1024.0
    logger.info(
        "HamDRM TX image prepared: %s (%.1f KB) → %s (%.1f KB, q=%s)",
        src.name,
        src_kb,
        out.name,
        out_kb,
        jpeg_quality,
    )
    return out
