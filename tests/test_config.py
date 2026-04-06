from unittest import TestCase

from inkypal.config import (
    DEFAULT_AI_BASE_URL,
    DEFAULT_AI_MODEL,
    get_ai_config,
    get_configured_port,
    parse_port,
)


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


class AIConfigTests(TestCase):
    def test_returns_none_when_api_key_missing(self) -> None:
        self.assertIsNone(get_ai_config({}))

    def test_returns_none_when_api_key_blank(self) -> None:
        self.assertIsNone(get_ai_config({"OPENAI_API_KEY": "  "}))

    def test_returns_config_with_defaults(self) -> None:
        cfg = get_ai_config({"OPENAI_API_KEY": "sk-test"})
        self.assertIsNotNone(cfg)
        self.assertEqual(cfg.api_key, "sk-test")
        self.assertEqual(cfg.base_url, DEFAULT_AI_BASE_URL)
        self.assertEqual(cfg.model, DEFAULT_AI_MODEL)

    def test_custom_base_url_and_model(self) -> None:
        cfg = get_ai_config(
            {
                "OPENAI_API_KEY": "sk-test",
                "OPENAI_BASE_URL": "http://localhost:1234/v1/",
                "OPENAI_MODEL": "llama3",
            }
        )
        self.assertEqual(cfg.base_url, "http://localhost:1234/v1")
        self.assertEqual(cfg.model, "llama3")

    def test_trailing_slash_stripped_from_base_url(self) -> None:
        cfg = get_ai_config(
            {
                "OPENAI_API_KEY": "key",
                "OPENAI_BASE_URL": "http://host/v1///",
            }
        )
        self.assertEqual(cfg.base_url, "http://host/v1")
