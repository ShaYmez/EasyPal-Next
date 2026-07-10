"""Render text to monochrome bitmap for spectrum painting."""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont


def render_text_bitmap(
    text: str,
    *,
    font_name: str = "DejaVu Sans Mono",
    font_size: int = 16,
    width: int = 512,
    height: int = 64,
) -> Image.Image:
    image = Image.new("L", (width, height), color=0)
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype(font_name, font_size)
    except OSError:
        font = ImageFont.load_default()
    draw.text((4, 8), text, fill=255, font=font)
    return image
