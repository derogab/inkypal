"""Networking helpers for the local API."""

from __future__ import annotations

import socket


def get_local_ip() -> str:
    """Return the most likely LAN IP address for this machine."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()
