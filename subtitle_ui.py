"""Floating always-on-top subtitle window (tkinter).

tkinter runs on the main thread; translation deltas arrive from any
thread via the thread-safe push_* methods, polled with root.after().
Run standalone for a visual demo:  python subtitle_ui.py
"""

import queue
import time
import tkinter as tk
import tkinter.font as tkfont
from collections import deque

import config
from strings import t

_POLL_MS = 50


class SubtitleWindow:
    """Borderless topmost subtitle overlay at the bottom of the screen.

    Deltas accumulate into the current line; the line is committed when
    it ends with a sentence-ending character or after a pause of
    config.SENTENCE_PAUSE_S without new text. Drag to move; the
    right-click menu opens settings (when wired) and quits; Esc quits.
    """

    def __init__(self, root: tk.Tk, on_close=None, on_open_settings=None,
                 on_toggle_translation=None, on_finish_session=None,
                 on_summarize_last=None):
        self._root = root
        self._on_close = on_close
        self._on_toggle_translation = on_toggle_translation
        self._on_finish_session = on_finish_session
        self._on_summarize_last = on_summarize_last
        self._text_queue: queue.Queue = queue.Queue()
        self._lines: deque[str] = deque(maxlen=config.MAX_LINES)
        self._current = ""
        self._last_text_time = 0.0
        self._drag_offset = (0, 0)
        self._runtime_state = "stopped"
        self._summary_available = False

        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.attributes("-alpha", config.WINDOW_ALPHA)
        root.configure(bg="black")

        screen_w = root.winfo_screenwidth()
        self._width = int(screen_w * config.WINDOW_WIDTH_RATIO)

        self._status_bar = tk.Frame(root, bg="black")
        self._status_bar.pack(fill="x", padx=10, pady=(3, 0))
        self._status_dot = tk.Label(
            self._status_bar, text="●", font=(config.FONT_FAMILY, 9),
            fg="#888888", bg="black",
        )
        self._status_dot.pack(side="left")
        self._status_label = tk.Label(
            self._status_bar, text=t("stopped"),
            font=(config.FONT_FAMILY, 10),
            fg="#aaaaaa", bg="black", anchor="w",
        )
        self._status_label.pack(side="left", fill="x", expand=True, padx=(4, 8))
        self._toggle_button = None
        if on_toggle_translation is not None:
            self._toggle_button = tk.Button(
                self._status_bar,
                text=t("action_start"),
                command=on_toggle_translation,
                font=(config.FONT_FAMILY, 9),
                fg="#eeeeee",
                bg="#333333",
                activeforeground="white",
                activebackground="#4a4a4a",
                relief="flat",
                bd=0,
                padx=8,
                pady=1,
                cursor="hand2",
                takefocus=False,
            )
            self._toggle_button.pack(side="right")
        self._finish_button = None
        if on_finish_session is not None:
            self._finish_button = tk.Button(
                self._status_bar,
                text=t("action_finish"),
                command=on_finish_session,
                font=(config.FONT_FAMILY, 9),
                fg="#eeeeee",
                bg="#333333",
                activeforeground="white",
                activebackground="#4a4a4a",
                disabledforeground="#777777",
                relief="flat",
                bd=0,
                padx=8,
                pady=1,
                cursor="hand2",
                takefocus=False,
                state="disabled",
            )
            self._finish_button.pack(side="right", padx=(0, 5))

        self._source_current = ""
        # Font object (not a tuple) so _trim_source can measure pixel widths
        self._source_font = tkfont.Font(
            family=config.FONT_FAMILY, size=config.SOURCE_FONT_SIZE)
        self._source_label = tk.Label(
            root, text="", font=self._source_font,
            fg="#bbbbbb", bg="black", justify="left", anchor="w",
            wraplength=self._width - 24,
        )
        if config.SHOW_SOURCE_TEXT:
            self._source_label.pack(fill="x", padx=12)

        self._label = tk.Label(
            root, text=t("waiting"), font=(config.FONT_FAMILY, config.FONT_SIZE),
            fg="white", bg="black", justify="left", anchor="w",
            wraplength=self._width - 24,
        )
        self._label.pack(fill="x", padx=12, pady=(0, 8))

        root.bind("<Escape>", lambda e: self.close())
        root.bind("<Button-3>", self._show_menu)
        root.bind("<Button-1>", self._drag_start)
        root.bind("<B1-Motion>", self._drag_move)
        root.bind("<Configure>", lambda e: self._reposition())

        self._menu = tk.Menu(root, tearoff=0)
        self._menu_toggle_index = None
        self._menu_finish_index = None
        self._menu_summary_index = None
        has_session_actions = False
        if on_toggle_translation is not None:
            self._menu.add_command(label=t("action_start"),
                                   command=on_toggle_translation)
            self._menu_toggle_index = self._menu.index("end")
            has_session_actions = True
        if on_finish_session is not None:
            self._menu.add_command(
                label=t("action_finish"),
                command=on_finish_session,
                state="disabled",
            )
            self._menu_finish_index = self._menu.index("end")
            has_session_actions = True
        if on_summarize_last is not None:
            self._menu.add_command(
                label=t("menu_summarize_last"),
                command=on_summarize_last,
                state="disabled",
            )
            self._menu_summary_index = self._menu.index("end")
            has_session_actions = True
        if has_session_actions:
            self._menu.add_separator()
        self._menu_has_settings = on_open_settings is not None
        self._menu_settings_index = None
        if self._menu_has_settings:
            self._menu.add_command(label=t("menu_settings"),
                                   command=on_open_settings)
            self._menu_settings_index = self._menu.index("end")
        self._menu.add_command(label=t("menu_quit"), command=self.close)
        self._menu_quit_index = self._menu.index("end")

        self._moved_by_user = False
        self._last_geometry = ""
        self._preview_on = False  # settings open: show placeholder text
        self._after_id = root.after(_POLL_MS, self._poll)
        self._reposition()

    # --- thread-safe input ---

    def push_text(self, delta: str) -> None:
        """Append a translation delta (callable from any thread)."""
        self._text_queue.put(("text", delta))

    def push_source_text(self, delta: str) -> None:
        self._text_queue.put(("source", delta))

    def push_status(self, message: str) -> None:
        self._text_queue.put(("status", message))

    def push_runtime_state(self, state: str, message: str) -> None:
        """Update control state and status text from any thread."""
        self._text_queue.put(("runtime", (state, message)))

    def push_main_thread(self, callback) -> None:
        """Schedule a callback through the same thread-safe UI queue."""
        self._text_queue.put(("callback", callback))

    # --- main-thread machinery ---

    def close(self) -> None:
        self._root.after_cancel(self._after_id)
        if self._on_close is not None:
            self._on_close()
        self._root.destroy()

    def _poll(self) -> None:
        changed = False
        while True:
            try:
                kind, payload = self._text_queue.get_nowait()
            except queue.Empty:
                break
            changed = True
            if kind == "text":
                self._append_delta(payload)
            elif kind == "source" and config.SHOW_SOURCE_TEXT:
                self._source_current = self._trim_source(
                    self._source_current + payload)
                self._source_label.config(text=self._source_current)
            elif kind == "status":
                self._status_label.config(text=payload)
            elif kind == "runtime":
                state, message = payload
                self._apply_runtime_state(state, message)
            elif kind == "callback":
                payload()
        # pause timeout: commit the current line so old text stops growing
        if (self._current
                and time.monotonic() - self._last_text_time
                > config.SENTENCE_PAUSE_S):
            self._commit_line()
            changed = True
        if changed:
            self._render()
        self._after_id = self._root.after(_POLL_MS, self._poll)

    def _append_delta(self, delta: str) -> None:
        self._last_text_time = time.monotonic()
        for ch in delta:
            self._current += ch
            if ch in config.SENTENCE_ENDINGS:
                self._commit_line()

    def _trim_source(self, text: str) -> str:
        """Drop oldest words until the text fits SOURCE_MAX_LINES.

        The label wraps at word boundaries, so a wrapped line rarely
        uses its full pixel width — budget 90% per line to stay under
        the target even with wrap slack.
        """
        max_px = int((self._width - 24) * config.SOURCE_MAX_LINES * 0.9)
        while text and self._source_font.measure(text) > max_px:
            head, sep, rest = text.partition(" ")
            text = rest if sep else text[1:]
        return text

    def _commit_line(self) -> None:
        # source text is NOT cleared here: it scrolls independently,
        # capped by SOURCE_MAX_LINES in _trim_source — clearing it per
        # committed translation line kept it forever at ~1 line
        if self._current.strip():
            self._lines.append(self._current.strip())
        self._current = ""

    def apply_settings(self) -> None:
        """Re-apply user-adjustable config values to the live window."""
        self._refresh_controls()
        if self._menu_settings_index is not None:
            self._menu.entryconfigure(
                self._menu_settings_index, label=t("menu_settings"))
        self._menu.entryconfigure(
            self._menu_quit_index, label=t("menu_quit"))
        if self._lines.maxlen != config.MAX_LINES:
            # deque capacity is fixed at construction; rebuild, keeping
            # the most recent lines
            self._lines = deque(self._lines, maxlen=config.MAX_LINES)
        self._root.attributes("-alpha", config.WINDOW_ALPHA)
        # width may have changed: resize, and re-wrap both labels to match
        self._width = int(self._root.winfo_screenwidth()
                          * config.WINDOW_WIDTH_RATIO)
        self._label.config(wraplength=self._width - 24)
        self._source_label.config(wraplength=self._width - 24)
        self._label.config(font=(config.FONT_FAMILY, config.FONT_SIZE))
        self._source_font.configure(size=config.SOURCE_FONT_SIZE)
        # font size or line budget may have changed — re-trim what's shown
        self._source_current = self._trim_source(self._source_current)
        self._refresh_source_label()
        if config.SHOW_SOURCE_TEXT:
            if not self._source_label.winfo_ismapped():
                self._source_label.pack(fill="x", padx=12,
                                        before=self._label)
        else:
            self._source_label.pack_forget()
        self._render()  # height may have changed; _render repositions

    def _apply_runtime_state(self, state: str, message: str) -> None:
        self._runtime_state = state
        self._status_label.config(text=message)
        self._refresh_controls()

    def _refresh_controls(self) -> None:
        styles = {
            "starting": ("#e7b94f", "action_pause"),
            "running": ("#55c878", "action_pause"),
            "paused": ("#e7b94f", "action_resume"),
            "error": ("#ef6a6a", "action_retry"),
            "stopped": ("#888888", "action_start"),
            "finished": ("#888888", "action_start"),
            "summarizing": ("#a78bfa", "action_start"),
        }
        color, action_key = styles.get(
            self._runtime_state, styles["stopped"])
        self._status_dot.config(fg=color)
        busy = self._runtime_state == "summarizing"
        if self._toggle_button is not None:
            self._toggle_button.config(
                text=t(action_key),
                state="disabled" if busy else "normal",
            )
        if self._menu_toggle_index is not None:
            self._menu.entryconfigure(
                self._menu_toggle_index,
                label=t(action_key),
                state="disabled" if busy else "normal",
            )
        can_finish = self._runtime_state in {
            "starting", "running", "paused", "error",
        }
        if self._finish_button is not None:
            self._finish_button.config(
                text=t("action_finish"),
                state="normal" if can_finish else "disabled",
            )
        if self._menu_finish_index is not None:
            self._menu.entryconfigure(
                self._menu_finish_index,
                label=t("action_finish"),
                state="normal" if can_finish else "disabled",
            )
        if self._menu_summary_index is not None:
            can_summarize = (
                self._summary_available
                and self._runtime_state
                not in {"starting", "running", "summarizing"}
            )
            self._menu.entryconfigure(
                self._menu_summary_index,
                label=t("menu_summarize_last"),
                state="normal" if can_summarize else "disabled",
            )

    def set_summary_available(self, available: bool) -> None:
        """Enable or disable the retry action for the last transcript."""
        self._summary_available = available
        self._refresh_controls()

    def set_preview(self, on: bool) -> None:
        """Placeholder text while the settings dialog is open.

        Live subtitles (if any) stay visible and are used for the
        preview instead; the placeholder only fills an empty window so
        size/line changes are immediately visible.
        """
        self._preview_on = on
        self._refresh_source_label()
        self._render()

    def _refresh_source_label(self) -> None:
        text = self._source_current
        if not text and self._preview_on:
            # repeat the sample until it exceeds the pixel budget, then
            # trim with the same logic as live text, so the placeholder
            # genuinely fills SOURCE_MAX_LINES wrapped lines
            unit = t("preview_source") + " "
            max_px = int((self._width - 24)
                         * config.SOURCE_MAX_LINES * 0.9)
            text = unit
            for _ in range(50):  # hard cap — measure() could misbehave
                if self._source_font.measure(text) > max_px:
                    break
                text += unit
            text = self._trim_source(text)
        self._source_label.config(text=text)

    def _render(self) -> None:
        shown = list(self._lines)
        if self._current:
            shown.append(self._current)
        shown = shown[-config.MAX_LINES:]
        if not shown and self._preview_on:
            # one placeholder per line so "lines shown" is visible too
            shown = [t("preview_line")] * config.MAX_LINES
        # empty means no subtitles yet — show the waiting hint
        self._label.config(text="\n".join(shown) or t("waiting"))
        # explicit geometry() disables auto-sizing, so grow/shrink manually
        self._root.update_idletasks()
        self._reposition()

    def _reposition(self) -> None:
        """Keep the window bottom-centered as its height changes.

        Called from the <Configure> handler, so it must not set the same
        geometry twice — that would re-fire <Configure> in an endless loop.
        """
        h = self._root.winfo_reqheight()
        if self._moved_by_user:
            # keep the user's position, only track the content height
            x, y = self._root.winfo_x(), self._root.winfo_y()
        else:
            x = (self._root.winfo_screenwidth() - self._width) // 2
            y = (self._root.winfo_screenheight()
                 - config.WINDOW_BOTTOM_MARGIN - h)
        geometry = f"{self._width}x{h}+{x}+{y}"
        if geometry != self._last_geometry:
            self._last_geometry = geometry
            self._root.geometry(geometry)

    # --- dragging ---

    def _drag_start(self, event) -> None:
        self._drag_offset = (event.x_root - self._root.winfo_x(),
                             event.y_root - self._root.winfo_y())

    def _drag_move(self, event) -> None:
        self._moved_by_user = True
        x = event.x_root - self._drag_offset[0]
        y = event.y_root - self._drag_offset[1]
        self._root.geometry(f"+{x}+{y}")

    def _show_menu(self, event) -> None:
        self._menu.tk_popup(event.x_root, event.y_root)


