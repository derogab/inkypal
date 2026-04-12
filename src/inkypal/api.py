"""Very small HTTP API for updating the display."""

from __future__ import annotations

import json
import logging
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from inkypal.config import AIConfig
from inkypal.faces import list_faces, resolve_face

ROOT_ENDPOINTS = [
    {
        "method": "GET",
        "path": "/",
        "description": "API index and runtime summary",
    },
    {
        "method": "GET",
        "path": "/health",
        "description": "Health state of the running service",
    },
    {
        "method": "GET",
        "path": "/status",
        "description": "Current companion state",
    },
    {
        "method": "GET",
        "path": "/faces",
        "description": "Available built-in face names",
    },
    {
        "method": "POST",
        "path": "/message",
        "description": "Update the displayed face and/or content",
    },
    {
        "method": "POST",
        "path": "/off",
        "description": "Clear the display to white and pause idle animation",
    },
]


_log = logging.getLogger(__name__)


def make_server(
    controller,
    host: str = "0.0.0.0",
    port: int = 0,
    ai_config: AIConfig | None = None,
) -> ThreadingHTTPServer:
    """Create an API server bound to a random port by default."""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path not in ("/", "/health", "/status", "/faces"):
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
                return

            if self.path == "/health":
                self._send_json(HTTPStatus.OK, controller.health_payload())
                return

            if self.path == "/":
                self._send_json(
                    HTTPStatus.OK,
                    {
                        "running": True,
                        "ip": controller.state.host,
                        "port": controller.state.port,
                        "endpoints": ROOT_ENDPOINTS,
                    },
                )
                return

            if self.path == "/faces":
                self._send_json(HTTPStatus.OK, {"ok": True, "faces": list_faces()})
                return

            self._send_json(HTTPStatus.OK, controller.status_payload())

        def do_POST(self) -> None:  # noqa: N802
            if self.path == "/off":
                controller.power_off()
                self._send_json(
                    HTTPStatus.OK,
                    {
                        "ok": True,
                        "off": True,
                        "ip": controller.state.host,
                        "port": controller.state.port,
                    },
                )
                return

            if self.path != "/message":
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
                return

            payload = self._read_json()
            if payload is None:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid json"})
                return

            face = payload.get("face")
            content = payload.get("content")

            # Discard unknown user face so the AI can choose instead
            if face is not None:
                try:
                    resolve_face(face)
                except ValueError:
                    face = None

            if face is None and content is None:
                self._send_json(HTTPStatus.OK, controller.status_payload())
                return

            if content and ai_config is not None:
                from inkypal.ai import transform_message

                ai_result = transform_message(content, ai_config)
                content = ai_result.message
                if face is None:
                    face = ai_result.face

            # Fall back to default face if AI returned an unknown one
            if face is not None:
                try:
                    resolve_face(face)
                except ValueError:
                    face = "happy"

            controller.update(face=face, message=content)
            self._send_json(HTTPStatus.OK, controller.status_payload())

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            _log.debug(format, *args)

        def _read_json(self) -> dict | None:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                return {}
            try:
                raw = self.rfile.read(length)
                return json.loads(raw.decode("utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                return None

        def _send_json(self, status: HTTPStatus, payload: dict) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return ThreadingHTTPServer((host, port), Handler)
