"""Command line entry point."""

from __future__ import annotations

import sys

from inkypal.api import make_server
from inkypal.display import DisplayController, DisplayState
from inkypal.faces import resolve_face
from inkypal.network import get_local_ip
from inkypal.render import DEFAULT_MESSAGE, DEFAULT_ROTATION


def main() -> int:
    face_name, _ = resolve_face("happy")
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
        server.server_close()
        controller.shutdown()
