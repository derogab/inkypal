from unittest import TestCase

from PIL import Image, ImageDraw

from inkypal.render import ellipsize_text, load_font, render_face_image, wrap_message


class RenderTests(TestCase):
    def test_render_face_image_uses_expected_size(self) -> None:
        image = render_face_image(
            face_text="(o_o)",
            message="hello",
            host="127.0.0.1",
            port=8080,
        )
        self.assertEqual(image.size, (250, 122))

    def test_wrap_message_limits_line_count(self) -> None:
        image = Image.new("1", (250, 122), 255)
        draw = ImageDraw.Draw(image)
        wrapped = wrap_message(
            "To thine own self be true and it must follow.",
            draw,
            load_font(16),
            max_width=120,
            max_lines=2,
            scale=1,
        )
        self.assertLessEqual(len(wrapped.splitlines()), 2)

    def test_ellipsize_text_shortens_when_needed(self) -> None:
        self.assertEqual(ellipsize_text("abcdef", 4), "abc…")
