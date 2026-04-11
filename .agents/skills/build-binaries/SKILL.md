---
name: build-binaries
description: Build InkyPal Linux executables locally using the bundled helper script.
compatibility: Requires container, docker, or podman. The helper script prefers Apple Container, then Docker, then Podman.
---

Use this skill when the user asks to build InkyPal Linux executables locally.

## Rule

Always use `.agents/skills/build-binaries/scripts/build-emulated-executable.sh`.
Do not inline the container commands from this skill.

## Goal

Produce these Linux binary artifacts in `dist/`:

| Platform        | Arch      | Output file                  |
|-----------------|-----------|------------------------------|
| `linux/arm64`   | `aarch64` | `dist/inkypal-linux-aarch64` |
| `linux/amd64`   | `x86_64`  | `dist/inkypal-linux-x86_64`  |

## Default build

Build both targets by default. If the user explicitly asks for only one target, build just that one.

Run these commands from the repository root:

```bash
bash .agents/skills/build-binaries/scripts/build-emulated-executable.sh linux/arm64 inkypal-linux-aarch64
bash .agents/skills/build-binaries/scripts/build-emulated-executable.sh linux/amd64 inkypal-linux-x86_64
```

## Helper behavior

The helper script:

1. Picks the first supported runtime in this order: `container`, `docker`, `podman`.
2. Starts Apple Container automatically when needed.
3. Copies the finished executable into `dist/<artifact_name>`.

## Verification

After building:

1. Confirm `dist/inkypal-linux-aarch64` exists.
2. Confirm `dist/inkypal-linux-x86_64` exists.
3. Check both file sizes are reasonable for PyInstaller onefile binaries.
