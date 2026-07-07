"""Settings panel: provider switch and simple appearance options.

Opened from the subtitle window's right-click menu. Applying saves to
settings.json, updates the live window, and restarts the translation
backend when the provider or a capture/recording option changed. All
labels resolve through strings.t() so the panel follows the
interface-language setting.

Layout: labeled sections (engine / subtitles / source text / recording)
so the growing option list stays scannable.
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
        self._source_lines = tk.IntVar(value=config.SOURCE_MAX_LINES)
        self._source_font_size = tk.IntVar(value=config.SOURCE_FONT_SIZE)
        self._alpha = tk.DoubleVar(value=config.WINDOW_ALPHA)
        self._save_transcript = tk.BooleanVar(value=config.SAVE_TRANSCRIPT)
        self._speaker_labels = tk.BooleanVar(value=config.SPEAKER_LABELS)
        self._capture_mic = tk.BooleanVar(value=config.CAPTURE_MICROPHONE)
        self._language = tk.StringVar(value=config.UI_LANGUAGE)

        frame = ttk.Frame(top, padding=16)
        frame.grid(sticky="nsew")

        # --- engine ---
        engine = ttk.LabelFrame(frame, text=t("engine"), padding=8)
        engine.grid(row=0, column=0, sticky="ew")
        ttk.Radiobutton(
            engine, text=t("engine_gemini"), value="gemini",
            variable=self._provider,
        ).grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(
            engine, text=t("engine_openai"), value="openai",
            variable=self._provider,
        ).grid(row=1, column=0, sticky="w")

        # --- subtitles ---
        sub = ttk.LabelFrame(frame, text=t("section_subtitle"), padding=8)
        sub.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        sub.columnconfigure(0, weight=1)
        ttk.Label(sub, text=t("font_size")).grid(row=0, column=0, sticky="w")
        ttk.Spinbox(
            sub, from_=10, to=32, textvariable=self._font_size, width=5,
        ).grid(row=0, column=1, sticky="e")
        ttk.Label(sub, text=t("lines")).grid(
            row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Spinbox(
            sub, from_=1, to=10, textvariable=self._max_lines, width=5,
        ).grid(row=1, column=1, sticky="e", pady=(6, 0))
        ttk.Label(sub, text=t("opacity")).grid(
            row=2, column=0, sticky="w", pady=(6, 0))
        ttk.Scale(
            sub, from_=0.3, to=1.0, variable=self._alpha,
            orient="horizontal", length=140,
        ).grid(row=2, column=1, sticky="e", pady=(6, 0))

        # --- source text ---
        src = ttk.LabelFrame(frame, text=t("section_source"), padding=8)
        src.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        src.columnconfigure(0, weight=1)
        ttk.Checkbutton(
            src, text=t("show_source"), variable=self._show_source,
        ).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(src, text=t("source_font_size")).grid(
            row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Spinbox(
            src, from_=8, to=28, textvariable=self._source_font_size, width=5,
        ).grid(row=1, column=1, sticky="e", pady=(6, 0))
        ttk.Label(src, text=t("source_lines")).grid(
            row=2, column=0, sticky="w", pady=(6, 0))
        ttk.Spinbox(
            src, from_=1, to=5, textvariable=self._source_lines, width=5,
        ).grid(row=2, column=1, sticky="e", pady=(6, 0))

        # --- recording ---
        rec = ttk.LabelFrame(frame, text=t("section_record"), padding=8)
        rec.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        ttk.Checkbutton(
            rec, text=t("save_transcript"), variable=self._save_transcript,
        ).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(
            rec, text=t("speaker_labels"), variable=self._speaker_labels,
        ).grid(row=1, column=0, sticky="w", padx=(18, 0), pady=(2, 0))
        ttk.Checkbutton(
            rec, text=t("capture_mic"), variable=self._capture_mic,
        ).grid(row=2, column=0, sticky="w", pady=(6, 0))

        # --- interface language ---
        lang = ttk.Frame(frame)
        lang.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        lang.columnconfigure(0, weight=1)
        ttk.Label(lang, text=t("ui_language")).grid(row=0, column=0,
                                                    sticky="w")
        # language names always shown in their own language
        ttk.Radiobutton(
            lang, text="English", value="en", variable=self._language,
        ).grid(row=0, column=1, padx=(0, 8))
        ttk.Radiobutton(
            lang, text="中文", value="zh-TW", variable=self._language,
        ).grid(row=0, column=2)

        buttons = ttk.Frame(frame)
        buttons.grid(row=5, column=0, sticky="e", pady=(14, 0))
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
            sub_win = window._root
            wx, wy = sub_win.winfo_x(), sub_win.winfo_y()
            ww, wh = sub_win.winfo_width(), sub_win.winfo_height()
            x = max(8, min(wx + (ww - dw) // 2, sw - dw - 8))
            if wy > sh // 2:  # subtitle in lower half -> panel above it
                y = max(8, wy - dh - 12)
            else:             # subtitle dragged up high -> panel below it
                y = min(sh - dh - 8, wy + wh + 12)
        except tk.TclError:   # subtitle window gone — fall back to center
            x, y = (sw - dw) // 2, (sh - dh) // 2
        top.geometry(f"+{x}+{y}")
        top.grab_set()

    def _int_or(self, var, fallback: int, lo: int, hi: int) -> int:
        try:
            value = int(var.get())
        except (tk.TclError, ValueError):
            return fallback  # keep current on garbage input
        return max(lo, min(hi, value))

    def _apply(self) -> None:
        provider_changed = self._provider.get() != config.PROVIDER
        pipeline_changed = (
            bool(self._save_transcript.get()) != config.SAVE_TRANSCRIPT
            or bool(self._speaker_labels.get()) != config.SPEAKER_LABELS
            or bool(self._capture_mic.get()) != config.CAPTURE_MICROPHONE)
        config.PROVIDER = self._provider.get()
        config.UI_LANGUAGE = self._language.get()
        config.FONT_SIZE = self._int_or(
            self._font_size, config.FONT_SIZE, 10, 32)
        config.SOURCE_FONT_SIZE = self._int_or(
            self._source_font_size, config.SOURCE_FONT_SIZE, 8, 28)
        config.MAX_LINES = self._int_or(
            self._max_lines, config.MAX_LINES, 1, 10)
        config.SOURCE_MAX_LINES = self._int_or(
            self._source_lines, config.SOURCE_MAX_LINES, 1, 5)
        config.SHOW_SOURCE_TEXT = bool(self._show_source.get())
        config.SAVE_TRANSCRIPT = bool(self._save_transcript.get())
        config.SPEAKER_LABELS = bool(self._speaker_labels.get())
        config.CAPTURE_MICROPHONE = bool(self._capture_mic.get())
        config.WINDOW_ALPHA = round(max(0.3, min(1.0, self._alpha.get())), 2)

        config.save_user_settings()
        self._window.apply_settings()
        self._top.destroy()
        # capture/recording options are wired at pipeline start, so both
        # provider switches and those toggles need a backend restart
        if (provider_changed or pipeline_changed) \
                and self._backend is not None:
            if provider_changed:
                self._window.push_status(
                    t("switching_engine", provider=config.PROVIDER))
            elif config.SAVE_TRANSCRIPT:
                self._window.push_status(t("transcript_on"))
            else:
                self._window.push_status(t("reconnecting"))
            self._backend.restart()
