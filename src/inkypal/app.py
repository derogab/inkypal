"""Runtime entry point."""

from __future__ import annotations

import logging
import sys
from functools import partial
from threading import Event, Thread
from time import monotonic

from inkypal.api import make_server
from inkypal.config import IDLE_ANIMATION_SECONDS, UPDATE_CHECK_INTERVAL_SECONDS, get_ai_config, get_configured_port, get_debug_mode, get_gotify_config
from inkypal.display import DisplayController, DisplayState
from inkypal.faces import IDLE_FACES, resolve_face
from inkypal.gotify import send_message
from inkypal.network import get_local_ip
from inkypal.render import DEFAULT_MESSAGE, DEFAULT_ROTATION
from inkypal.update import check_update_available


def run_idle_loop(controller: DisplayController, stop_event: Event) -> None:
    next_update_check = 0.0
    while not stop_event.wait(IDLE_ANIMATION_SECONDS):
        try:
            controller.animate()
        except Exception as error:
            print(f"idle animation error: {error}", file=sys.stderr)

        now = monotonic()
        if now >= next_update_check:
            next_update_check = now + UPDATE_CHECK_INTERVAL_SECONDS
            controller.set_update_available(check_update_available())


def main() -> int:
    logging.basicConfig(
        level=logging.DEBUG if get_debug_mode() else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    face_name, _ = resolve_face(IDLE_FACES[1])
    from inkypal.waveshare_v4 import EPD

    host = get_local_ip()
    port = get_configured_port()
    ai_config = get_ai_config()
    gotify_config = get_gotify_config()
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
        message_sink=(
            partial(send_message, config=gotify_config)
            if gotify_config is not None
            else None
        ),
    )

    server = make_server(controller, port=port, ai_config=ai_config)
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
