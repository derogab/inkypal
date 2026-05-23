import json
import logging
from threading import Thread
from unittest import TestCase
from unittest.mock import patch

from inkypal.ai import AIResponse
from inkypal.api import ROOT_ENDPOINTS, make_server
from inkypal.config import AIConfig
from inkypal.display import DisplayController, DisplayState


class FakeEpd:
    width = 122
    height = 250

    def init(self) -> None:
        return None

    def clear(self) -> None:
        return None

    def display_part_base_image(self, _buffer) -> None:
        return None

    def display_partial(self, _buffer) -> None:
        return None

    def display(self, _buffer) -> None:
        return None

    def get_buffer(self, _image):
        return bytearray(b"buffer")

    def sleep(self) -> None:
        return None


class ApiTests(TestCase):
    def test_root_endpoint_reports_runtime_summary(self) -> None:
        controller = DisplayController(
            FakeEpd(),
            DisplayState(
                face="look_center",
                message="",
                rotation=180,
                host="127.0.0.1",
                port=0,
            ),
        )
        server = make_server(controller, host="127.0.0.1", port=0)
        controller.state.port = server.server_address[1]
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            import urllib.request

            with urllib.request.urlopen(f"http://127.0.0.1:{controller.state.port}/") as response:
                payload = json.loads(response.read().decode("utf-8"))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)

        self.assertTrue(payload["running"])
        self.assertEqual(payload["port"], controller.state.port)
        self.assertEqual(payload["endpoints"], ROOT_ENDPOINTS)

    def test_debug_log_emitted_for_request(self) -> None:
        controller = DisplayController(
            FakeEpd(),
            DisplayState(
                face="look_center",
                message="",
                rotation=180,
                host="127.0.0.1",
                port=0,
            ),
        )
        server = make_server(controller, host="127.0.0.1", port=0)
        controller.state.port = server.server_address[1]
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            import urllib.request

            with self.assertLogs("inkypal.api", level=logging.DEBUG) as cm:
                with urllib.request.urlopen(f"http://127.0.0.1:{controller.state.port}/health") as response:
                    response.read()
            self.assertTrue(any("/health" in msg for msg in cm.output))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)

    def test_message_endpoint_updates_face_and_content(self) -> None:
        controller = DisplayController(
            FakeEpd(),
            DisplayState(
                face="look_center",
                message="",
                rotation=180,
                host="127.0.0.1",
                port=0,
            ),
        )
        server = make_server(controller, host="127.0.0.1", port=0)
        controller.state.port = server.server_address[1]
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            import urllib.request

            request = urllib.request.Request(
                f"http://127.0.0.1:{controller.state.port}/message",
                data=json.dumps({"face": "love", "content": "Text Example"}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request) as response:
                payload = json.loads(response.read().decode("utf-8"))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)

        self.assertEqual(payload["face"], "love")
        self.assertEqual(payload["message"], "Text Example")

    def test_invalid_face_discarded_when_content_present(self) -> None:
        controller = DisplayController(
            FakeEpd(),
            DisplayState(
                face="look_center",
                message="",
                rotation=180,
                host="127.0.0.1",
                port=0,
            ),
        )
        server = make_server(controller, host="127.0.0.1", port=0)
        controller.state.port = server.server_address[1]
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            import urllib.request

            request = urllib.request.Request(
                f"http://127.0.0.1:{controller.state.port}/message",
                data=json.dumps({"face": "nonexistent", "content": "hello"}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request) as response:
                payload = json.loads(response.read().decode("utf-8"))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["message"], "hello")

    def test_invalid_face_without_content_returns_status(self) -> None:
        controller = DisplayController(
            FakeEpd(),
            DisplayState(
                face="look_center",
                message="",
                rotation=180,
                host="127.0.0.1",
                port=0,
            ),
        )
        server = make_server(controller, host="127.0.0.1", port=0)
        controller.state.port = server.server_address[1]
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            import urllib.request

            request = urllib.request.Request(
                f"http://127.0.0.1:{controller.state.port}/message",
                data=json.dumps({"face": "nonexistent"}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request) as response:
                payload = json.loads(response.read().decode("utf-8"))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["face"], "look_center")

    def test_message_endpoint_transforms_content_when_ai_configured(self) -> None:
        controller = DisplayController(
            FakeEpd(),
            DisplayState(
                face="look_center",
                message="",
                rotation=180,
                host="127.0.0.1",
                port=0,
            ),
        )
        ai_config = AIConfig(base_url="http://localhost", api_key="key", model="model")
        server = make_server(controller, host="127.0.0.1", port=0, ai_config=ai_config)
        controller.state.port = server.server_address[1]
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            import urllib.request

            request = urllib.request.Request(
                f"http://127.0.0.1:{controller.state.port}/message",
                data=json.dumps({"content": "raw update"}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with patch(
                "inkypal.ai.transform_message",
                return_value=AIResponse(message="friendly update", face="excited"),
            ) as transform_message:
                with urllib.request.urlopen(request) as response:
                    payload = json.loads(response.read().decode("utf-8"))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)

        transform_message.assert_called_once_with("raw update", ai_config)
        self.assertEqual(payload["face"], "excited")
        self.assertEqual(payload["message"], "friendly update")

    def test_requests_without_api_key_are_rejected_when_configured(self) -> None:
        controller = DisplayController(
            FakeEpd(),
            DisplayState(
                face="look_center",
                message="",
                rotation=180,
                host="127.0.0.1",
                port=0,
            ),
        )
        server = make_server(controller, host="127.0.0.1", port=0, api_key="secret")
        controller.state.port = server.server_address[1]
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            import urllib.error
            import urllib.request

            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(f"http://127.0.0.1:{controller.state.port}/status")
            self.assertEqual(ctx.exception.code, 401)
            self.assertIn("Bearer", ctx.exception.headers.get("WWW-Authenticate", ""))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)

    def test_requests_with_wrong_api_key_are_rejected(self) -> None:
        controller = DisplayController(
            FakeEpd(),
            DisplayState(
                face="look_center",
                message="",
                rotation=180,
                host="127.0.0.1",
                port=0,
            ),
        )
        server = make_server(controller, host="127.0.0.1", port=0, api_key="secret")
        controller.state.port = server.server_address[1]
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            import urllib.error
            import urllib.request

            request = urllib.request.Request(
                f"http://127.0.0.1:{controller.state.port}/status",
                headers={"Authorization": "Bearer wrong"},
            )
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(request)
            self.assertEqual(ctx.exception.code, 401)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)

    def test_requests_with_correct_api_key_are_accepted(self) -> None:
        controller = DisplayController(
            FakeEpd(),
            DisplayState(
                face="look_center",
                message="",
                rotation=180,
                host="127.0.0.1",
                port=0,
            ),
        )
        server = make_server(controller, host="127.0.0.1", port=0, api_key="secret")
        controller.state.port = server.server_address[1]
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            import urllib.request

            request = urllib.request.Request(
                f"http://127.0.0.1:{controller.state.port}/message",
                data=json.dumps({"face": "love", "content": "Text Example"}).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer secret",
                },
                method="POST",
            )
            with urllib.request.urlopen(request) as response:
                payload = json.loads(response.read().decode("utf-8"))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)

        self.assertEqual(payload["face"], "love")
        self.assertEqual(payload["message"], "Text Example")

    def test_message_endpoint_bypass_ai_shows_raw_content(self) -> None:
        controller = DisplayController(
            FakeEpd(),
            DisplayState(
                face="look_center",
                message="",
                rotation=180,
                host="127.0.0.1",
                port=0,
            ),
        )
        ai_config = AIConfig(base_url="http://localhost", api_key="key", model="model")
        server = make_server(controller, host="127.0.0.1", port=0, ai_config=ai_config)
        controller.state.port = server.server_address[1]
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            import urllib.request

            request = urllib.request.Request(
                f"http://127.0.0.1:{controller.state.port}/message",
                data=json.dumps({"content": "raw update", "bypass_ai": True}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with patch("inkypal.ai.transform_message") as transform_message:
                with urllib.request.urlopen(request) as response:
                    payload = json.loads(response.read().decode("utf-8"))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)

        transform_message.assert_not_called()
        self.assertEqual(payload["face"], "look_center")
        self.assertEqual(payload["message"], "raw update")

    def test_mcp_initialize_and_tools_list_exposes_send_to_inkypal_only(self) -> None:
        controller = DisplayController(
            FakeEpd(),
            DisplayState(
                face="look_center",
                message="",
                rotation=180,
                host="127.0.0.1",
                port=0,
            ),
        )
        server = make_server(controller, host="127.0.0.1", port=0)
        controller.state.port = server.server_address[1]
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            import urllib.request

            initialize = urllib.request.Request(
                f"http://127.0.0.1:{controller.state.port}/mcp",
                data=json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2025-11-25",
                            "capabilities": {},
                            "clientInfo": {"name": "test-client", "version": "1.0"},
                        },
                    }
                ).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                },
                method="POST",
            )
            with urllib.request.urlopen(initialize) as response:
                initialize_payload = json.loads(response.read().decode("utf-8"))

            tools_list = urllib.request.Request(
                f"http://127.0.0.1:{controller.state.port}/mcp",
                data=json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/list",
                    }
                ).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                    "MCP-Protocol-Version": "2025-11-25",
                },
                method="POST",
            )
            with urllib.request.urlopen(tools_list) as response:
                tools_payload = json.loads(response.read().decode("utf-8"))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)

        self.assertEqual(
            initialize_payload["result"]["protocolVersion"], "2025-11-25"
        )
        self.assertEqual(
            initialize_payload["result"]["capabilities"],
            {"tools": {"listChanged": False}},
        )
        server_description = initialize_payload["result"]["serverInfo"]["description"]
        self.assertIn("e-paper hardware", server_description)
        self.assertIn("writable face", server_description)
        self.assertIn("notify the user", server_description)
        tools = tools_payload["result"]["tools"]
        self.assertEqual([tool["name"] for tool in tools], ["send_to_inkypal"])
        self.assertIn("visible notification", tools[0]["description"])
        self.assertIn("hardware display", tools[0]["description"])
        self.assertIn("notify the user", tools[0]["description"])
        self.assertIn("few words", tools[0]["description"])
        self.assertEqual(
            tools[0]["inputSchema"]["required"],
            ["face", "content"],
        )
        self.assertIn(
            "love",
            tools[0]["inputSchema"]["properties"]["face"]["description"],
        )
        self.assertIn(
            "small",
            tools[0]["inputSchema"]["properties"]["content"]["description"],
        )

    def test_mcp_send_to_inkypal_tool_updates_face_and_content(self) -> None:
        controller = DisplayController(
            FakeEpd(),
            DisplayState(
                face="look_center",
                message="",
                rotation=180,
                host="127.0.0.1",
                port=0,
            ),
        )
        server = make_server(controller, host="127.0.0.1", port=0)
        controller.state.port = server.server_address[1]
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            import urllib.request

            request = urllib.request.Request(
                f"http://127.0.0.1:{controller.state.port}/mcp",
                data=json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "tools/call",
                        "params": {
                            "name": "send_to_inkypal",
                            "arguments": {
                                "face": "love",
                                "content": "MCP update",
                            },
                        },
                    }
                ).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request) as response:
                payload = json.loads(response.read().decode("utf-8"))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)

        self.assertFalse(payload["result"]["isError"])
        self.assertEqual(payload["result"]["structuredContent"]["face"], "love")
        self.assertEqual(payload["result"]["structuredContent"]["message"], "MCP update")
        self.assertEqual(controller.state.face, "love")
        self.assertEqual(controller.state.message, "MCP update")

    def test_mcp_send_to_inkypal_tool_bypasses_ai_transformation(self) -> None:
        controller = DisplayController(
            FakeEpd(),
            DisplayState(
                face="look_center",
                message="",
                rotation=180,
                host="127.0.0.1",
                port=0,
            ),
        )
        ai_config = AIConfig(base_url="http://localhost", api_key="key", model="model")
        server = make_server(controller, host="127.0.0.1", port=0, ai_config=ai_config)
        controller.state.port = server.server_address[1]
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            import urllib.request

            request = urllib.request.Request(
                f"http://127.0.0.1:{controller.state.port}/mcp",
                data=json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "tools/call",
                        "params": {
                            "name": "send_to_inkypal",
                            "arguments": {
                                "face": "love",
                                "content": "raw MCP update",
                            },
                        },
                    }
                ).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with patch("inkypal.ai.transform_message") as transform_message:
                with urllib.request.urlopen(request) as response:
                    payload = json.loads(response.read().decode("utf-8"))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)

        transform_message.assert_not_called()
        self.assertFalse(payload["result"]["isError"])
        self.assertEqual(payload["result"]["structuredContent"]["face"], "love")
        self.assertEqual(
            payload["result"]["structuredContent"]["message"],
            "raw MCP update",
        )
        self.assertEqual(controller.state.face, "love")
        self.assertEqual(controller.state.message, "raw MCP update")

    def test_mcp_send_to_inkypal_tool_reports_unknown_face_without_update(self) -> None:
        controller = DisplayController(
            FakeEpd(),
            DisplayState(
                face="look_center",
                message="",
                rotation=180,
                host="127.0.0.1",
                port=0,
            ),
        )
        server = make_server(controller, host="127.0.0.1", port=0)
        controller.state.port = server.server_address[1]
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            import urllib.request

            request = urllib.request.Request(
                f"http://127.0.0.1:{controller.state.port}/mcp",
                data=json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "tools/call",
                        "params": {
                            "name": "send_to_inkypal",
                            "arguments": {
                                "face": "missing",
                                "content": "MCP update",
                            },
                        },
                    }
                ).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request) as response:
                payload = json.loads(response.read().decode("utf-8"))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)

        self.assertTrue(payload["result"]["isError"])
        self.assertIn("Unknown face", payload["result"]["content"][0]["text"])
        self.assertEqual(controller.state.face, "look_center")
        self.assertEqual(controller.state.message, "")

    def test_mcp_send_to_inkypal_tool_reports_empty_face_without_update(self) -> None:
        controller = DisplayController(
            FakeEpd(),
            DisplayState(
                face="look_center",
                message="",
                rotation=180,
                host="127.0.0.1",
                port=0,
            ),
        )
        server = make_server(controller, host="127.0.0.1", port=0)
        controller.state.port = server.server_address[1]
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            import urllib.request

            request = urllib.request.Request(
                f"http://127.0.0.1:{controller.state.port}/mcp",
                data=json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "tools/call",
                        "params": {
                            "name": "send_to_inkypal",
                            "arguments": {
                                "face": "",
                                "content": "MCP update",
                            },
                        },
                    }
                ).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request) as response:
                payload = json.loads(response.read().decode("utf-8"))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)

        self.assertTrue(payload["result"]["isError"])
        self.assertIn("Unknown face", payload["result"]["content"][0]["text"])
        self.assertEqual(controller.state.face, "look_center")
        self.assertEqual(controller.state.message, "")

    def test_mcp_initialized_notification_is_accepted(self) -> None:
        controller = DisplayController(
            FakeEpd(),
            DisplayState(
                face="look_center",
                message="",
                rotation=180,
                host="127.0.0.1",
                port=0,
            ),
        )
        server = make_server(controller, host="127.0.0.1", port=0)
        controller.state.port = server.server_address[1]
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            import urllib.request

            request = urllib.request.Request(
                f"http://127.0.0.1:{controller.state.port}/mcp",
                data=json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "method": "notifications/initialized",
                    }
                ).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request) as response:
                status = response.status
                body = response.read()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)

        self.assertEqual(status, 202)
        self.assertEqual(body, b"")

    def test_mcp_endpoint_uses_api_key_authentication(self) -> None:
        controller = DisplayController(
            FakeEpd(),
            DisplayState(
                face="look_center",
                message="",
                rotation=180,
                host="127.0.0.1",
                port=0,
            ),
        )
        server = make_server(controller, host="127.0.0.1", port=0, api_key="secret")
        controller.state.port = server.server_address[1]
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            import urllib.error
            import urllib.request

            body = json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/list",
                }
            ).encode("utf-8")
            url = f"http://127.0.0.1:{controller.state.port}/mcp"

            unauthenticated = urllib.request.Request(
                url,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(unauthenticated)
            self.assertEqual(ctx.exception.code, 401)
            unauthenticated_headers = dict(ctx.exception.headers.items())

            authenticated = urllib.request.Request(
                url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer secret",
                },
                method="POST",
            )
            with urllib.request.urlopen(authenticated) as response:
                payload = json.loads(response.read().decode("utf-8"))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)

        self.assertNotIn("Access-Control-Allow-Origin", unauthenticated_headers)
        self.assertEqual(
            [tool["name"] for tool in payload["result"]["tools"]],
            ["send_to_inkypal"],
        )

    def test_mcp_auth_failure_includes_cors_headers_for_allowed_origin(self) -> None:
        controller = DisplayController(
            FakeEpd(),
            DisplayState(
                face="look_center",
                message="",
                rotation=180,
                host="127.0.0.1",
                port=0,
            ),
        )
        server = make_server(controller, host="127.0.0.1", port=0, api_key="secret")
        controller.state.port = server.server_address[1]
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            import urllib.error
            import urllib.request

            request = urllib.request.Request(
                f"http://127.0.0.1:{controller.state.port}/mcp",
                data=json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "tools/list",
                    }
                ).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Origin": "http://localhost:2276",
                    "Authorization": "Bearer stale",
                },
                method="POST",
            )
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(request)
            headers = dict(ctx.exception.headers.items())
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)

        self.assertEqual(ctx.exception.code, 401)
        self.assertEqual(
            headers.get("Access-Control-Allow-Origin"), "http://localhost:2276"
        )
        self.assertIn("Origin", headers.get("Vary", ""))
        self.assertIn("Bearer", headers.get("WWW-Authenticate", ""))

    def test_mcp_preflight_returns_cors_headers_for_allowed_origin(self) -> None:
        controller = DisplayController(
            FakeEpd(),
            DisplayState(
                face="look_center",
                message="",
                rotation=180,
                host="127.0.0.1",
                port=0,
            ),
        )
        server = make_server(controller, host="127.0.0.1", port=0)
        controller.state.port = server.server_address[1]
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            import urllib.request

            preflight = urllib.request.Request(
                f"http://127.0.0.1:{controller.state.port}/mcp",
                headers={
                    "Origin": "http://localhost:2276",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "authorization, content-type",
                },
                method="OPTIONS",
            )
            with urllib.request.urlopen(preflight) as response:
                status = response.status
                headers = dict(response.headers.items())
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)

        self.assertEqual(status, 204)
        self.assertEqual(
            headers.get("Access-Control-Allow-Origin"), "http://localhost:2276"
        )
        self.assertIn("POST", headers.get("Access-Control-Allow-Methods", ""))
        self.assertIn("OPTIONS", headers.get("Access-Control-Allow-Methods", ""))
        self.assertNotIn("GET", headers.get("Access-Control-Allow-Methods", ""))
        self.assertIn(
            "authorization",
            headers.get("Access-Control-Allow-Headers", "").lower(),
        )
        self.assertIn(
            "content-type",
            headers.get("Access-Control-Allow-Headers", "").lower(),
        )
        self.assertEqual(headers.get("Access-Control-Max-Age"), "86400")

    def test_mcp_response_includes_cors_headers_for_allowed_origin(self) -> None:
        controller = DisplayController(
            FakeEpd(),
            DisplayState(
                face="look_center",
                message="",
                rotation=180,
                host="127.0.0.1",
                port=0,
            ),
        )
        server = make_server(controller, host="127.0.0.1", port=0)
        controller.state.port = server.server_address[1]
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            import urllib.request

            request = urllib.request.Request(
                f"http://127.0.0.1:{controller.state.port}/mcp",
                data=json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "tools/list",
                    }
                ).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Origin": "http://localhost:2276",
                },
                method="POST",
            )
            with urllib.request.urlopen(request) as response:
                headers = dict(response.headers.items())
                response.read()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)

        self.assertEqual(
            headers.get("Access-Control-Allow-Origin"), "http://localhost:2276"
        )
        self.assertIn("Origin", headers.get("Vary", ""))

    def test_mcp_preflight_rejects_disallowed_origin(self) -> None:
        controller = DisplayController(
            FakeEpd(),
            DisplayState(
                face="look_center",
                message="",
                rotation=180,
                host="127.0.0.1",
                port=0,
            ),
        )
        server = make_server(controller, host="127.0.0.1", port=0)
        controller.state.port = server.server_address[1]
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            import urllib.error
            import urllib.request

            preflight = urllib.request.Request(
                f"http://127.0.0.1:{controller.state.port}/mcp",
                headers={
                    "Origin": "http://evil.example.com",
                    "Access-Control-Request-Method": "POST",
                },
                method="OPTIONS",
            )
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(preflight)
            self.assertEqual(ctx.exception.code, 403)
            headers = dict(ctx.exception.headers.items())
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)

        self.assertNotIn("Access-Control-Allow-Origin", headers)

    def test_mcp_request_rejects_malformed_origin(self) -> None:
        controller = DisplayController(
            FakeEpd(),
            DisplayState(
                face="look_center",
                message="",
                rotation=180,
                host="127.0.0.1",
                port=0,
            ),
        )
        server = make_server(controller, host="127.0.0.1", port=0)
        controller.state.port = server.server_address[1]
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            import urllib.error
            import urllib.request

            request = urllib.request.Request(
                f"http://127.0.0.1:{controller.state.port}/mcp",
                data=json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "tools/list",
                    }
                ).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Origin": "http://[::1",
                },
                method="POST",
            )
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(request)
            headers = dict(ctx.exception.headers.items())
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)

        self.assertEqual(ctx.exception.code, 403)
        self.assertNotIn("Access-Control-Allow-Origin", headers)

    def test_mcp_preflight_rejects_malformed_origin(self) -> None:
        controller = DisplayController(
            FakeEpd(),
            DisplayState(
                face="look_center",
                message="",
                rotation=180,
                host="127.0.0.1",
                port=0,
            ),
        )
        server = make_server(controller, host="127.0.0.1", port=0)
        controller.state.port = server.server_address[1]
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            import urllib.error
            import urllib.request

            preflight = urllib.request.Request(
                f"http://127.0.0.1:{controller.state.port}/mcp",
                headers={
                    "Origin": "http://[::1",
                    "Access-Control-Request-Method": "POST",
                },
                method="OPTIONS",
            )
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(preflight)
            headers = dict(ctx.exception.headers.items())
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)

        self.assertEqual(ctx.exception.code, 403)
        self.assertNotIn("Access-Control-Allow-Origin", headers)

    def test_mcp_request_rejects_origin_with_invalid_port(self) -> None:
        controller = DisplayController(
            FakeEpd(),
            DisplayState(
                face="look_center",
                message="",
                rotation=180,
                host="127.0.0.1",
                port=0,
            ),
        )
        server = make_server(controller, host="127.0.0.1", port=0)
        controller.state.port = server.server_address[1]
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            import urllib.error
            import urllib.request

            request = urllib.request.Request(
                f"http://127.0.0.1:{controller.state.port}/mcp",
                data=json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "tools/list",
                    }
                ).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Origin": "http://localhost:abc",
                },
                method="POST",
            )
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(request)
            headers = dict(ctx.exception.headers.items())
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)

        self.assertEqual(ctx.exception.code, 403)
        self.assertNotIn("Access-Control-Allow-Origin", headers)

    def test_mcp_get_returns_405_with_allow_post_and_options(self) -> None:
        controller = DisplayController(
            FakeEpd(),
            DisplayState(
                face="look_center",
                message="",
                rotation=180,
                host="127.0.0.1",
                port=0,
            ),
        )
        server = make_server(controller, host="127.0.0.1", port=0)
        controller.state.port = server.server_address[1]
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            import urllib.error
            import urllib.request

            request = urllib.request.Request(
                f"http://127.0.0.1:{controller.state.port}/mcp",
                method="GET",
            )
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(request)
            headers = dict(ctx.exception.headers.items())
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)

        self.assertEqual(ctx.exception.code, 405)
        allow = headers.get("Allow", "")
        self.assertIn("POST", allow)
        self.assertIn("OPTIONS", allow)
