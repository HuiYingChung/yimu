"""Settings panel: provider switch and simple appearance options.

Opened from the subtitle window's right-click menu. Applying saves to
settings.json, updates the live window, and restarts the translation
backend when the provider changed.
"""

import tkinter as tk
from tkinter import ttk

import config


class SettingsDialog:
    def __init__(self, root: tk.Tk, window, backend):
        self._window = window
        self._backend = backend

        top = self._top = tk.Toplevel(root)
        top.title("設定")
        top.attributes("-topmost", True)
        top.resizable(False, False)

        self._provider = tk.StringVar(value=config.PROVIDER)
        self._font_size = tk.IntVar(value=config.FONT_SIZE)
        self._show_source = tk.BooleanVar(value=config.SHOW_SOURCE_TEXT)
        self._alpha = tk.DoubleVar(value=config.WINDOW_ALPHA)

        frame = ttk.Frame(top, padding=16)
        frame.grid(sticky="nsew")

        ttk.Label(frame, text="翻譯引擎").grid(
            row=0, column=0, sticky="w", pady=(0, 2))
        ttk.Radiobutton(
            frame, text="Gemini", value="gemini", variable=self._provider,
        ).grid(row=1, column=0, columnspan=2, sticky="w")
        ttk.Radiobutton(
            frame, text="OpenAI（付費，約 $2/小時）", value="openai",
            variable=self._provider,
        ).grid(row=2, column=0, columnspan=2, sticky="w")

        ttk.Separator(frame).grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=8)

        ttk.Label(frame, text="字級").grid(row=4, column=0, sticky="w")
        ttk.Spinbox(
            frame, from_=10, to=32, textvariable=self._font_size, width=5,
        ).grid(row=4, column=1, sticky="e")

        ttk.Checkbutton(
            frame, text="顯示原文", variable=self._show_source,
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(6, 0))

        ttk.Label(frame, text="透明度").grid(
            row=6, column=0, sticky="w", pady=(6, 0))
        ttk.Scale(
            frame, from_=0.3, to=1.0, variable=self._alpha,
            orient="horizontal", length=140,
        ).grid(row=6, column=1, sticky="e", pady=(6, 0))

        buttons = ttk.Frame(frame)
        buttons.grid(row=7, column=0, columnspan=2, sticky="e", pady=(14, 0))
        ttk.Button(buttons, text="取消", command=top.destroy).grid(
            row=0, column=0, padx=(0, 8))
        ttk.Button(buttons, text="套用", command=self._apply).grid(
            row=0, column=1)

        # center the dialog on the screen, above the subtitle window
        top.update_idletasks()
        x = (top.winfo_screenwidth() - top.winfo_reqwidth()) // 2
        y = (top.winfo_screenheight() - top.winfo_reqheight()) // 2
        top.geometry(f"+{x}+{y}")
        top.grab_set()

    def _apply(self) -> None:
        provider_changed = self._provider.get() != config.PROVIDER
        config.PROVIDER = self._provider.get()
        try:
            size = int(self._font_size.get())
        except (tk.TclError, ValueError):
            size = config.FONT_SIZE  # keep current on garbage input
        config.FONT_SIZE = max(10, min(32, size))
        config.SHOW_SOURCE_TEXT = bool(self._show_source.get())
        config.WINDOW_ALPHA = round(max(0.3, min(1.0, self._alpha.get())), 2)

        config.save_user_settings()
        self._window.apply_settings()
        self._top.destroy()
        if provider_changed and self._backend is not None:
            self._window.push_status(
                f"切換引擎：{config.PROVIDER}，重新連線中…")
            self._backend.restart()
