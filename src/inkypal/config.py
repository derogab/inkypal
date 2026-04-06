"""Runtime configuration helpers."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

IDLE_ANIMATION_SECONDS = 10
DISPLAY_OVERRIDE_SECONDS = 60

DEFAULT_AI_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_AI_MODEL = "auto"


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


@dataclass(frozen=True)
class AIConfig:
    base_url: str
    api_key: str
    model: str


def get_ai_config(env: Mapping[str, str] | None = None) -> AIConfig | None:
    """Read optional AI configuration from the environment.

    Returns ``None`` when ``OPENAI_API_KEY`` is not set, which keeps
    the current pass-through behaviour.
    """
    if env is None:
        env = os.environ

    api_key = env.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None

    base_url = env.get("OPENAI_BASE_URL", "").strip() or DEFAULT_AI_BASE_URL
    model = env.get("OPENAI_MODEL", "").strip() or DEFAULT_AI_MODEL

    return AIConfig(base_url=base_url.rstrip("/"), api_key=api_key, model=model)
