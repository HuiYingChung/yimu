"""Settings panel: provider switch and simple appearance options.

Opened from the subtitle window's right-click menu. Applying saves to
settings.json, updates the live window, and restarts the translation
backend when the provider changed. All labels resolve through
strings.t() so the panel follows the interface-language setting.
"""

import tkinter as tk
from tkinter import ttk

import config
from strings import t


class SettingsDialog:
    def __init__(self, root: tk.Tk, window, backend):
        self._window = window
        self._backend = backend

        top = self._top = tk.Toplevel(root)
        top.title(t("settings_title"))
        top.attributes("-topmost", True)
        top.resizable(False, False)

        self._provider = tk.StringVar(value=config.PROVIDER)
        self._font_size = tk.IntVar(value=config.FONT_SIZE)
        self._max_lines = tk.IntVar(value=config.MAX_LINES)
        self._show_source = tk.BooleanVar(value=config.SHOW_SOURCE_TEXT)
        self._alpha = tk.DoubleVar(value=config.WINDOW_ALPHA)
        self._language = tk.StringVar(value=config.UI_LANGUAGE)

        frame = ttk.Frame(top, padding=16)
        frame.grid(sticky="nsew")

        ttk.Label(frame, text=t("engine")).grid(
            row=0, column=0, sticky="w", pady=(0, 2))
        ttk.Radiobutton(
            frame, text=t("engine_gemini"), value="gemini",
            variable=self._provider,
        ).grid(row=1, column=0, columnspan=2, sticky="w")
        ttk.Radiobutton(
            frame, text=t("engine_openai"), value="openai",
            variable=self._provider,
        ).grid(row=2, column=0, columnspan=2, sticky="w")

        ttk.Separator(frame).grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=8)

        ttk.Label(frame, text=t("font_size")).grid(row=4, column=0, sticky="w")
        ttk.Spinbox(
            frame, from_=10, to=32, textvariable=self._font_size, width=5,
        ).grid(row=4, column=1, sticky="e")

        ttk.Label(frame, text=t("lines")).grid(
            row=5, column=0, sticky="w", pady=(6, 0))
        ttk.Spinbox(
            frame, from_=1, to=10, textvariable=self._max_lines, width=5,
        ).grid(row=5, column=1, sticky="e", pady=(6, 0))

        ttk.Checkbutton(
            frame, text=t("show_source"), variable=self._show_source,
        ).grid(row=6, column=0, columnspan=2, sticky="w", pady=(6, 0))

        ttk.Label(frame, text=t("opacity")).grid(
            row=7, column=0, sticky="w", pady=(6, 0))
        ttk.Scale(
            frame, from_=0.3, to=1.0, variable=self._alpha,
            orient="horizontal", length=140,
        ).grid(row=7, column=1, sticky="e", pady=(6, 0))

        ttk.Separator(frame).grid(
            row=8, column=0, columnspan=2, sticky="ew", pady=8)

        ttk.Label(frame, text=t("ui_language")).grid(
            row=9, column=0, sticky="w")
        lang_row = ttk.Frame(frame)
        lang_row.grid(row=9, column=1, sticky="e")
        # language names always shown in their own language
        ttk.Radiobutton(
            lang_row, text="English", value="en", variable=self._language,
        ).grid(row=0, column=0, padx=(0, 8))
        ttk.Radiobutton(
            lang_row, text="中文", value="zh-TW", variable=self._language,
        ).grid(row=0, column=1)

        buttons = ttk.Frame(frame)
        buttons.grid(row=10, column=0, columnspan=2, sticky="e", pady=(14, 0))
        ttk.Button(buttons, text=t("cancel"), command=top.destroy).grid(
            row=0, column=0, padx=(0, 8))
        ttk.Button(buttons, text=t("apply"), command=self._apply).grid(
            row=0, column=1)

        # open next to the subtitle window: the settings and the window
        # they affect should share the same visual context
        top.update_idletasks()
        dw, dh = top.winfo_reqwidth(), top.winfo_reqheight()
        sw, sh = top.winfo_screenwidth(), top.winfo_screenheight()
        try:
            sub = window._root
            wx, wy = sub.winfo_x(), sub.winfo_y()
            ww, wh = sub.winfo_width(), sub.winfo_height()
            x = max(8, min(wx + (ww - dw) // 2, sw - dw - 8))
            if wy > sh // 2:  # subtitle in lower half -> panel above it
                y = max(8, wy - dh - 12)
            else:             # subtitle dragged up high -> panel below it
                y = min(sh - dh - 8, wy + wh + 12)
        except tk.TclError:   # subtitle window gone — fall back to center
            x, y = (sw - dw) // 2, (sh - dh) // 2
        top.geometry(f"+{x}+{y}")
        top.grab_set()

    def _apply(self) -> None:
        provider_changed = self._provider.get() != config.PROVIDER
        config.PROVIDER = self._provider.get()
        config.UI_LANGUAGE = self._language.get()
        try:
            size = int(self._font_size.get())
        except (tk.TclError, ValueError):
            size = config.FONT_SIZE  # keep current on garbage input
        config.FONT_SIZE = max(10, min(32, size))
        try:
            lines = int(self._max_lines.get())
        except (tk.TclError, ValueError):
            lines = config.MAX_LINES
        config.MAX_LINES = max(1, min(10, lines))
        config.SHOW_SOURCE_TEXT = bool(self._show_source.get())
        config.WINDOW_ALPHA = round(max(0.3, min(1.0, self._alpha.get())), 2)

        config.save_user_settings()
        self._window.apply_settings()
        self._top.destroy()
        if provider_changed and self._backend is not None:
            self._window.push_status(
                t("switching_engine", provider=config.PROVIDER))
            self._backend.restart()
