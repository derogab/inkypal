"""Command line entry point."""

from __future__ import annotations

import sys
from threading import Event, Thread

from inkypal.api import make_server
from inkypal.display import DisplayController, DisplayState
from inkypal.faces import IDLE_FACES, resolve_face
from inkypal.network import get_local_ip
from inkypal.render import DEFAULT_MESSAGE, DEFAULT_ROTATION

IDLE_ANIMATION_SECONDS = 10


def run_idle_loop(controller: DisplayController, stop_event: Event) -> None:
    while not stop_event.wait(IDLE_ANIMATION_SECONDS):
        try:
            controller.animate()
        except Exception as error:
            print(f"idle animation error: {error}", file=sys.stderr)


def main() -> int:
    face_name, _ = resolve_face(IDLE_FACES[1])
    from inkypal.waveshare_v4 import EPD

    host = get_local_ip()
    epd = EPD()
    controller = DisplayController(
        epd=epd,
        state=DisplayState(
            face=face_name,
            message=DEFAULT_MESSAGE,
            rotation=DEFAULT_ROTATION,
            host=host,
            port=0,
        ),
    )

    server = make_server(controller)
    controller.state.port = server.server_address[1]
    stop_event = Event()
    idle_thread = Thread(target=run_idle_loop, args=(controller, stop_event), daemon=True)
    idle_thread.start()

    try:
        controller.render_current()
        print(
            f"inkypal API listening on http://{controller.state.host}:{controller.state.port}"
        )
        server.serve_forever()
        return 0
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        return 130
    finally:
        stop_event.set()
        idle_thread.join(timeout=1)
        server.server_close()
        controller.shutdown()
