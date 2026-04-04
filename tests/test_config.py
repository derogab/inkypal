from unittest import TestCase

from inkypal.config import get_configured_port, parse_port


class ConfigTests(TestCase):
    def test_parse_port_returns_zero_when_unset(self) -> None:
        self.assertEqual(parse_port(None), 0)
        self.assertEqual(parse_port(""), 0)

    def test_parse_port_accepts_valid_value(self) -> None:
        self.assertEqual(parse_port("8080"), 8080)

    def test_parse_port_rejects_invalid_value(self) -> None:
        with self.assertRaisesRegex(ValueError, "integer"):
            parse_port("abc")

    def test_parse_port_rejects_out_of_range_value(self) -> None:
        with self.assertRaisesRegex(ValueError, "between 1 and 65535"):
            parse_port("70000")

    def test_get_configured_port_reads_mapping(self) -> None:
        self.assertEqual(get_configured_port({"INKYPAL_PORT": "9000"}), 9000)
