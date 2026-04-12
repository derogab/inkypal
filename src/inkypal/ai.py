"""Optional AI message transformation via OpenAI-compatible API."""

from __future__ import annotations

import json
import logging
import re
import urllib.request
from dataclasses import dataclass
from typing import TYPE_CHECKING

from inkypal import __version__ as _version
from inkypal.render import ellipsize_text, message_character_capacity

if TYPE_CHECKING:
    from inkypal.config import AIConfig

_AI_RESPONSE_CHAR_MARGIN = 8
AI_RESPONSE_MAX_CHARS = max(1, message_character_capacity() - _AI_RESPONSE_CHAR_MARGIN)

AI_FACE_MOODS: dict[str, str] = {
    "alert": "surprised or alarming",
    "angry": "frustrated or upset",
    "cool": "impressive or chill",
    "curious": "intrigued or wondering",
    "excited": "enthusiastic or great news",
    "happy": "friendly, positive, or neutral",
    "love": "heartwarming or affectionate",
    "sad": "disappointing or bad news",
    "sleepy": "tired, calm, or bored",
}

_FACE_LIST_TEXT = "\n".join(
    f"- {name}: {desc}" for name, desc in AI_FACE_MOODS.items()
)

SYSTEM_PROMPT = (
    "You are InkyPal, a tiny friendly companion bot living on a small e-ink "
    "display. Your owner sends you information and your job is to digest it "
    "and reply with a single short friendly sentence that informs your owner "
    "about the content, as if you are their little buddy telling them what "
    "is going on.\n\n"
    "Rules:\n"
    f"- Maximum {AI_RESPONSE_MAX_CHARS} characters for the message text.\n"
    "- Write exactly ONE short sentence — no line breaks.\n"
    "- Sound warm, cheerful, and concise — like a helpful little pal.\n"
    "- Do NOT use emoji.\n"
    "- Do NOT add quotes around your answer.\n"
    "- Do NOT repeat the raw input — rephrase it naturally.\n"
    "- If the input is unclear, do your best guess to summarise it.\n\n"
    "Pick a face expression that matches your message:\n"
    f"{_FACE_LIST_TEXT}\n\n"
    "Format: [face] message\n"
    "Example: [excited] Great weather today!\n"
)

_log = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 30
_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
_FACE_TAG_RE = re.compile(r"^\[(\w+)\]\s*(.*)", re.DOTALL)


@dataclass
class AIResponse:
    """Result of an AI message transformation."""

    message: str
    face: str | None = None


def _parse_ai_response(raw: str) -> AIResponse:
    """Extract face tag and message from AI output."""
    match = _FACE_TAG_RE.match(raw)
    if match:
        face_name = match.group(1).lower()
        message = match.group(2).strip()
        if face_name in AI_FACE_MOODS and message:
            return AIResponse(message=message, face=face_name)
    return AIResponse(message=raw)


def transform_message(content: str, config: AIConfig) -> AIResponse:
    """Transform *content* into a friendly display message using AI.

    Returns an `AIResponse` with the transformed message and an optional
    face suggestion.  Falls back to the original *content* on any error
    so the display always shows something.
    """
    if not content:
        return AIResponse(message=content)

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
        "User-Agent": f"InkyPal/{_version}",
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
        text = data["choices"][0]["message"]["content"]
        text = _THINK_BLOCK_RE.sub("", text).strip().strip('"')
        result = _parse_ai_response(text)
        result.message = ellipsize_text(
            " ".join(result.message.split()), AI_RESPONSE_MAX_CHARS
        )
        if result.message:
            return result
        return AIResponse(message=content)
    except Exception as exc:
        _log.warning("AI request failed: %s", exc)
        return AIResponse(message=content)
