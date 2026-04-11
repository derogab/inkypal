---
name: build-binaries
description: Build Linux executables using PyInstaller inside a container. Use when the user asks to build binaries or executables.
compatibility: Prefers Apple Container, then Docker, then Podman. Requires a container runtime for cross-platform Linux builds.
---

Use this skill when the user asks to build InkyPal binaries locally.

## Goal

Build Linux executables with PyInstaller, producing the same artifacts as the CI release workflow:

| Platform            | Arch       | Output file                    |
|---------------------|------------|--------------------------------|
| `linux/arm64`       | `aarch64`  | `dist/inkypal-linux-aarch64`   |
| `linux/amd64`       | `x86_64`   | `dist/inkypal-linux-x86_64`    |
| `linux/arm/v7`      | `armv7`    | `dist/inkypal-linux-armv7`     |

All outputs go into the `dist/` directory (already gitignored).

## Target selection

By default, build all three platforms. If only the host-native platform is desired, build just that one.

## Runtime selection

Pick the first available option in this exact order:

1. Apple Container: `container`
2. Docker: `docker`
3. Podman: `podman`

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

## Build command

The PyInstaller command is the same across all runtimes and all platforms. Only the container invocation and the platform/arch flag differ.

The build runs inside a `debian:trixie` container that installs the required system and Python dependencies, then invokes PyInstaller:

```bash
python3 -m PyInstaller \
  --clean \
  --onefile \
  --name inkypal \
  --paths src \
  --collect-submodules gpiozero.pins \
  --collect-data jaraco.text \
  --hidden-import lgpio \
  src/inkypal/__main__.py
```

The resulting binary is copied from the container's `dist/inkypal` to the host at `dist/<artifact_name>`.

### Apple Container

Apple Container uses `--arch` instead of `--platform`. Supported values are at least `arm64` and `amd64` (via Rosetta on Apple Silicon). Building `arm/v7` is not supported.

For `linux/arm64`:

```bash
mkdir -p dist
container run --rm --arch arm64 \
  -v "$PWD:/work" -w /work \
  debian:trixie bash -lc '
    apt-get update &&
    apt-get install -y ca-certificates &&
    echo "deb [trusted=yes] https://archive.raspberrypi.com/debian trixie main" > /etc/apt/sources.list.d/raspi.list &&
    apt-get update &&
    apt-get install -y \
      gcc \
      python3 \
      python3-pyinstaller \
      python3-pil \
      python3-gpiozero \
      python3-spidev \
      python3-lgpio &&
    python3 -m PyInstaller \
      --clean \
      --onefile \
      --name inkypal \
      --paths src \
      --collect-submodules gpiozero.pins \
      --collect-data jaraco.text \
      --hidden-import lgpio \
      src/inkypal/__main__.py &&
    cp dist/inkypal /work/dist/inkypal-linux-aarch64
  '
```

For `linux/amd64`:

```bash
mkdir -p dist
container run --rm --arch amd64 \
  -v "$PWD:/work" -w /work \
  debian:trixie bash -lc '
    apt-get update &&
    apt-get install -y ca-certificates &&
    echo "deb [trusted=yes] https://archive.raspberrypi.com/debian trixie main" > /etc/apt/sources.list.d/raspi.list &&
    apt-get update &&
    apt-get install -y \
      gcc \
      python3 \
      python3-pyinstaller \
      python3-pil \
      python3-gpiozero \
      python3-spidev \
      python3-lgpio &&
    python3 -m PyInstaller \
      --clean \
      --onefile \
      --name inkypal \
      --paths src \
      --collect-submodules gpiozero.pins \
      --collect-data jaraco.text \
      --hidden-import lgpio \
      src/inkypal/__main__.py &&
    cp dist/inkypal /work/dist/inkypal-linux-x86_64
  '
```

### Docker

Docker uses `--platform` and requires QEMU for cross-architecture builds via `docker/setup-qemu-action` or manual QEMU setup.

For any platform (`linux/amd64`, `linux/arm64`, `linux/arm/v7`):

```bash
mkdir -p dist
docker run --rm --platform <PLATFORM> \
  -v "$PWD:/work" -w /work \
  debian:trixie bash -lc '
    apt-get update &&
    apt-get install -y ca-certificates &&
    echo "deb [trusted=yes] https://archive.raspberrypi.com/debian trixie main" > /etc/apt/sources.list.d/raspi.list &&
    apt-get update &&
    apt-get install -y \
      gcc \
      python3 \
      python3-pyinstaller \
      python3-pil \
      python3-gpiozero \
      python3-spidev \
      python3-lgpio &&
    python3 -m PyInstaller \
      --clean \
      --onefile \
      --name inkypal \
      --paths src \
      --collect-submodules gpiozero.pins \
      --collect-data jaraco.text \
      --hidden-import lgpio \
      src/inkypal/__main__.py &&
    cp dist/inkypal /work/dist/<ARTIFACT_NAME>
  '
```

Map platform to artifact name:

| `--platform` value  | `<ARTIFACT_NAME>`           |
|---------------------|-----------------------------|
| `linux/amd64`       | `inkypal-linux-x86_64`      |
| `linux/arm64`       | `inkypal-linux-aarch64`     |
| `linux/arm/v7`      | `inkypal-linux-armv7`       |

Before running Docker cross-arch builds, ensure QEMU is registered:

```bash
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
```

### Podman

Identical to Docker but replace `docker` with `podman`. Podman also needs QEMU for cross-architecture builds.

## Verification

After building:

1. Confirm each expected file exists in `dist/`.
2. Check file sizes are reasonable (several MB for a PyInstaller onefile binary).
3. If on Linux, test the native binary: `./dist/inkypal-linux-<arch> --help`.