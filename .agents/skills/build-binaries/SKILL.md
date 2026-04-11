---
name: build-binaries
description: Build Linux executables using PyInstaller inside a container. Use when the user asks to build binaries or executables.
compatibility: Prefers Apple Container, then Docker, then Podman. Requires a container runtime for cross-platform Linux builds.
---

Use this skill when the user asks to build InkyPal Linux executables locally.

## Goal

Produce these Linux binary artifacts:

| Platform        | Arch      | Output file                  |
|-----------------|-----------|------------------------------|
| `linux/arm64`   | `aarch64` | `dist/inkypal-linux-aarch64` |
| `linux/amd64`   | `x86_64`  | `dist/inkypal-linux-x86_64`  |

All outputs go in `dist/`.

## Target selection

Build both targets by default. If the user only wants the host-native Linux target, build just that one.

## Shared helper

Use `scripts/build-emulated-executable.sh` for containerized builds.

```bash
bash .agents/skills/build-binaries/scripts/build-emulated-executable.sh <platform> <artifact_name>
```

The helper checks runtimes in this order and picks the first supported option:

1. `container`
2. `docker`
3. `podman`

Artifact mapping:

| Platform        | Artifact name              |
|-----------------|----------------------------|
| `linux/amd64`   | `inkypal-linux-x86_64`     |
| `linux/arm64`   | `inkypal-linux-aarch64`    |

## Runtime selection

Check availability in this order:

```bash
command -v container
command -v docker
command -v podman
```

If `container` is installed but not running yet, start it before retrying:

```bash
container system start
```

For both supported targets, use the first available runtime in this order: `container`, then `docker`, then `podman`.

The helper follows this order automatically.

## Docker and Podman notes

The Docker and Podman build commands expect QEMU support for cross-architecture builds.

For Docker, register QEMU before cross-arch builds if it is not already available:

```bash
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
```

## Apple Container

Apple Container uses `--arch` instead of `--platform`. It can build `linux/arm64` and `linux/amd64`.

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

## Verification

After building:

1. Confirm each expected file exists in `dist/`.
2. Check file sizes are reasonable for PyInstaller onefile binaries.
3. If a native Linux target was built on Linux, smoke-test it with `./dist/inkypal-linux-<arch> --help`.
