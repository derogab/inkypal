"""Image rendering helpers."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DISPLAY_IMAGE_SIZE = (250, 122)
DEFAULT_MESSAGE = ""
DEFAULT_ROTATION = 180
FACE_SCALE = 3

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
]


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a readable monospace font, with a safe fallback."""
    for candidate in FONT_CANDIDATES:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def render_face_image(
    face_text: str,
    message: str,
    host: str,
    port: int,
    rotation: int = DEFAULT_ROTATION,
) -> Image.Image:
    """Render a white image with black text for the e-paper display."""
    image = Image.new("1", DISPLAY_IMAGE_SIZE, 255)
    draw = ImageDraw.Draw(image)

    face_font = load_font(24)
    body_font = load_font(14)
    small_font = load_font(11)

    face_y = 18 if not message else 8
    draw_scaled_centered(image, face_text, face_font, y=face_y, scale=FACE_SCALE)
    if message:
        draw_centered(draw, message, body_font, y=74)
        draw_centered(draw, f"{host}:{port}", small_font, y=96)
    else:
        draw_centered(draw, f"{host}:{port}", small_font, y=100)

    return image.rotate(rotation)


def draw_centered(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    y: int,
) -> None:
    """Draw a single centered line of text."""
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    width = right - left
    x = (DISPLAY_IMAGE_SIZE[0] - width) // 2
    draw.text((x, y - top), text, font=font, fill=0)


def draw_scaled_centered(
    image: Image.Image,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    y: int,
    scale: int,
) -> None:
    """Draw text centered after nearest-neighbor scaling."""
    draw = ImageDraw.Draw(image)
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    width = right - left
    height = bottom - top

    mask = Image.new("1", (width, height), 255)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.text((-left, -top), text, font=font, fill=0)

    scaled = mask.resize((width * scale, height * scale), Image.Resampling.NEAREST)
    x = (DISPLAY_IMAGE_SIZE[0] - scaled.width) // 2
    image.paste(scaled, (x, y))
