import tkinter as tk
import unittest
from unittest import mock

from strings import t
from subtitle_ui import SubtitleWindow


class SubtitleControlTests(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk unavailable: {exc}")
        self.root.withdraw()
        self.toggle = mock.Mock()
        self.window = SubtitleWindow(
            self.root, on_toggle_translation=self.toggle)

    def tearDown(self):
        if hasattr(self, "root"):
            try:
                self.root.destroy()
            except tk.TclError:
                pass

    def test_runtime_state_updates_button_status_and_menu(self):
        self.window.push_runtime_state("running", t("connected"))
        self.window._poll()

        self.assertEqual(self.window._status_label.cget("text"), t("connected"))
        self.assertEqual(
            self.window._toggle_button.cget("text"), t("action_pause"))
        self.assertEqual(
            self.window._menu.entrycget(0, "label"), t("action_pause"))

        self.window._toggle_button.invoke()
        self.toggle.assert_called_once_with()

    def test_paused_state_offers_resume(self):
        self.window.push_runtime_state("paused", t("paused"))
        self.window._poll()

        self.assertEqual(self.window._status_label.cget("text"), t("paused"))
        self.assertEqual(
            self.window._toggle_button.cget("text"), t("action_resume"))
        self.assertEqual(self.window._status_dot.cget("fg"), "#e7b94f")


if __name__ == "__main__":
    unittest.main()
