"""Floating always-on-top subtitle window (tkinter).

tkinter runs on the main thread; translation deltas arrive from any
thread via thread-safe push_text()/push_status(), polled with
root.after(). Run standalone for a visual demo:  python subtitle_ui.py
"""

import queue
import time
import tkinter as tk
from collections import deque

import config

_POLL_MS = 50


class SubtitleWindow:
    """Borderless topmost subtitle overlay at the bottom of the screen.

    Deltas accumulate into the current line; the line is committed when
    it ends with a sentence-ending character or after a pause of
    config.SENTENCE_PAUSE_S without new text. Drag to move, Esc or
    right-click menu to quit.
    """

    def __init__(self, root: tk.Tk, on_close=None):
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

        self._source_label = None
        if config.SHOW_SOURCE_TEXT:
            self._source_label = tk.Label(
                root, text="", font=(config.FONT_FAMILY, config.FONT_SIZE - 8),
                fg="#bbbbbb", bg="black", justify="left", anchor="w",
                wraplength=self._width - 24,
            )
            self._source_label.pack(fill="x", padx=12)
            self._source_current = ""

        self._label = tk.Label(
            root, text="等待聲音…", font=(config.FONT_FAMILY, config.FONT_SIZE),
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
        self._menu.add_command(label="結束", command=self.close)

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
            elif kind == "source" and self._source_label is not None:
                self._source_current = (
                    self._source_current + payload
                )[-120:]
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

    def _commit_line(self) -> None:
        if self._current.strip():
            self._lines.append(self._current.strip())
        self._current = ""
        if self._source_label is not None:
            self._source_current = ""
            self._source_label.config(text="")

    def _render(self) -> None:
        shown = list(self._lines)
        if self._current:
            shown.append(self._current)
        shown = shown[-config.MAX_LINES:]
        self._label.config(text="\n".join(shown) or " ")

    def _reposition(self) -> None:
        """Keep the window bottom-centered as its height changes.

        Called from the <Configure> handler, so it must not set the same
        geometry twice — that would re-fire <Configure> in an endless loop.
        """
        if self._moved_by_user:
            return
        h = self._root.winfo_reqheight()
        x = (self._root.winfo_screenwidth() - self._width) // 2
        y = self._root.winfo_screenheight() - config.WINDOW_BOTTOM_MARGIN - h
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

    root = tk.Tk()
    window = SubtitleWindow(root)

    script = [
        (0.5, "status", "connected"),
        (0.5, "text", "大家早安，"),
        (0.4, "text", "歡迎來到"),
        (0.4, "text", "今天的簡報。"),
        (0.8, "text", "人工智慧現在"),
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
            else:
                window.push_status(payload)

    threading.Thread(target=feed, daemon=True).start()
    root.mainloop()


if __name__ == "__main__":
    _demo()
