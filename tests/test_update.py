import json
from unittest import TestCase
from unittest.mock import MagicMock, patch

from inkypal.update import _parse_version, check_update_available


class ParseVersionTests(TestCase):
    def test_parses_tagged_version(self) -> None:
        self.assertEqual(_parse_version("v0.2.0"), (0, 2, 0))

    def test_parses_bare_version(self) -> None:
        self.assertEqual(_parse_version("1.2.3"), (1, 2, 3))

    def test_ignores_prerelease_suffix(self) -> None:
        self.assertEqual(_parse_version("v1.0.0-beta.1"), (1, 0, 0))

    def test_empty_returns_empty_tuple(self) -> None:
        self.assertEqual(_parse_version(""), ())

    def test_garbage_returns_empty_tuple(self) -> None:
        self.assertEqual(_parse_version("not-a-version"), ())

    def test_newer_version_compares_greater(self) -> None:
        self.assertGreater(_parse_version("v0.3.0"), _parse_version("v0.2.0"))

    def test_same_version_not_greater(self) -> None:
        self.assertFalse(_parse_version("v0.2.0") > _parse_version("v0.2.0"))

    def test_older_version_not_greater(self) -> None:
        self.assertFalse(_parse_version("v0.1.0") > _parse_version("v0.2.0"))


def _mock_response(data: dict) -> MagicMock:
    response = MagicMock()
    response.read.return_value = json.dumps(data).encode("utf-8")
    response.__enter__ = MagicMock(return_value=response)
    response.__exit__ = MagicMock(return_value=False)
    return response


class CheckUpdateAvailableTests(TestCase):
    @patch("inkypal.update.urllib.request.urlopen")
    def test_returns_true_when_newer_version_exists(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_response({"tag_name": "v99.0.0"})
        self.assertTrue(check_update_available())

    @patch("inkypal.update.urllib.request.urlopen")
    def test_returns_false_when_current_is_latest(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_response({"tag_name": "v0.0.1"})
        self.assertFalse(check_update_available())

    @patch("inkypal.update.urllib.request.urlopen")
    def test_returns_false_for_same_version(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_response({"tag_name": "v0.2.0"})
        self.assertFalse(check_update_available(current_version="0.2.0"))

    @patch("inkypal.update.urllib.request.urlopen")
    def test_returns_false_on_network_error(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = OSError("no internet")
        self.assertFalse(check_update_available())

    @patch("inkypal.update.urllib.request.urlopen")
    def test_returns_false_on_empty_tag(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_response({"tag_name": ""})
        self.assertFalse(check_update_available())

    @patch("inkypal.update.urllib.request.urlopen")
    def test_returns_false_on_missing_tag(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_response({})
        self.assertFalse(check_update_available())

    @patch("inkypal.update.urllib.request.urlopen")
    def test_accepts_explicit_current_version(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_response({"tag_name": "v1.0.0"})
        self.assertTrue(check_update_available(current_version="0.9.0"))
        self.assertFalse(check_update_available(current_version="2.0.0"))
