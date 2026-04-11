from unittest import TestCase

from inkypal.config import (
    DEFAULT_AI_BASE_URL,
    DEFAULT_AI_MODEL,
    DEFAULT_OPENROUTER_CATEGORIES,
    DEFAULT_OPENROUTER_REFERER,
    DEFAULT_OPENROUTER_TITLE,
    get_ai_config,
    get_configured_port,
    get_debug_mode,
    get_gotify_config,
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


class DebugModeTests(TestCase):
    def test_disabled_by_default(self) -> None:
        self.assertFalse(get_debug_mode({}))

    def test_enabled_with_true(self) -> None:
        self.assertTrue(get_debug_mode({"DEBUG_MODE": "true"}))

    def test_enabled_with_one(self) -> None:
        self.assertTrue(get_debug_mode({"DEBUG_MODE": "1"}))

    def test_enabled_with_yes(self) -> None:
        self.assertTrue(get_debug_mode({"DEBUG_MODE": "yes"}))

    def test_case_insensitive(self) -> None:
        self.assertTrue(get_debug_mode({"DEBUG_MODE": "TRUE"}))

    def test_disabled_with_arbitrary_string(self) -> None:
        self.assertFalse(get_debug_mode({"DEBUG_MODE": "no"}))


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
        self.assertEqual(cfg.headers["HTTP-Referer"], DEFAULT_OPENROUTER_REFERER)
        self.assertEqual(cfg.headers["X-OpenRouter-Title"], DEFAULT_OPENROUTER_TITLE)
        self.assertEqual(
            cfg.headers["X-OpenRouter-Categories"],
            DEFAULT_OPENROUTER_CATEGORIES,
        )

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
        self.assertEqual(cfg.headers, {})

    def test_trailing_slash_stripped_from_base_url(self) -> None:
        cfg = get_ai_config(
            {
                "OPENAI_API_KEY": "key",
                "OPENAI_BASE_URL": "http://host/v1///",
            }
        )
        self.assertEqual(cfg.base_url, "http://host/v1")

    def test_openrouter_base_url_with_port_keeps_attribution_headers(self) -> None:
        cfg = get_ai_config(
            {
                "OPENAI_API_KEY": "sk-test",
                "OPENAI_BASE_URL": "https://openrouter.ai:443/api/v1",
            }
        )
        self.assertEqual(cfg.headers["HTTP-Referer"], DEFAULT_OPENROUTER_REFERER)
        self.assertEqual(cfg.headers["X-OpenRouter-Title"], DEFAULT_OPENROUTER_TITLE)
        self.assertEqual(
            cfg.headers["X-OpenRouter-Categories"],
            DEFAULT_OPENROUTER_CATEGORIES,
        )


class GotifyConfigTests(TestCase):
    def test_returns_none_when_url_or_token_missing(self) -> None:
        self.assertIsNone(get_gotify_config({}))
        self.assertIsNone(get_gotify_config({"GOTIFY_URL": "https://push.example.com"}))
        self.assertIsNone(get_gotify_config({"GOTIFY_TOKEN": "app-token"}))

    def test_returns_config_when_url_and_token_are_set(self) -> None:
        cfg = get_gotify_config(
            {
                "GOTIFY_URL": " https://push.example.com/ ",
                "GOTIFY_TOKEN": " app-token ",
            }
        )
        self.assertIsNotNone(cfg)
        self.assertEqual(cfg.base_url, "https://push.example.com")
        self.assertEqual(cfg.token, "app-token")
