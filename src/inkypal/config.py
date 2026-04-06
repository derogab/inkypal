"""Runtime configuration helpers."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from urllib.parse import urlparse

IDLE_ANIMATION_SECONDS = 10
DISPLAY_OVERRIDE_SECONDS = 60

DEFAULT_AI_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_AI_MODEL = "auto"
DEFAULT_OPENROUTER_REFERER = "https://github.com/derogab/inkypal"
DEFAULT_OPENROUTER_TITLE = "InkyPal AI"


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
    headers: Mapping[str, str] = field(default_factory=dict)


def is_openrouter_base_url(base_url: str) -> bool:
    """Return ``True`` when *base_url* points to OpenRouter."""
    return (urlparse(base_url).hostname or "").lower() == "openrouter.ai"


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
    headers: dict[str, str] = {}

    if is_openrouter_base_url(base_url):
        headers["HTTP-Referer"] = (
            env.get("OPENAI_OPENROUTER_REFERER", "").strip()
            or DEFAULT_OPENROUTER_REFERER
        )
        headers["X-OpenRouter-Title"] = (
            env.get("OPENAI_OPENROUTER_TITLE", "").strip()
            or DEFAULT_OPENROUTER_TITLE
        )

        categories = env.get("OPENAI_OPENROUTER_CATEGORIES", "").strip()
        if categories:
            headers["X-OpenRouter-Categories"] = categories

    return AIConfig(
        base_url=base_url.rstrip("/"),
        api_key=api_key,
        model=model,
        headers=headers,
    )
