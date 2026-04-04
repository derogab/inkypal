from unittest import TestCase

from inkypal.display import DisplayController, DisplayState
from inkypal.faces import IDLE_FACES


class FakeEpd:
    width = 122
    height = 250

    def __init__(self) -> None:
        self.operations: list[str] = []

    def init(self) -> None:
        self.operations.append("init")

    def clear(self) -> None:
        self.operations.append("clear")

    def display_part_base_image(self, _buffer) -> None:
        self.operations.append("display_part_base_image")

    def display_partial(self, _buffer) -> None:
        self.operations.append("display_partial")

    def display(self, _buffer) -> None:
        self.operations.append("display")

    def get_buffer(self, _image):
        return bytearray(b"buffer")

    def sleep(self) -> None:
        self.operations.append("sleep")


class DisplayControllerTests(TestCase):
    def test_api_face_override_expires_back_to_idle(self) -> None:
        fake_time = [0.0]
        epd = FakeEpd()
        controller = DisplayController(
            epd,
            DisplayState(
                face=IDLE_FACES[1],
                message="",
                rotation=180,
                host="127.0.0.1",
                port=8080,
            ),
            now=lambda: fake_time[0],
            face_override_seconds=60,
        )

        controller.render_current()
        controller.update(face="love", message="hello")
        self.assertEqual(controller.state.face, "love")

        fake_time[0] = 30.0
        controller.animate()
        self.assertEqual(controller.state.face, "love")

        fake_time[0] = 61.0
        controller.animate()
        self.assertEqual(controller.state.face, "look_right")

    def test_power_off_pauses_idle_animation(self) -> None:
        epd = FakeEpd()
        controller = DisplayController(
            epd,
            DisplayState(
                face=IDLE_FACES[1],
                message="",
                rotation=180,
                host="127.0.0.1",
                port=8080,
            ),
        )

        controller.render_current()
        controller.power_off()
        face_before = controller.state.face
        controller.animate()
        self.assertEqual(controller.state.face, face_before)