def _demo() -> None:
    """Standalone visual demo: feeds scripted deltas from a thread."""
    import threading

    config.SHOW_SOURCE_TEXT = True  # demo always shows the source line
    root = tk.Tk()
    window = SubtitleWindow(root)

    script = [
        (0.5, "status", "connected"),
        (0.3, "source", "Good morning everyone, "),
        (0.2, "text", "大家早安，"),
        (0.3, "source", "and welcome to today's presentation. "),
        (0.4, "text", "歡迎來到"),
        (0.4, "text", "今天的簡報。"),
        (0.5, "source", "Artificial intelligence can now translate "
                        "spoken language in real time, and this long "
                        "sentence keeps growing to exercise the "
                        "SOURCE_MAX_LINES trimming logic. "),
        (0.4, "text", "人工智慧現在"),
        (0.4, "text", "可以即時翻譯口語。"),
        (0.8, "text", "這是第三句，"),
        (0.4, "text", "測試兩行捲動。"),
        (3.0, "text", "停頓超時後的新句子"),
        (2.0, "status", "demo done — drag me, press Esc to quit"),
    ]

    def feed() -> None:
        for delay, kind, payload in script:
            time.sleep(delay)
            if kind == "text":
                window.push_text(payload)
            elif kind == "source":
                window.push_source_text(payload)
            else:
                window.push_status(payload)

    threading.Thread(target=feed, daemon=True).start()
    root.mainloop()


if __name__ == "__main__":
    _demo()
