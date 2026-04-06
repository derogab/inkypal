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

    def test_wrap_message_keeps_more_content_when_more_lines_fit(self) -> None:
        image = Image.new("1", (250, 122), 255)
        draw = ImageDraw.Draw(image)
        text = (
            "The display should use more room so longer status updates stay readable "
            "before they need to be truncated."
        )

        two_lines = wrap_message(
            text,
            draw,
            load_font(12),
            max_width=120,
            max_lines=2,
            scale=1,
        )
        four_lines = wrap_message(
            text,
            draw,
            load_font(12),
            max_width=120,
            max_lines=4,
            scale=1,
        )

        self.assertGreater(
            len(four_lines.replace("\n", "")),
            len(two_lines.replace("\n", "")),
        )
        self.assertLessEqual(len(four_lines.splitlines()), 4)
        self.assertTrue(two_lines.splitlines()[-1].endswith("…"))

    def test_render_with_update_available_uses_expected_size(self) -> None:
        image = render_face_image(
            face_text="(o_o)",
            message="hello",
            host="127.0.0.1",
            port=8080,
            update_available=True,
        )
        self.assertEqual(image.size, (250, 122))

    def test_update_dot_draws_dark_pixels(self) -> None:
        without = render_face_image(
            face_text="(o_o)",
            message="",
            host="127.0.0.1",
            port=8080,
            rotation=0,
            update_available=False,
        )
        with_dot = render_face_image(
            face_text="(o_o)",
            message="",
            host="127.0.0.1",
            port=8080,
            rotation=0,
            update_available=True,
        )
        without_data = list(without.tobytes())
        with_data = list(with_dot.tobytes())
        diff_pixels = sum(
            1
            for a, b in zip(without_data, with_data)
            if a != b
        )
        self.assertGreater(diff_pixels, 0)

    def test_ellipsize_text_shortens_when_needed(self) -> None:
        self.assertEqual(ellipsize_text("abcdef", 4), "abc…")
