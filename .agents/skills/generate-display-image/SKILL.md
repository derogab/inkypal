---
name: generate-display-image
description: Generate the README preview image at .github/assets/display.png after display rendering changes. Use when faces, layout, fonts, footer content, or message formatting changes and a fresh preview image is needed.
compatibility: Prefers Apple Container, then Docker, then Podman. Falls back to the local Python environment only when no supported container runtime is available.
---

Use this skill when the rendered e-paper preview in `.github/assets/display.png` needs to be refreshed.

## Goal

Create `.github/assets/display.png` from the current renderer with the canonical preview content:

- Rotation: `0`
- Face: `happy`
- Message: `Hello world!`
- Host: `192.168.1.2`
- Port: `8080`
- Version text: `v0.0.0`
- Final output scale: `3x` nearest-neighbor

Render the image manually. Do not call `render_face_image`, because the preview must pin the footer version text to `v0.0.0` instead of the package version.

## Runtime selection

Pick the first available option in this exact order:

1. Apple Container: `container`
2. Docker: `docker`
3. Podman: `podman`
4. Local Python environment

Checks:

```bash
command -v container
command -v docker
command -v podman
```

If `container` is installed but not running yet, start it before retrying:

```bash
container system start
```

## Container workflow

Use the same Python script body for Apple Container, Docker, and Podman. Install the Python and system dependencies required to run the real repository renderer inside the container. In the current repo that means `Pillow` plus `fonts-dejavu-core`, so the preview uses the same drawing code and the same preferred Linux monospace font path as the e-ink runtime.

### Apple Container

```bash
container run --rm --volume "$PWD:/app" --workdir /app docker.io/python:3.12-slim bash -lc '
  apt-get update >/dev/null &&
  apt-get install -y --no-install-recommends fonts-dejavu-core >/dev/null &&
  pip install -q Pillow &&
  PYTHONPATH=src python3 - <<"PY"
from PIL import Image, ImageDraw

from inkypal.faces import resolve_face
from inkypal.render import (
    DISPLAY_IMAGE_SIZE,
    FACE_FONT_SIZE,
    FACE_SCALE,
    FACE_Y,
    FOOTER_Y,
    MESSAGE_AREA_BOTTOM,
    MESSAGE_MAX_LINES,
    MESSAGE_AREA_TOP,
    MESSAGE_HORIZONTAL_MARGIN,
    draw_bottom_left,
    draw_bottom_right,
    draw_message_centered,
    draw_scaled_centered,
    load_font,
)

image = Image.new("1", DISPLAY_IMAGE_SIZE, 255)
draw = ImageDraw.Draw(image)
_, face_text = resolve_face("happy")

draw_scaled_centered(image, face_text, load_font(FACE_FONT_SIZE), y=FACE_Y, scale=FACE_SCALE)
draw_message_centered(
    image,
    "Hello world!",
    top=MESSAGE_AREA_TOP,
    bottom=MESSAGE_AREA_BOTTOM,
    max_width=DISPLAY_IMAGE_SIZE[0] - (MESSAGE_HORIZONTAL_MARGIN * 2),
    max_lines=MESSAGE_MAX_LINES,
)
footer_font = load_font(10)
draw_bottom_left(draw, "192.168.1.2:8080", footer_font, y=FOOTER_Y)
draw_bottom_right(draw, "v0.0.0", footer_font, y=FOOTER_Y)

scaled = image.resize((image.width * 3, image.height * 3), Image.Resampling.NEAREST)
scaled.save(".github/assets/display.png")
PY'
```

### Docker

```bash
docker run --rm -v "$PWD:/app" -w /app python:3.12-slim bash -lc '
  apt-get update >/dev/null &&
  apt-get install -y --no-install-recommends fonts-dejavu-core >/dev/null &&
  pip install -q Pillow &&
  PYTHONPATH=src python3 - <<"PY"
from PIL import Image, ImageDraw

from inkypal.faces import resolve_face
from inkypal.render import (
    DISPLAY_IMAGE_SIZE,
    FACE_FONT_SIZE,
    FACE_SCALE,
    FACE_Y,
    FOOTER_Y,
    MESSAGE_AREA_BOTTOM,
    MESSAGE_MAX_LINES,
    MESSAGE_AREA_TOP,
    MESSAGE_HORIZONTAL_MARGIN,
    draw_bottom_left,
    draw_bottom_right,
    draw_message_centered,
    draw_scaled_centered,
    load_font,
)

image = Image.new("1", DISPLAY_IMAGE_SIZE, 255)
draw = ImageDraw.Draw(image)
_, face_text = resolve_face("happy")

draw_scaled_centered(image, face_text, load_font(FACE_FONT_SIZE), y=FACE_Y, scale=FACE_SCALE)
draw_message_centered(
    image,
    "Hello world!",
    top=MESSAGE_AREA_TOP,
    bottom=MESSAGE_AREA_BOTTOM,
    max_width=DISPLAY_IMAGE_SIZE[0] - (MESSAGE_HORIZONTAL_MARGIN * 2),
    max_lines=MESSAGE_MAX_LINES,
)
footer_font = load_font(10)
draw_bottom_left(draw, "192.168.1.2:8080", footer_font, y=FOOTER_Y)
draw_bottom_right(draw, "v0.0.0", footer_font, y=FOOTER_Y)

scaled = image.resize((image.width * 3, image.height * 3), Image.Resampling.NEAREST)
scaled.save(".github/assets/display.png")
PY'
```

