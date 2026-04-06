"""Image rendering helpers."""

from __future__ import annotations

import math
from pathlib import Path
import textwrap

from PIL import Image, ImageDraw, ImageFont

from inkypal import __version__

DISPLAY_IMAGE_SIZE = (250, 122)
DEFAULT_MESSAGE = ""
DEFAULT_ROTATION = 180
FACE_SCALE = 3
FACE_FONT_SIZE = 8
FACE_Y = 8
MESSAGE_AREA_TOP = 38
MESSAGE_AREA_BOTTOM = 106
MESSAGE_MAX_LINES = 4
MESSAGE_HORIZONTAL_MARGIN = 8
FOOTER_Y = 112
MESSAGE_FONT_SIZES = (18, 16, 14, 12)

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
]


def load_font(
    size: int,
    candidates: list[str] | tuple[str, ...] = FONT_CANDIDATES,
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a readable monospace font, with a safe fallback."""
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default(size=size)


def render_face_image(
    face_text: str,
    message: str,
    host: str,
    port: int,
    rotation: int = DEFAULT_ROTATION,
    update_available: bool = False,
) -> Image.Image:
    """Render a white image with black text for the e-paper display."""
    image = Image.new("1", DISPLAY_IMAGE_SIZE, 255)
    draw = ImageDraw.Draw(image)

    face_font = load_font(FACE_FONT_SIZE)
    small_font = load_font(10)

    draw_scaled_centered(image, face_text, face_font, y=FACE_Y, scale=FACE_SCALE)
    if message:
        draw_message_centered(
            image,
            message,
            top=MESSAGE_AREA_TOP,
            bottom=MESSAGE_AREA_BOTTOM,
            max_width=DISPLAY_IMAGE_SIZE[0] - (MESSAGE_HORIZONTAL_MARGIN * 2),
            max_lines=MESSAGE_MAX_LINES,
        )

    version_text = f"v{__version__}"
    draw_bottom_left(draw, f"{host}:{port}", small_font, y=FOOTER_Y)
    draw_bottom_right(draw, version_text, small_font, y=FOOTER_Y)
    if update_available:
        _draw_update_dot(draw, version_text, small_font, y=FOOTER_Y)

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


def draw_message_centered(
    image: Image.Image,
    text: str,
    top: int,
    bottom: int,
    max_width: int,
    max_lines: int,
    line_spacing: int = 0,
) -> None:
    """Draw wrapped message text inside a fixed vertical area."""
    draw = ImageDraw.Draw(image)
    wrapped, font = fit_message_to_area(
        text,
        draw,
        max_width=max_width,
        max_height=bottom - top,
        max_lines=max_lines,
        line_spacing=line_spacing,
    )
    left, text_top, right, text_bottom = draw.multiline_textbbox(
        (0, 0), wrapped, font=font, spacing=line_spacing, align="center"
    )
    width = max(1, math.ceil(right - left))
    height = max(1, math.ceil(text_bottom - text_top))
    mask = Image.new("1", (width, height), 255)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.multiline_text(
        (-left, -text_top),
        wrapped,
        font=font,
        fill=0,
        spacing=line_spacing,
        align="center",
    )
    x = int((DISPLAY_IMAGE_SIZE[0] - width) // 2)
    y = int(top + max(0, ((bottom - top) - height) // 2))
    image.paste(mask, (x, y))


def fit_message_to_area(
    text: str,
    draw: ImageDraw.ImageDraw,
    max_width: int,
    max_height: int,
    max_lines: int,
    line_spacing: int = 0,
) -> tuple[str, ImageFont.FreeTypeFont | ImageFont.ImageFont]:
    """Choose the largest message font that fits the available area."""
    fallback_font = load_font(MESSAGE_FONT_SIZES[-1])
    fallback_wrapped = wrap_message(
        text,
        draw,
        fallback_font,
        max_width=max_width,
        max_lines=max_lines,
        scale=1,
    )

    for size in MESSAGE_FONT_SIZES:
        font = load_font(size)
        lines = wrap_message_lines(text, draw, font, max_width=max_width, scale=1)
        if len(lines) > max_lines:
            continue

        candidate = "\n".join(lines)
        left, text_top, right, text_bottom = draw.multiline_textbbox(
            (0, 0), candidate, font=font, spacing=line_spacing, align="center"
        )
        width = max(1, math.ceil(right - left))
        height = max(1, math.ceil(text_bottom - text_top))
        if width <= max_width and height <= max_height:
            return candidate, font

    return fallback_wrapped, fallback_font


def message_character_capacity() -> int:
    """Estimate total fallback characters available in the message area."""
    image = Image.new("1", DISPLAY_IMAGE_SIZE, 255)
    draw = ImageDraw.Draw(image)
    font = load_font(MESSAGE_FONT_SIZES[-1])
    max_width = DISPLAY_IMAGE_SIZE[0] - (MESSAGE_HORIZONTAL_MARGIN * 2)
    return message_max_chars(draw, font, max_width=max_width, scale=1) * MESSAGE_MAX_LINES


def wrap_message_lines(
    text: str,
    draw: ImageDraw.ImageDraw,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
    scale: int,
) -> list[str]:
    """Wrap text using a monospace width estimate for the chosen font."""
    max_chars = message_max_chars(draw, font, max_width=max_width, scale=scale)
    return textwrap.wrap(
        text,
        width=max_chars,
        break_long_words=True,
        break_on_hyphens=False,
    ) or [""]


def message_max_chars(
    draw: ImageDraw.ImageDraw,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
    scale: int,
) -> int:
    """Estimate how many monospace characters fit in the available width."""
    char_left, _, char_right, _ = draw.textbbox((0, 0), "M", font=font)
    char_width = max(1, char_right - char_left)
    return max(1, max_width // (char_width * scale))


def wrap_message(
    text: str,
    draw: ImageDraw.ImageDraw,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
    max_lines: int,
    scale: int,
) -> str:
    """Wrap and clamp a message to a small number of monospace lines."""
    max_chars = message_max_chars(draw, font, max_width=max_width, scale=scale)
    lines = wrap_message_lines(text, draw, font, max_width=max_width, scale=scale)

    if len(lines) > max_lines:
        remaining = " ".join(lines[max_lines - 1 :])
        lines = lines[: max_lines - 1] + [ellipsize_text(remaining, max_chars)]

    return "\n".join(lines)


def ellipsize_text(text: str, max_chars: int) -> str:
    """Trim text to fit a fixed character width."""
    if len(text) <= max_chars:
        return text
    if max_chars <= 1:
        return text[:max_chars]
    return text[: max_chars - 1] + "…"


def _draw_update_dot(
    draw: ImageDraw.ImageDraw,
    version_text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    y: int,
    margin: int = 6,
    radius: int = 2,
) -> None:
    """Draw a small filled circle just left of the version text."""
    left, top, right, bottom = draw.textbbox((0, 0), version_text, font=font)
    text_width = right - left
    text_x = DISPLAY_IMAGE_SIZE[0] - text_width - margin
    cy = y + (bottom - top) // 2
    cx = text_x - radius - 3
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=0)


def draw_bottom_left(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    y: int,
    margin: int = 6,
) -> None:
    """Draw a single line aligned to the lower left area."""
    _, top, _, _ = draw.textbbox((0, 0), text, font=font)
    draw.text((margin, y - top), text, font=font, fill=0)


def draw_bottom_right(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    y: int,
    margin: int = 6,
) -> None:
    """Draw a single line aligned to the lower right area."""
    left, top, right, _ = draw.textbbox((0, 0), text, font=font)
    width = right - left
    x = DISPLAY_IMAGE_SIZE[0] - width - margin
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
