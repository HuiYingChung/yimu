import json
import tempfile
import unittest
from pathlib import Path

import config


class ConfigLanguageTests(unittest.TestCase):
    def setUp(self):
        self._original = {
            "_SETTINGS_PATH": config._SETTINGS_PATH,
            "PROVIDER": config.PROVIDER,
            "TARGET_LANGUAGE_CODE": config.TARGET_LANGUAGE_CODE,
        }
        self._temp_dir = tempfile.TemporaryDirectory()
        config._SETTINGS_PATH = str(
            Path(self._temp_dir.name) / "settings.json")

    def tearDown(self):
        for name, value in self._original.items():
            setattr(config, name, value)
        self._temp_dir.cleanup()

    def _write_settings(self, data):
        Path(config._SETTINGS_PATH).write_text(
            json.dumps(data), encoding="utf-8")

    def test_load_coerces_target_for_saved_provider(self):
        self._write_settings({
            "PROVIDER": "openai",
            "TARGET_LANGUAGE_CODE": "pl",
        })
        config.load_user_settings()
        self.assertEqual(config.PROVIDER, "openai")
        self.assertEqual(config.TARGET_LANGUAGE_CODE, "zh-Hant")

    def test_load_maps_portuguese_variant_between_providers(self):
        self._write_settings({
            "PROVIDER": "openai",
            "TARGET_LANGUAGE_CODE": "pt-BR",
        })
        config.load_user_settings()
        self.assertEqual(config.TARGET_LANGUAGE_CODE, "pt")

    def test_save_persists_target_language(self):
        config.PROVIDER = "openai"
        config.TARGET_LANGUAGE_CODE = "ja"
        config.save_user_settings()
        saved = json.loads(
            Path(config._SETTINGS_PATH).read_text(encoding="utf-8"))
        self.assertEqual(saved["TARGET_LANGUAGE_CODE"], "ja")


if __name__ == "__main__":
    unittest.main()
