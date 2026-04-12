import json
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from unittest import TestCase

from inkypal.ai import AI_RESPONSE_MAX_CHARS, AIResponse, transform_message
from inkypal.config import AIConfig


class _FakeCompletionHandler(BaseHTTPRequestHandler):
    response_text = "Hey, it is 32C out there!"

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length).decode("utf-8"))
        self.server.last_request_body = body
        self.server.last_request_headers = {
            key.lower(): value for key, value in self.headers.items()
        }

        reply = {
            "choices": [
                {"message": {"content": self.response_text}}
            ]
        }
        data = json.dumps(reply).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args) -> None:
        return


class TransformMessageTests(TestCase):
    def test_empty_content_returns_unchanged(self) -> None:
        cfg = AIConfig(base_url="http://localhost", api_key="k", model="m")
        result = transform_message("", cfg)
        self.assertEqual(result.message, "")
        self.assertIsNone(result.face)

    def test_successful_transformation(self) -> None:
        server = HTTPServer(("127.0.0.1", 0), _FakeCompletionHandler)
        port = server.server_address[1]
        thread = Thread(target=server.handle_request, daemon=True)
        thread.start()

        cfg = AIConfig(
            base_url=f"http://127.0.0.1:{port}",
            api_key="sk-test",
            model="test-model",
        )
        result = transform_message("temperature: 32C", cfg)
        server.server_close()
        thread.join(timeout=2)

        self.assertEqual(result.message, "Hey, it is 32C out there!")
        self.assertIsNone(result.face)
        body = server.last_request_body
        self.assertEqual(body["model"], "test-model")
        self.assertEqual(body["messages"][1]["content"], "temperature: 32C")
        self.assertNotIn("max_tokens", body)
        self.assertIn(
            f"Maximum {AI_RESPONSE_MAX_CHARS} characters",
            body["messages"][0]["content"],
        )

    def test_strips_surrounding_quotes(self) -> None:
        class QuotedHandler(_FakeCompletionHandler):
            response_text = '"Looking warm at 32C!"'

        server = HTTPServer(("127.0.0.1", 0), QuotedHandler)
        port = server.server_address[1]
        thread = Thread(target=server.handle_request, daemon=True)
        thread.start()

        cfg = AIConfig(
            base_url=f"http://127.0.0.1:{port}",
            api_key="sk-test",
            model="m",
        )
        result = transform_message("temp 32", cfg)
        server.server_close()
        thread.join(timeout=2)

        self.assertEqual(result.message, "Looking warm at 32C!")

    def test_clamps_long_responses_to_display_safe_length(self) -> None:
        class LongHandler(_FakeCompletionHandler):
            response_text = "x" * (AI_RESPONSE_MAX_CHARS + 10)

        server = HTTPServer(("127.0.0.1", 0), LongHandler)
        port = server.server_address[1]
        thread = Thread(target=server.handle_request, daemon=True)
        thread.start()

        cfg = AIConfig(
            base_url=f"http://127.0.0.1:{port}",
            api_key="sk-test",
            model="m",
        )
        result = transform_message("temp 32", cfg)
        server.server_close()
        thread.join(timeout=2)

        self.assertEqual(len(result.message), AI_RESPONSE_MAX_CHARS)
        self.assertTrue(result.message.endswith("…"))

    def test_sends_configured_headers(self) -> None:
        server = HTTPServer(("127.0.0.1", 0), _FakeCompletionHandler)
        port = server.server_address[1]
        thread = Thread(target=server.handle_request, daemon=True)
        thread.start()

        cfg = AIConfig(
            base_url=f"http://127.0.0.1:{port}",
            api_key="sk-test",
            model="m",
            headers={
                "HTTP-Referer": "https://github.com/derogab/inkypal",
                "X-OpenRouter-Title": "InkyPal AI",
                "X-OpenRouter-Categories": "personal-agent",
            },
        )
        transform_message("temp 32", cfg)
        server.server_close()
        thread.join(timeout=2)

        headers = server.last_request_headers
        self.assertEqual(headers["http-referer"], "https://github.com/derogab/inkypal")
        self.assertEqual(headers["x-openrouter-title"], "InkyPal AI")
        self.assertEqual(headers["x-openrouter-categories"], "personal-agent")

    def test_strips_think_blocks_from_reasoning_models(self) -> None:
        class ThinkHandler(_FakeCompletionHandler):
            response_text = "<think>Let me reason about this...</think>It is sunny!"

        server = HTTPServer(("127.0.0.1", 0), ThinkHandler)
        port = server.server_address[1]
        thread = Thread(target=server.handle_request, daemon=True)
        thread.start()

        cfg = AIConfig(
            base_url=f"http://127.0.0.1:{port}",
            api_key="sk-test",
            model="m",
        )
        result = transform_message("weather", cfg)
        server.server_close()
        thread.join(timeout=2)

        self.assertEqual(result.message, "It is sunny!")

    def test_fallback_on_connection_error(self) -> None:
        cfg = AIConfig(
            base_url="http://127.0.0.1:1",
            api_key="sk-test",
            model="m",
        )
        result = transform_message("raw data", cfg)
        self.assertEqual(result.message, "raw data")
        self.assertIsNone(result.face)

    def test_logs_warning_on_connection_error(self) -> None:
        cfg = AIConfig(
            base_url="http://127.0.0.1:1",
            api_key="sk-test",
            model="m",
        )
        with self.assertLogs("inkypal.ai", level=logging.WARNING) as cm:
            transform_message("raw data", cfg)
        self.assertTrue(any("AI request failed" in msg for msg in cm.output))

    def test_fallback_on_bad_json(self) -> None:
        class BadJsonHandler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", "2")
                self.end_headers()
                self.wfile.write(b"{}")

            def log_message(self, format, *args) -> None:
                return

        server = HTTPServer(("127.0.0.1", 0), BadJsonHandler)
        port = server.server_address[1]
        thread = Thread(target=server.handle_request, daemon=True)
        thread.start()

        cfg = AIConfig(
            base_url=f"http://127.0.0.1:{port}",
            api_key="sk-test",
            model="m",
        )
        result = transform_message("raw data", cfg)
        server.server_close()
        thread.join(timeout=2)

        self.assertEqual(result.message, "raw data")
        self.assertIsNone(result.face)


