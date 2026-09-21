"""Side-effect-free malformed/config scope rejection tests."""

import json
import unittest
from unittest.mock import patch

from spike import ConfigError, EXPECTED, validate_config


class ConfigTests(unittest.TestCase):
    def read_config(self, value):
        with patch("pathlib.Path.read_text", return_value=json.dumps(value)), \
                patch("subprocess.run", side_effect=AssertionError("Unexpected CLI access")), \
                patch("socket.socket", side_effect=AssertionError("Unexpected network access")):
            return validate_config("unused-config.json")

    def test_missing_path(self):
        with self.assertRaisesRegex(ConfigError, "Missing --config"):
            validate_config(None)

    def test_malformed_json(self):
        with patch("pathlib.Path.read_text", return_value="{"), \
                self.assertRaisesRegex(ConfigError, "readable JSON"):
            validate_config("unused-config.json")

    def test_missing_field(self):
        config = dict(EXPECTED)
        del config["projectEndpoint"]
        with self.assertRaisesRegex(ConfigError, "requires only"):
            self.read_config(config)

    def test_wrong_scope_each_field(self):
        for field in EXPECTED:
            with self.subTest(field=field), self.assertRaisesRegex(ConfigError, "exact scope"):
                self.read_config({**EXPECTED, field: "unapproved"})

    def test_credentials_rejected(self):
        with self.assertRaisesRegex(ConfigError, "credentials are not accepted"):
            self.read_config({**EXPECTED, "apiKey": "synthetic-not-a-real-key"})

    def test_array_rejected(self):
        with self.assertRaisesRegex(ConfigError, "requires only"):
            self.read_config([])

    def test_approved_config(self):
        self.assertEqual(self.read_config(EXPECTED), EXPECTED)


if __name__ == "__main__":
    unittest.main()
