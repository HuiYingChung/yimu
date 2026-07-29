import tkinter as tk
import unittest
from unittest import mock

import config
from languages import language_label
from settings_ui import SettingsDialog


class _WindowStub:
    def __init__(self, root):
        self._root = root

    def apply_settings(self):
        pass

    def set_preview(self, _enabled):
        pass

    def push_status(self, _message):
        pass


class SettingsLanguageUITests(unittest.TestCase):
    def setUp(self):
        self._original_provider = config.PROVIDER
        self._original_target = config.TARGET_LANGUAGE_CODE
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk unavailable: {exc}")
        self.root.withdraw()
        self.dialog = SettingsDialog(
            self.root, _WindowStub(self.root), backend=None)

    def tearDown(self):
        if hasattr(self, "dialog"):
            try:
                if self.dialog._top.winfo_exists():
                    self.dialog._cancel()
            except tk.TclError:
                pass
        if hasattr(self, "root"):
            self.root.destroy()
        config.PROVIDER = self._original_provider
        config.TARGET_LANGUAGE_CODE = self._original_target

    def test_provider_switch_updates_target_choices_without_losing_common_code(
            self):
        self.assertGreaterEqual(
            len(self.dialog._target_combo.cget("values")), 70)

        japanese = language_label("ja", config.UI_LANGUAGE)
        self.dialog._target_language.set(japanese)
        self.dialog._provider.set("openai")
        self.root.update_idletasks()

        self.assertEqual(
            len(self.dialog._target_combo.cget("values")), 13)
        self.assertEqual(self.dialog._selected_target_code(), "ja")

    def test_provider_switch_falls_back_from_unsupported_target(self):
        polish = language_label("pl", config.UI_LANGUAGE)
        self.dialog._target_language.set(polish)
        self.dialog._provider.set("openai")
        self.root.update_idletasks()

        self.assertEqual(
            self.dialog._selected_target_code(), "zh-Hant")

    def test_apply_persists_target_and_restarts_pipeline(self):
        backend = mock.Mock()
        self.dialog._backend = backend
        self.dialog._provider.set("openai")
        self.dialog._target_language.set(
            language_label("ja", config.UI_LANGUAGE))

        with mock.patch.object(config, "save_user_settings") as save:
            self.dialog._apply()

        self.assertEqual(config.PROVIDER, "openai")
        self.assertEqual(config.TARGET_LANGUAGE_CODE, "ja")
        save.assert_called_once_with()
        backend.restart.assert_called_once()
        self.assertIn("openai", backend.restart.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
