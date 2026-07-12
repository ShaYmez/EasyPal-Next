"""EmbedTxt — overlay text on TX images (EasyPal EmbedTxt habit)."""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont


def embed_text_on_image(
    image: Image.Image,
    text: str,
    *,
    font_name: str = "Tahoma",
    font_size: int = 28,
    margin: int = 12,
) -> Image.Image:
    """Draw ``text`` in the bottom-left of ``image`` (RGB)."""
    msg = (text or "").strip()
    if not msg:
        return image
    canvas = image.convert("RGB").copy()
    draw = ImageDraw.Draw(canvas)
    font = None
    for name in (font_name, "Tahoma", "Arial", "DejaVu Sans"):
        try:
            font = ImageFont.truetype(name, font_size)
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), msg, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = margin
    y = max(margin, canvas.size[1] - th - margin - bbox[1])
    # Soft shadow for readability on bright/dark pics.
    draw.text((x + 1, y + 1), msg, fill=(0, 0, 0), font=font)
    draw.text((x, y), msg, fill=(255, 255, 220), font=font)
    return canvas
