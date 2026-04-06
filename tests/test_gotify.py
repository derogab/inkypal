import json
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from unittest import TestCase
from unittest.mock import patch

from inkypal.config import GotifyConfig
from inkypal.gotify import send_message


class _FakeGotifyHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        self.server.last_path = self.path
        self.server.last_body = urllib.parse.parse_qs(body)
        self.server.last_headers = {
            key.lower(): value for key, value in self.headers.items()
        }

        reply = json.dumps({"id": 1}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(reply)))
        self.end_headers()
        self.wfile.write(reply)

    def log_message(self, format, *args) -> None:
        return


class GotifyTests(TestCase):
    @patch("inkypal.gotify.urllib.request.urlopen")
    def test_empty_message_skips_request(self, mock_urlopen) -> None:
        send_message("", GotifyConfig(base_url="https://push.example.com", token="token"))
        mock_urlopen.assert_not_called()

    def test_sends_message_to_gotify(self) -> None:
        server = HTTPServer(("127.0.0.1", 0), _FakeGotifyHandler)
        port = server.server_address[1]
        thread = Thread(target=server.handle_request, daemon=True)
        thread.start()

        send_message(
            "Hello from InkyPal",
            GotifyConfig(base_url=f"http://127.0.0.1:{port}/", token="app-token"),
        )
        server.server_close()
        thread.join(timeout=2)

        self.assertEqual(server.last_path, "/message?token=app-token")
        self.assertEqual(server.last_body["message"], ["Hello from InkyPal"])
        self.assertEqual(
            server.last_headers["content-type"],
            "application/x-www-form-urlencoded",
        )

    def test_fallback_on_connection_error(self) -> None:
        send_message(
            "Hello from InkyPal",
            GotifyConfig(base_url="http://127.0.0.1:1", token="app-token"),
        )
