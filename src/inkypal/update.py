"""GitHub release update checker."""

from __future__ import annotations

import json
import re
import urllib.request

from inkypal import __version__

_GITHUB_API_URL = "https://api.github.com/repos/derogab/inkypal/releases/latest"
_TIMEOUT_SECONDS = 10


def _parse_version(tag: str) -> tuple[int, ...]:
    """Parse a version string like ``v0.2.0`` into a comparable tuple."""
    match = re.match(r"v?(\d+(?:\.\d+)*)", tag)
    if not match:
        return ()
    return tuple(int(x) for x in match.group(1).split("."))


def check_update_available(current_version: str = __version__) -> bool:
    """Return *True* when a newer release exists on GitHub.

    Silently returns *False* on any network or parsing error so the
    caller never needs to handle exceptions.
    """
    try:
        request = urllib.request.Request(
            _GITHUB_API_URL,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "inkypal",
            },
            method="GET",
        )
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
        tag = data.get("tag_name", "")
        if not tag:
            return False
        return _parse_version(tag) > _parse_version(current_version)
    except Exception:
        return False
