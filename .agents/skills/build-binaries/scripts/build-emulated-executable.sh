#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  printf 'Usage: build-emulated-executable.sh <platform> <artifact_name>\n' >&2
  exit 1
fi

platform="$1"
artifact_name="$2"

has_command() {
  command -v "$1" >/dev/null 2>&1
}

container_arch() {
  case "$platform" in
    linux/arm64)
      printf 'arm64\n'
      ;;
    linux/amd64)
      printf 'amd64\n'
      ;;
    *)
      return 1
      ;;
  esac
}

build_with_container() {
  local arch
  arch="$(container_arch)"

  printf 'Using Apple Container for %s.\n' "$platform"
  container system start >/dev/null 2>&1 || true

  mkdir -p dist
  container run --rm --arch "$arch" \
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
      cp dist/inkypal /work/dist/'"$artifact_name"'
    '
}

build_with_docker_like() {
  local runtime="$1"

  printf 'Using %s for %s.\n' "$runtime" "$platform"

  mkdir -p dist
  "$runtime" run --rm --platform "$platform" \
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
      cp dist/inkypal /work/dist/'"$artifact_name"'
    '
}

if has_command container && container_arch >/dev/null 2>&1; then
  build_with_container
  exit 0
fi

if has_command docker; then
  build_with_docker_like docker
  exit 0
fi

if has_command podman; then
  build_with_docker_like podman
  exit 0
fi

if has_command container; then
  printf 'Apple Container is available but does not support %s. Use Docker or Podman for this target.\n' "$platform" >&2
  exit 1
fi

printf 'No supported container runtime is available. Check container, docker, then podman.\n' >&2
exit 1
