"""Built-in text faces for the display."""

FACES = {
    "look_left": "(O_o)",
    "look_center": "(o_o)",
    "look_right": "(o_O)",
    "happy": "(o_o)",
    "alert": "(O_O)",
    "sleepy": "(-_-)",
    "debug": "(x_x)",
    "curious": "(o_O)",
    "excited": "(^_^)",
    "love": "(o3o)",
    "sad": "(u_u)",
    "cool": "(B_B)",
    "angry": "(>_<)",
}

IDLE_FACES = ("look_left", "look_center", "look_right")


def list_faces() -> list[str]:
    """Return available built-in face names."""
    return sorted(FACES)


def resolve_face(name: str | None) -> tuple[str, str]:
    """Return the face label and the face text to render."""
    if not name:
        name = "happy"

    key = name.lower()
    if key not in FACES:
        raise ValueError(f"unknown face: {name}")
    return key, FACES[key]
