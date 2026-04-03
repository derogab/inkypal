"""Display state and rendering orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock

from PIL import Image

from inkypal.faces import resolve_face
from inkypal.render import render_face_image


@dataclass
class DisplayState:
    """Current values rendered on screen."""

    face: str
    message: str
    rotation: int
    host: str
    port: int


class DisplayController:
    """Thread-safe wrapper for rendering updates to the panel."""

    def __init__(self, epd, state: DisplayState) -> None:
        self._epd = epd
        self._state = state
        self._lock = Lock()
        self._ready_for_partial = False

    @property
    def state(self) -> DisplayState:
        return self._state

    @property
    def display_ready(self) -> bool:
        return self._ready_for_partial

    def status_payload(self) -> dict[str, object]:
        return {
            "ok": True,
            "face": self._state.face,
            "message": self._state.message,
            "ip": self._state.host,
            "port": self._state.port,
        }

    def health_payload(self) -> dict[str, object]:
        return {
            "ok": True,
            "display_ready": self.display_ready,
            "api_ready": True,
        }

    def render_current(self) -> None:
        self._render(self._state, partial=False)

    def update(
        self,
        *,
        face: str | None = None,
        message: str | None = None,
    ) -> DisplayState:
        if face is not None:
            face_name, _ = resolve_face(face)
            self._state.face = face_name
        if message is not None:
            self._state.message = message
        self._render(self._state, partial=self._ready_for_partial)
        return self._state

    def shutdown(self) -> None:
        with self._lock:
            self._epd.sleep()
            self._ready_for_partial = False

    def power_off(self) -> DisplayState:
        blank_buffer = self._blank_buffer()
        with self._lock:
            if not self._ready_for_partial:
                self._epd.init()
                self._epd.display_part_base_image(blank_buffer)
                self._ready_for_partial = True
            else:
                self._epd.display_partial(blank_buffer)
        return self._state

    def _blank_buffer(self) -> bytearray:
        blank_image = Image.new("1", (self._epd.height, self._epd.width), 255)
        return self._epd.get_buffer(blank_image)

    def _render(self, state: DisplayState, *, partial: bool) -> None:
        _, face_text = resolve_face(state.face)
        image = render_face_image(
            face_text=face_text,
            message=state.message,
            host=state.host,
            port=state.port,
            rotation=state.rotation,
        )
        image_buffer = self._epd.get_buffer(image)
        with self._lock:
            if not self._ready_for_partial:
                self._epd.init()
                self._epd.clear()
                self._epd.display_part_base_image(image_buffer)
                self._ready_for_partial = True
                return

            if partial:
                self._epd.display_partial(image_buffer)
            else:
                self._epd.display(image_buffer)
