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

    def __init__(self, root: tk.Tk, on_close=None, on_open_settings=None):
        self._root = root
        self._on_close = on_close
        self._text_queue: queue.Queue = queue.Queue()
        self._lines: deque[str] = deque(maxlen=config.MAX_LINES)
        self._current = ""
        self._last_text_time = 0.0
        self._drag_offset = (0, 0)

        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.attributes("-alpha", config.WINDOW_ALPHA)
        root.configure(bg="black")

        screen_w = root.winfo_screenwidth()
        self._width = int(screen_w * config.WINDOW_WIDTH_RATIO)

        self._status_label = tk.Label(
            root, text="", font=(config.FONT_FAMILY, 10),
            fg="#999999", bg="black", anchor="w",
        )
        self._status_label.pack(fill="x", padx=12, pady=(4, 0))

        self._source_current = ""
        # Font object (not a tuple) so _trim_source can measure pixel widths
        self._source_font = tkfont.Font(
            family=config.FONT_FAMILY, size=config.FONT_SIZE - 6)
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
        self._menu_has_settings = on_open_settings is not None
        if self._menu_has_settings:
            self._menu.add_command(label=t("menu_settings"),
                                   command=on_open_settings)
        self._menu.add_command(label=t("menu_quit"), command=self.close)

        self._moved_by_user = False
        self._last_geometry = ""
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
        if self._menu_has_settings:
            self._menu.entryconfigure(0, label=t("menu_settings"))
            self._menu.entryconfigure(1, label=t("menu_quit"))
        else:
            self._menu.entryconfigure(0, label=t("menu_quit"))
        if self._lines.maxlen != config.MAX_LINES:
            # deque capacity is fixed at construction; rebuild, keeping
            # the most recent lines
            self._lines = deque(self._lines, maxlen=config.MAX_LINES)
        self._root.attributes("-alpha", config.WINDOW_ALPHA)
        self._label.config(font=(config.FONT_FAMILY, config.FONT_SIZE))
        self._source_font.configure(size=config.FONT_SIZE - 6)
        # font size or line budget may have changed — re-trim what's shown
        self._source_current = self._trim_source(self._source_current)
        self._source_label.config(text=self._source_current)
        if config.SHOW_SOURCE_TEXT:
            if not self._source_label.winfo_ismapped():
                self._source_label.pack(fill="x", padx=12,
                                        before=self._label)
        else:
            self._source_label.pack_forget()
        self._render()  # height may have changed; _render repositions

    def _render(self) -> None:
        shown = list(self._lines)
        if self._current:
            shown.append(self._current)
        shown = shown[-config.MAX_LINES:]
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