class SmartFaceTests(TestCase):
    def test_parses_face_tag_from_response(self) -> None:
        class FaceHandler(_FakeCompletionHandler):
            response_text = "[excited] Warm day ahead!"

        server = HTTPServer(("127.0.0.1", 0), FaceHandler)
        port = server.server_address[1]
        thread = Thread(target=server.handle_request, daemon=True)
        thread.start()

        cfg = AIConfig(
            base_url=f"http://127.0.0.1:{port}",
            api_key="sk-test",
            model="m",
        )
        result = transform_message("temperature: 32C", cfg)
        server.server_close()
        thread.join(timeout=2)

        self.assertEqual(result.face, "excited")
        self.assertEqual(result.message, "Warm day ahead!")

    def test_unknown_face_tag_ignored(self) -> None:
        class UnknownFaceHandler(_FakeCompletionHandler):
            response_text = "[robot] Beep boop!"

        server = HTTPServer(("127.0.0.1", 0), UnknownFaceHandler)
        port = server.server_address[1]
        thread = Thread(target=server.handle_request, daemon=True)
        thread.start()

        cfg = AIConfig(
            base_url=f"http://127.0.0.1:{port}",
            api_key="sk-test",
            model="m",
        )
        result = transform_message("hello", cfg)
        server.server_close()
        thread.join(timeout=2)

        self.assertIsNone(result.face)
        self.assertEqual(result.message, "[robot] Beep boop!")

    def test_missing_face_tag_returns_no_face(self) -> None:
        server = HTTPServer(("127.0.0.1", 0), _FakeCompletionHandler)
        port = server.server_address[1]
        thread = Thread(target=server.handle_request, daemon=True)
        thread.start()

        cfg = AIConfig(
            base_url=f"http://127.0.0.1:{port}",
            api_key="sk-test",
            model="m",
        )
        result = transform_message("temperature: 32C", cfg)
        server.server_close()
        thread.join(timeout=2)

        self.assertIsNone(result.face)
        self.assertEqual(result.message, "Hey, it is 32C out there!")

    def test_face_tag_with_think_block(self) -> None:
        class ThinkFaceHandler(_FakeCompletionHandler):
            response_text = "<think>hmm</think>[sad] Bad news today"

        server = HTTPServer(("127.0.0.1", 0), ThinkFaceHandler)
        port = server.server_address[1]
        thread = Thread(target=server.handle_request, daemon=True)
        thread.start()

        cfg = AIConfig(
            base_url=f"http://127.0.0.1:{port}",
            api_key="sk-test",
            model="m",
        )
        result = transform_message("bad stuff", cfg)
        server.server_close()
        thread.join(timeout=2)

        self.assertEqual(result.face, "sad")
        self.assertEqual(result.message, "Bad news today")

    def test_prompt_lists_available_faces(self) -> None:
        from inkypal.ai import AI_FACE_MOODS, SYSTEM_PROMPT

        for face_name in AI_FACE_MOODS:
            self.assertIn(face_name, SYSTEM_PROMPT)

    def test_all_ai_faces_are_valid(self) -> None:
        from inkypal.ai import AI_FACE_MOODS
        from inkypal.faces import resolve_face

        for face_name in AI_FACE_MOODS:
            key, text = resolve_face(face_name)
            self.assertEqual(key, face_name)
            self.assertTrue(text)
