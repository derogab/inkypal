# Agent Guidelines

## Scope

This file is for AI agent guidance only.
Do not duplicate user-facing documentation from `README.md`.

## Project guidance

- Keep the project minimal.
- Prefer stable behavior over clever abstractions.
- Avoid adding frameworks, background services, or extra infrastructure unless explicitly requested.
- Preserve compatibility with the supported hardware setup described in `README.md`.

## Editing guidance

- Prefer small, targeted changes.
- Avoid writing code comments unless they clarify non-obvious behavior.
- Avoid adding documentation that describes internal code structure unless it is needed for maintenance.
- When behavior changes, update `README.md` if the change affects users.
- When display rendering changes (faces, layout, fonts, footer, or message formatting), use the `generate-display-image` skill to regenerate `.github/assets/display.png`.


## Verification

- Syntax check: `python3 -m compileall src/inkypal tests`
- Tests: `PYTHONPATH=src python3 -m unittest discover -s tests`
- Agents MUST run the test suite after every code change.
- When behavior changes, agents MUST update or add tests as needed.

## Runtime model

- Treat `systemd` service startup plus the HTTP API as the normal runtime model.
- Do not add new runtime CLI flags unless explicitly requested.

## Notes for agents

- Treat the e-paper display as slow hardware: avoid unnecessary full refreshes.
- Prefer behavior that keeps the display responsive for later updates while the app is running.
- If display behavior changes, verify against the upstream display references documented in `README.md` before changing the local driver.
