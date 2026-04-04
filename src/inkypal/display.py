"""Display state and rendering orchestration."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from threading import RLock
from time import monotonic

from PIL import Image

from inkypal.config import DISPLAY_OVERRIDE_SECONDS
from inkypal.faces import IDLE_FACES, resolve_face
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

    def __init__(
        self,
        epd,
        state: DisplayState,
        *,
        now: Callable[[], float] = monotonic,
        idle_faces: Sequence[str] = IDLE_FACES,
        override_seconds: int = DISPLAY_OVERRIDE_SECONDS,
    ) -> None:
        self._epd = epd
        self._state = state
        self._lock = RLock()
        self._ready_for_partial = False
        self._powered_off = False
        self._override_until: float | None = None
        self._now = now
        self._idle_faces = tuple(idle_faces)
        self._override_seconds = override_seconds
        self._idle_index = 0

        if state.face in self._idle_faces:
            self._idle_index = (self._idle_faces.index(state.face) + 1) % len(self._idle_faces)

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
        with self._lock:
            if face is not None:
                face_name, _ = resolve_face(face)
                self._state.face = face_name
                if face_name in self._idle_faces:
                    self._idle_index = (self._idle_faces.index(face_name) + 1) % len(self._idle_faces)

            if message is not None:
                self._state.message = message

            self._refresh_override_until()

            self._powered_off = False
            self._render(self._state, partial=self._ready_for_partial)
            return self._state

    def animate(self) -> None:
        with self._lock:
            if self._powered_off:
                return

            if self._override_until is not None:
                if self._now() < self._override_until:
                    return

                self._override_until = None
                changed = False

                if self._state.message:
                    self._state.message = ""
                    changed = True

                if self._state.face not in self._idle_faces:
                    self._state.face = self._idle_faces[self._idle_index]
                    self._idle_index = (self._idle_index + 1) % len(self._idle_faces)
                    changed = True

                if changed:
                    self._render(self._state, partial=self._ready_for_partial)
                    return

            next_face = self._idle_faces[self._idle_index]
            self._idle_index = (self._idle_index + 1) % len(self._idle_faces)

            if self._state.face == next_face:
                return

            self._state.face = next_face
            self._render(self._state, partial=self._ready_for_partial)

    def shutdown(self) -> None:
        with self._lock:
            self._epd.sleep()
            self._ready_for_partial = False
            self._powered_off = False

    def power_off(self) -> DisplayState:
        blank_buffer = self._blank_buffer()
        with self._lock:
            self._powered_off = True
            self._override_until = None
            if not self._ready_for_partial:
                self._epd.init()
                self._epd.display_part_base_image(blank_buffer)
                self._ready_for_partial = True
            else:
                self._epd.display_partial(blank_buffer)
        return self._state

    def _refresh_override_until(self) -> None:
        if self._state.face not in self._idle_faces or self._state.message:
            self._override_until = self._now() + self._override_seconds
        else:
            self._override_until = None

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
