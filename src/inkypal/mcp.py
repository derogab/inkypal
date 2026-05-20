"""Minimal MCP JSON-RPC handling."""

from __future__ import annotations

from dataclasses import dataclass, field
from http import HTTPStatus
from typing import Any

from inkypal import __version__
from inkypal.faces import list_faces

PROTOCOL_VERSION = "2025-11-25"
SUPPORTED_PROTOCOL_VERSIONS = ("2025-11-25", "2025-06-18", "2025-03-26")
TOOL_NAME = "send_message"


@dataclass(frozen=True)
class MCPResponse:
    status: HTTPStatus
    payload: dict[str, Any] | None = None
    headers: dict[str, str] = field(default_factory=dict)


def parse_error_response() -> MCPResponse:
    return error_response(HTTPStatus.BAD_REQUEST, None, -32700, "Parse error")


def invalid_origin_response() -> MCPResponse:
    return error_response(HTTPStatus.FORBIDDEN, None, -32000, "Invalid Origin header")


def unsupported_protocol_response(protocol_version: str) -> MCPResponse:
    return error_response(
        HTTPStatus.BAD_REQUEST,
        None,
        -32602,
        "Unsupported protocol version",
        {
            "supported": list(SUPPORTED_PROTOCOL_VERSIONS),
            "requested": protocol_version,
        },
    )


def handle_request(
    payload: object,
    *,
    controller,
    protocol_version: str | None = None,
) -> MCPResponse:
    if (
        protocol_version is not None
        and protocol_version not in SUPPORTED_PROTOCOL_VERSIONS
    ):
        return unsupported_protocol_response(protocol_version)

    if not isinstance(payload, dict):
        return error_response(HTTPStatus.BAD_REQUEST, None, -32600, "Invalid Request")

    if payload.get("jsonrpc") != "2.0":
        return error_response(
            HTTPStatus.BAD_REQUEST,
            payload.get("id"),
            -32600,
            "Invalid Request",
        )

    if "method" not in payload and ("result" in payload or "error" in payload):
        return MCPResponse(HTTPStatus.ACCEPTED)

    method = payload.get("method")
    if not isinstance(method, str):
        return error_response(
            HTTPStatus.BAD_REQUEST,
            payload.get("id"),
            -32600,
            "Invalid Request",
        )

    if "id" not in payload:
        return MCPResponse(HTTPStatus.ACCEPTED)

    message_id = payload["id"]
    if not isinstance(message_id, (str, int)) or isinstance(message_id, bool):
        return error_response(HTTPStatus.BAD_REQUEST, None, -32600, "Invalid Request")

    if method == "initialize":
        params = payload.get("params")
        requested_version = (
            params.get("protocolVersion") if isinstance(params, dict) else None
        )
        return result_response(message_id, initialize_result(requested_version))

    if method == "ping":
        return result_response(message_id, {})

    if method == "tools/list":
        return result_response(message_id, {"tools": [tool_definition()]})

    if method == "tools/call":
        return MCPResponse(
            HTTPStatus.OK,
            handle_tool_call(controller, message_id, payload.get("params")),
        )

    return MCPResponse(
        HTTPStatus.OK,
        jsonrpc_error(message_id, -32601, f"Method not found: {method}"),
    )


def result_response(message_id: str | int, result: dict[str, Any]) -> MCPResponse:
    return MCPResponse(HTTPStatus.OK, jsonrpc_result(message_id, result))


def jsonrpc_result(message_id: str | int, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "result": result}


def error_response(
    status: HTTPStatus,
    message_id: object,
    code: int,
    message: str,
    data: dict[str, Any] | None = None,
) -> MCPResponse:
    return MCPResponse(status, jsonrpc_error(message_id, code, message, data))


def jsonrpc_error(
    message_id: object,
    code: int,
    message: str,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": message_id, "error": error}


def tool_error(message: str) -> dict[str, Any]:
    return {
        "content": [{"type": "text", "text": message}],
        "isError": True,
    }


def tool_definition() -> dict[str, Any]:
    faces = list_faces()
    return {
        "name": TOOL_NAME,
        "title": "Send Message",
        "description": "Update the InkyPal display with a built-in face and message content.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "face": {
                    "type": "string",
                    "description": "Built-in face name to show. Allowed values: "
                    + ", ".join(faces)
                    + ".",
                    "enum": faces,
                },
                "content": {
                    "type": "string",
                    "description": "Message text to show below the face.",
                },
            },
            "required": ["face", "content"],
            "additionalProperties": False,
        },
    }


def initialize_result(requested_version: object) -> dict[str, Any]:
    protocol_version = (
        requested_version
        if requested_version in SUPPORTED_PROTOCOL_VERSIONS
        else PROTOCOL_VERSION
    )
    return {
        "protocolVersion": protocol_version,
        "capabilities": {"tools": {"listChanged": False}},
        "serverInfo": {
            "name": "inkypal",
            "title": "InkyPal",
            "version": __version__,
            "description": "A tiny smart companion on e-ink",
        },
    }


def handle_tool_call(controller, message_id: str | int, params: object) -> dict[str, Any]:
    if not isinstance(params, dict):
        return jsonrpc_error(message_id, -32602, "Invalid params")

    name = params.get("name")
    if name != TOOL_NAME:
        return jsonrpc_error(message_id, -32602, f"Unknown tool: {name}")

    arguments = params.get("arguments")
    if not isinstance(arguments, dict):
        return jsonrpc_result(
            message_id,
            tool_error("Invalid arguments: expected an object."),
        )

    face = arguments.get("face")
    content = arguments.get("content")
    if not isinstance(face, str) or not isinstance(content, str):
        return jsonrpc_result(
            message_id,
            tool_error("Invalid arguments: face and content must be strings."),
        )

    faces = list_faces()
    if face not in faces:
        return jsonrpc_result(
            message_id,
            tool_error(
                "Unknown face. Use one of: " + ", ".join(faces) + "."
            ),
        )

    controller.update(face=face, message=content)
    return jsonrpc_result(
        message_id,
        {
            "content": [{"type": "text", "text": "Message sent."}],
            "structuredContent": controller.status_payload(),
            "isError": False,
        },
    )
