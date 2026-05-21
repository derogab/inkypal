"""Very small HTTP API for updating the display."""

from __future__ import annotations

import hmac
import json
import logging
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from inkypal import mcp
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
    {
        "method": "POST",
        "path": "/mcp",
        "description": "MCP endpoint",
    },
]


_log = logging.getLogger(__name__)

_MCP_ALLOWED_METHODS = "GET, POST, OPTIONS"
_MCP_DEFAULT_ALLOWED_HEADERS = (
    "Authorization, Content-Type, Accept, MCP-Protocol-Version, Mcp-Session-Id"
)
_MCP_PREFLIGHT_MAX_AGE = "86400"


def make_server(
    controller,
    host: str = "0.0.0.0",
    port: int = 0,
    ai_config: AIConfig | None = None,
    api_key: str | None = None,
) -> ThreadingHTTPServer:
    """Create an API server bound to a random port by default."""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if not self._authorized():
                return

            if self.path == "/mcp":
                if not self._valid_mcp_origin():
                    self._send_mcp_response(mcp.invalid_origin_response())
                    return
                extra_headers = {"Allow": "POST", **self._mcp_cors_headers()}
                self._send_empty(
                    HTTPStatus.METHOD_NOT_ALLOWED,
                    extra_headers=extra_headers,
                )
                return

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

        def do_OPTIONS(self) -> None:  # noqa: N802
            if self.path != "/mcp":
                self._send_empty(HTTPStatus.METHOD_NOT_ALLOWED)
                return

            if not self._valid_mcp_origin():
                self._send_mcp_response(mcp.invalid_origin_response())
                return

            origin = self.headers.get("Origin")
            if not origin:
                self._send_empty(
                    HTTPStatus.NO_CONTENT,
                    extra_headers={"Allow": _MCP_ALLOWED_METHODS},
                )
                return

            request_headers = self.headers.get(
                "Access-Control-Request-Headers",
                _MCP_DEFAULT_ALLOWED_HEADERS,
            )
            self._send_empty(
                HTTPStatus.NO_CONTENT,
                extra_headers={
                    "Access-Control-Allow-Origin": origin,
                    "Access-Control-Allow-Methods": _MCP_ALLOWED_METHODS,
                    "Access-Control-Allow-Headers": request_headers,
                    "Access-Control-Max-Age": _MCP_PREFLIGHT_MAX_AGE,
                    "Vary": "Origin, Access-Control-Request-Headers",
                },
            )

        def do_POST(self) -> None:  # noqa: N802
            if not self._authorized():
                return

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

            if self.path == "/mcp":
                self._handle_mcp()
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
            bypass_ai = payload.get("bypass_ai") is True

            # Discard unknown user face so the AI can choose instead
            if face is not None:
                try:
                    resolve_face(face)
                except ValueError:
                    face = None

            if face is None and content is None:
                self._send_json(HTTPStatus.OK, controller.status_payload())
                return

            original_content = content
            if content and ai_config is not None and not bypass_ai:
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

            controller.update(face=face, message=content, notification_message=original_content)
            self._send_json(HTTPStatus.OK, controller.status_payload())

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            _log.debug(format, *args)

        def _authorized(self) -> bool:
            if api_key is None:
                return True

            header = self.headers.get("Authorization", "")
            scheme, _, token = header.partition(" ")
            if scheme.lower() != "bearer" or not hmac.compare_digest(token, api_key):
                self._send_json(
                    HTTPStatus.UNAUTHORIZED,
                    {"error": "unauthorized"},
                    extra_headers={"WWW-Authenticate": 'Bearer realm="inkypal"'},
                )
                return False
            return True

        def _read_json(self) -> dict | None:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                return {}
            try:
                raw = self.rfile.read(length)
                return json.loads(raw.decode("utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                return None

        def _handle_mcp(self) -> None:
            if not self._valid_mcp_origin():
                self._send_mcp_response(mcp.invalid_origin_response())
                return

            payload = self._read_json()
            if payload is None:
                self._send_mcp_response(mcp.parse_error_response())
                return

            self._send_mcp_response(
                mcp.handle_request(
                    payload,
                    controller=controller,
                    protocol_version=self.headers.get("MCP-Protocol-Version"),
                )
            )

        def _valid_mcp_origin(self) -> bool:
            origin = self.headers.get("Origin")
            if not origin:
                return True

            parsed = urlparse(origin)
            origin_host = parsed.hostname
            if origin_host is None:
                return False

            allowed_hosts = {controller.state.host, "localhost", "127.0.0.1", "::1"}
            return origin_host.lower() in {host.lower() for host in allowed_hosts}

        def _mcp_cors_headers(self) -> dict[str, str]:
            origin = self.headers.get("Origin")
            if not origin or not self._valid_mcp_origin():
                return {}
            return {
                "Access-Control-Allow-Origin": origin,
                "Vary": "Origin",
            }

        def _send_json(
            self,
            status: HTTPStatus,
            payload: dict,
            extra_headers: dict[str, str] | None = None,
        ) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            for name, value in (extra_headers or {}).items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(body)

        def _send_mcp_response(self, response: mcp.MCPResponse) -> None:
            headers = {**response.headers, **self._mcp_cors_headers()}
            if response.payload is None:
                self._send_empty(response.status, extra_headers=headers)
                return
            self._send_json(
                response.status,
                response.payload,
                extra_headers=headers,
            )

        def _send_empty(
            self,
            status: HTTPStatus,
            extra_headers: dict[str, str] | None = None,
        ) -> None:
            self.send_response(status)
            self.send_header("Content-Length", "0")
            for name, value in (extra_headers or {}).items():
                self.send_header(name, value)
            self.end_headers()

    return ThreadingHTTPServer((host, port), Handler)