### Podman

```bash
podman run --rm -v "$PWD:/app" -w /app docker.io/python:3.12-slim bash -lc '
  apt-get update >/dev/null &&
  apt-get install -y --no-install-recommends fonts-dejavu-core >/dev/null &&
  pip install -q Pillow &&
  PYTHONPATH=src python3 - <<"PY"
from PIL import Image, ImageDraw

from inkypal.faces import resolve_face
from inkypal.render import (
    DISPLAY_IMAGE_SIZE,
    FACE_FONT_SIZE,
    FACE_SCALE,
    FACE_Y,
    FOOTER_Y,
    MESSAGE_AREA_BOTTOM,
    MESSAGE_MAX_LINES,
    MESSAGE_AREA_TOP,
    MESSAGE_HORIZONTAL_MARGIN,
    draw_bottom_left,
    draw_bottom_right,
    draw_message_centered,
    draw_scaled_centered,
    load_font,
)

image = Image.new("1", DISPLAY_IMAGE_SIZE, 255)
draw = ImageDraw.Draw(image)
_, face_text = resolve_face("happy")

draw_scaled_centered(image, face_text, load_font(FACE_FONT_SIZE), y=FACE_Y, scale=FACE_SCALE)
draw_message_centered(
    image,
    "Hello world!",
    top=MESSAGE_AREA_TOP,
    bottom=MESSAGE_AREA_BOTTOM,
    max_width=DISPLAY_IMAGE_SIZE[0] - (MESSAGE_HORIZONTAL_MARGIN * 2),
    max_lines=MESSAGE_MAX_LINES,
)
footer_font = load_font(10)
draw_bottom_left(draw, "192.168.1.2:8080", footer_font, y=FOOTER_Y)
draw_bottom_right(draw, "v0.0.0", footer_font, y=FOOTER_Y)

scaled = image.resize((image.width * 3, image.height * 3), Image.Resampling.NEAREST)
scaled.save(".github/assets/display.png")
PY'
```

## Local Python fallback

Use this only when `container`, `docker`, and `podman` are all unavailable.

```bash
python3 -m pip install Pillow
PYTHONPATH=src python3 - <<"PY"
from PIL import Image, ImageDraw

from inkypal.faces import resolve_face
from inkypal.render import (
    DISPLAY_IMAGE_SIZE,
    FACE_FONT_SIZE,
    FACE_SCALE,
    FACE_Y,
    FOOTER_Y,
    MESSAGE_AREA_BOTTOM,
    MESSAGE_MAX_LINES,
    MESSAGE_AREA_TOP,
    MESSAGE_HORIZONTAL_MARGIN,
    draw_bottom_left,
    draw_bottom_right,
    draw_message_centered,
    draw_scaled_centered,
    load_font,
)

image = Image.new("1", DISPLAY_IMAGE_SIZE, 255)
draw = ImageDraw.Draw(image)
_, face_text = resolve_face("happy")

draw_scaled_centered(image, face_text, load_font(FACE_FONT_SIZE), y=FACE_Y, scale=FACE_SCALE)
draw_message_centered(
    image,
    "Hello world!",
    top=MESSAGE_AREA_TOP,
    bottom=MESSAGE_AREA_BOTTOM,
    max_width=DISPLAY_IMAGE_SIZE[0] - (MESSAGE_HORIZONTAL_MARGIN * 2),
    max_lines=MESSAGE_MAX_LINES,
)
footer_font = load_font(10)
draw_bottom_left(draw, "192.168.1.2:8080", footer_font, y=FOOTER_Y)
draw_bottom_right(draw, "v0.0.0", footer_font, y=FOOTER_Y)

scaled = image.resize((image.width * 3, image.height * 3), Image.Resampling.NEAREST)
scaled.save(".github/assets/display.png")
PY
```

## Verification

After generating the file:

1. Confirm `.github/assets/display.png` exists and was updated.
2. Inspect the image to verify the face, message, footer alignment, and scaling.
3. If the renderer changed in the same task, run the project verification commands after the image is regenerated.
