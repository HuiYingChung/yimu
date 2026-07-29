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
        self.finish = mock.Mock()
        self.summarize = mock.Mock()
        self.window = SubtitleWindow(
            self.root,
            on_toggle_translation=self.toggle,
            on_finish_session=self.finish,
            on_summarize_last=self.summarize,
        )

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
        self.assertEqual(
            self.window._finish_button.cget("state"), "normal")

    def test_finish_and_summary_actions_follow_session_state(self):
        self.assertEqual(
            self.window._finish_button.cget("state"), "disabled")
        self.window.push_runtime_state("running", t("connected"))
        self.window._poll()
        self.window._finish_button.invoke()
        self.finish.assert_called_once_with()

        self.window.set_summary_available(True)
        self.window.push_runtime_state("finished", t("session_finished"))
        self.window._poll()

        self.assertEqual(
            self.window._menu.entrycget(
                self.window._menu_summary_index, "state"),
            "normal",
        )
        self.window._menu.invoke(self.window._menu_summary_index)
        self.summarize.assert_called_once_with()

    def test_paused_state_offers_resume(self):
        self.window.push_runtime_state("paused", t("paused"))
        self.window._poll()

        self.assertEqual(self.window._status_label.cget("text"), t("paused"))
        self.assertEqual(
            self.window._toggle_button.cget("text"), t("action_resume"))
        self.assertEqual(self.window._status_dot.cget("fg"), "#e7b94f")


if __name__ == "__main__":
    unittest.main()
