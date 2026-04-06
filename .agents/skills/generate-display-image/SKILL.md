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

Use the exact renderer that drives the e-ink output. Only override the canonical preview inputs above.

Do not reimplement layout, wrapping, font selection, scaling masks, or footer placement in the skill. Call `render_face_image` directly and temporarily pin `inkypal.render.__version__` to `0.0.0` so the preview footer stays at `v0.0.0`.

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

Use the same Python script body for Apple Container, Docker, and Podman. Install the Python and system dependencies required to run the real repository renderer inside the container. In the current repo that means `Pillow` plus `fonts-dejavu-core`, so the preview uses the same render path and the same preferred Linux monospace font path as the e-ink runtime.

### Apple Container

```bash
container run --rm --volume "$PWD:/app" --workdir /app docker.io/python:3.12-slim bash -lc '
  apt-get update >/dev/null &&
  apt-get install -y --no-install-recommends fonts-dejavu-core >/dev/null &&
  pip install -q Pillow &&
  PYTHONPATH=src python3 - <<"PY"
from PIL import Image

import inkypal.render as render
from inkypal.faces import resolve_face

original_version = render.__version__
render.__version__ = "0.0.0"

try:
    _, face_text = resolve_face("happy")
    image = render.render_face_image(
        face_text=face_text,
        message="Hello world!",
        host="192.168.1.2",
        port=8080,
        rotation=0,
    )
finally:
    render.__version__ = original_version

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
from PIL import Image

import inkypal.render as render
from inkypal.faces import resolve_face

original_version = render.__version__
render.__version__ = "0.0.0"

try:
    _, face_text = resolve_face("happy")
    image = render.render_face_image(
        face_text=face_text,
        message="Hello world!",
        host="192.168.1.2",
        port=8080,
        rotation=0,
    )
finally:
    render.__version__ = original_version

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
from PIL import Image

import inkypal.render as render
from inkypal.faces import resolve_face

original_version = render.__version__
render.__version__ = "0.0.0"

try:
    _, face_text = resolve_face("happy")
    image = render.render_face_image(
        face_text=face_text,
        message="Hello world!",
        host="192.168.1.2",
        port=8080,
        rotation=0,
    )
finally:
    render.__version__ = original_version

scaled = image.resize((image.width * 3, image.height * 3), Image.Resampling.NEAREST)
scaled.save(".github/assets/display.png")
PY'
```

## Local Python fallback

Use this only when `container`, `docker`, and `podman` are all unavailable.

This still uses `render_face_image`, but the output can diverge if the host does not have the same preferred font available.

```bash
python3 -m pip install Pillow
PYTHONPATH=src python3 - <<"PY"
from PIL import Image

import inkypal.render as render
from inkypal.faces import resolve_face

original_version = render.__version__
render.__version__ = "0.0.0"

try:
    _, face_text = resolve_face("happy")
    image = render.render_face_image(
        face_text=face_text,
        message="Hello world!",
        host="192.168.1.2",
        port=8080,
        rotation=0,
    )
finally:
    render.__version__ = original_version

scaled = image.resize((image.width * 3, image.height * 3), Image.Resampling.NEAREST)
scaled.save(".github/assets/display.png")
PY
```

## Verification

After generating the file:

1. Confirm `.github/assets/display.png` exists and was updated.
2. Inspect the image to verify the face, message, footer alignment, and scaling.
3. If the renderer changed in the same task, run the project verification commands after the image is regenerated.
