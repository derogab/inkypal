"""Optional AI message transformation via OpenAI-compatible API."""

from __future__ import annotations

import json
import urllib.request
from typing import TYPE_CHECKING

from inkypal.render import ellipsize_text, message_character_capacity

if TYPE_CHECKING:
    from inkypal.config import AIConfig

_AI_RESPONSE_CHAR_MARGIN = 8
AI_RESPONSE_MAX_CHARS = max(1, message_character_capacity() - _AI_RESPONSE_CHAR_MARGIN)

SYSTEM_PROMPT = (
    "You are InkyPal, a tiny friendly companion bot living on a small e-ink "
    "display. Your owner sends you information and your job is to digest it "
    "and reply with a single short friendly sentence that informs your owner "
    "about the content, as if you are their little buddy telling them what "
    "is going on.\n\n"
    "Rules:\n"
    f"- Maximum {AI_RESPONSE_MAX_CHARS} characters so it fits the display.\n"
    "- Write exactly ONE short sentence — no line breaks.\n"
    "- Sound warm, cheerful, and concise — like a helpful little pal.\n"
    "- Do NOT use emoji.\n"
    "- Do NOT add quotes around your answer.\n"
    "- Do NOT repeat the raw input — rephrase it naturally.\n"
    "- If the input is unclear, do your best guess to summarise it.\n"
)

_TIMEOUT_SECONDS = 10


def transform_message(content: str, config: AIConfig) -> str:
    """Transform *content* into a friendly display message using AI.

    Falls back to the original *content* on any error so the display
    always shows something.
    """
    if not content:
        return content

    url = f"{config.base_url}/chat/completions"
    body = json.dumps(
        {
            "model": config.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
            "temperature": 0.7,
        }
    ).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.api_key}",
    }
    headers.update(config.headers)

    request = urllib.request.Request(
        url,
        data=body,
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
        text = data["choices"][0]["message"]["content"].strip().strip('"')
        text = ellipsize_text(" ".join(text.split()), AI_RESPONSE_MAX_CHARS)
        return text if text else content
    except Exception:
        return content
