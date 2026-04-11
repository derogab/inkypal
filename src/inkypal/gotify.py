"""Gotify message forwarding."""

from __future__ import annotations

import urllib.parse
import urllib.request
from typing import TYPE_CHECKING

from inkypal import __version__ as _version

if TYPE_CHECKING:
    from inkypal.config import GotifyConfig

_TIMEOUT_SECONDS = 10


def send_message(message: str, config: GotifyConfig) -> None:
    """Forward *message* to Gotify, ignoring any delivery error."""
    if not message:
        return

    url = f"{config.base_url}/message?{urllib.parse.urlencode({'token': config.token})}"
    body = urllib.parse.urlencode({"message": message}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": f"InkyPal/{_version}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS):
            return
    except Exception:
        return
