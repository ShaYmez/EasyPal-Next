"""Render text to monochrome bitmap for spectrum painting."""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFilter, ImageFont


# EasyPal waterfall display calibration ~11.63 Hz/pixel. Match that density so
# glyphs sound/look like stock WFTxt (18 Hz/px was too sparse / harsh).
PAINT_HZ_PER_PIXEL = 12.0


def paint_height_for_band(freq_min_hz: int, freq_max_hz: int) -> int:
    span = max(100, int(freq_max_hz) - int(freq_min_hz))
    # Allow enough rows for ~12 Hz/px across EasyPal's ~150–2800 Hz paint band.
    return max(64, min(256, int(round(span / PAINT_HZ_PER_PIXEL))))


def render_text_bitmap(
    text: str,
    *,
    font_name: str = "Tahoma",
    font_size: int = 24,
    width: int = 512,
    height: int | None = None,
    freq_min_hz: int = 100,
    freq_max_hz: int = 2500,
    negative: bool = False,
    min_columns: int = 80,
    slash_zeros: bool = False,
) -> Image.Image:
    """Render waterfall text for SpectrumPainter.

    X = time, Y = frequency (top = high Hz after encode).
    Positive paint (default): bright glyphs = tones (classic readable WFTxt).
    Negative paint: filled band with letter holes — padding stays silent.
    """
    if height is None:
        height = paint_height_for_band(freq_min_hz, freq_max_hz)

    image = Image.new("L", (width, height), color=0)
    draw = ImageDraw.Draw(image)

    font = None
    for name in (font_name, "Tahoma", "Arial", "DejaVu Sans Mono"):
        for size in (font_size, 24, 20, 16):
            try:
                font = ImageFont.truetype(name, size)
                break
            except OSError:
                continue
        if font is not None:
            break
    if font is None:
        font = ImageFont.load_default()

    paint_text = text.replace("0", "Ø") if slash_zeros else text

    bbox = draw.textbbox((0, 0), paint_text, font=font)
    text_h = bbox[3] - bbox[1]
    x = 6
    y = max(0, (height - text_h) // 2 - bbox[1])
    draw.text((x, y), paint_text, fill=255, font=font)
    image = image.filter(ImageFilter.MaxFilter(3))

    content = image.getbbox()
    if content is not None:
        left = max(0, content[0] - 2)
        right = min(width, content[2] + 6)
        image = image.crop((left, 0, right, height))

    if negative:
        # Invert glyph region only — empty margins must stay silent (0).
        image = Image.eval(image, lambda p: 255 - p)

    if image.size[0] < min_columns:
        # Always pad with silence (0), never with inverted "full band" energy.
        padded = Image.new("L", (min_columns, height), color=0)
        ox = (min_columns - image.size[0]) // 2
        padded.paste(image, (ox, 0))
        image = padded

    return image
