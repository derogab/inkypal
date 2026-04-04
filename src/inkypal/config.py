"""Runtime configuration helpers."""

from __future__ import annotations

import os
from collections.abc import Mapping

IDLE_ANIMATION_SECONDS = 10
DISPLAY_OVERRIDE_SECONDS = 60


def parse_port(value: str | None) -> int:
    """Parse an optional port value.

    Returns `0` when unset so the OS can choose a random free port.
    """
    if not value:
        return 0

    try:
        port = int(value)
    except ValueError as error:
        raise ValueError("INKYPAL_PORT must be an integer") from error

    if not (1 <= port <= 65535):
        raise ValueError("INKYPAL_PORT must be between 1 and 65535")

    return port


def get_configured_port(env: Mapping[str, str] | None = None) -> int:
    """Read the configured API port from the environment."""
    if env is None:
        env = os.environ
    return parse_port(env.get("INKYPAL_PORT"))
