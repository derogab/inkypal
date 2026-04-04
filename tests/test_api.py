import json
from threading import Thread
from unittest import TestCase

from inkypal.api import ROOT_ENDPOINTS, make_server
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
