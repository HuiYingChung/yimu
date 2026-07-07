"""Settings panel: provider switch and simple appearance options.

Opened from the subtitle window's right-click menu. Appearance options
(fonts, lines, opacity, width) and the interface language preview live
on the subtitle window as they change; Cancel restores everything and
only Apply persists to settings.json. Provider and capture/recording
toggles still need a backend restart on Apply.

Every text-bearing widget is registered with its strings key so a
language switch can relabel the whole dialog in place.

Layout: labeled sections (engine / translation / source text /
recording / window) so the growing option list stays scannable.
"""

import tkinter as tk
from tkinter import messagebox, ttk

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
        self._width_ratio = tk.DoubleVar(value=config.WINDOW_WIDTH_RATIO)
        self._save_transcript = tk.BooleanVar(value=config.SAVE_TRANSCRIPT)
        self._transcript_content = tk.StringVar(
            value=config.TRANSCRIPT_CONTENT)
        self._speaker_labels = tk.BooleanVar(value=config.SPEAKER_LABELS)
        self._capture_mic = tk.BooleanVar(value=config.CAPTURE_MICROPHONE)
        self._language = tk.StringVar(value=config.UI_LANGUAGE)

        # options that preview live; snapshot originals for Cancel
        self._orig = {
            "WINDOW_ALPHA": config.WINDOW_ALPHA,
            "WINDOW_WIDTH_RATIO": config.WINDOW_WIDTH_RATIO,
            "FONT_SIZE": config.FONT_SIZE,
            "SOURCE_FONT_SIZE": config.SOURCE_FONT_SIZE,
            "MAX_LINES": config.MAX_LINES,
            "SOURCE_MAX_LINES": config.SOURCE_MAX_LINES,
            "SHOW_SOURCE_TEXT": config.SHOW_SOURCE_TEXT,
            "UI_LANGUAGE": config.UI_LANGUAGE,
        }
        self._preview_after: str | None = None
        # (widget, strings-key) pairs so a language switch can relabel
        # the dialog in place
        self._i18n: list = []

        frame = ttk.Frame(top, padding=16)
        frame.grid(sticky="nsew")

        def reg(widget, key):
            self._i18n.append((widget, key))
            return widget

        # --- engine ---
        engine = reg(ttk.LabelFrame(frame, text=t("engine"), padding=8),
                     "engine")
        engine.grid(row=0, column=0, sticky="ew")
        reg(ttk.Radiobutton(
            engine, text=t("engine_gemini"), value="gemini",
            variable=self._provider,
        ), "engine_gemini").grid(row=0, column=0, sticky="w")
        reg(ttk.Radiobutton(
            engine, text=t("engine_openai"), value="openai",
            variable=self._provider,
        ), "engine_openai").grid(row=1, column=0, sticky="w")

        # --- translation subtitles ---
        sub = reg(ttk.LabelFrame(frame, text=t("section_subtitle"),
                                 padding=8), "section_subtitle")
        sub.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        sub.columnconfigure(0, weight=1)
        reg(ttk.Label(sub, text=t("font_size")),
            "font_size").grid(row=0, column=0, sticky="w")
        ttk.Spinbox(
            sub, from_=10, to=32, textvariable=self._font_size, width=5,
        ).grid(row=0, column=1, sticky="e")
        reg(ttk.Label(sub, text=t("lines")),
            "lines").grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Spinbox(
            sub, from_=1, to=10, textvariable=self._max_lines, width=5,
        ).grid(row=1, column=1, sticky="e", pady=(6, 0))

        # --- source text ---
        src = reg(ttk.LabelFrame(frame, text=t("section_source"),
                                 padding=8), "section_source")
        src.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        src.columnconfigure(0, weight=1)
        reg(ttk.Checkbutton(
            src, text=t("show_source"), variable=self._show_source,
        ), "show_source").grid(row=0, column=0, columnspan=2, sticky="w")
        reg(ttk.Label(src, text=t("source_font_size")),
            "source_font_size").grid(row=1, column=0, sticky="w",
                                     pady=(6, 0))
        ttk.Spinbox(
            src, from_=8, to=28, textvariable=self._source_font_size, width=5,
        ).grid(row=1, column=1, sticky="e", pady=(6, 0))
        reg(ttk.Label(src, text=t("source_lines")),
            "source_lines").grid(row=2, column=0, sticky="w", pady=(6, 0))
        ttk.Spinbox(
            src, from_=1, to=5, textvariable=self._source_lines, width=5,
        ).grid(row=2, column=1, sticky="e", pady=(6, 0))

        # --- recording ---
        rec = reg(ttk.LabelFrame(frame, text=t("section_record"),
                                 padding=8), "section_record")
        rec.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        reg(ttk.Checkbutton(
            rec, text=t("save_transcript"), variable=self._save_transcript,
        ), "save_transcript").grid(row=0, column=0, sticky="w")
        content_row = ttk.Frame(rec)
        content_row.grid(row=1, column=0, sticky="w",
                         padx=(18, 0), pady=(2, 0))
        # sub-options that only make sense while the transcript is on;
        # greyed out otherwise (see _update_dependents)
        self._transcript_dependents = []
        for col, (value, key) in enumerate(
                [("both", "ts_both"), ("translation", "ts_translation"),
                 ("source", "ts_source")]):
            radio = reg(ttk.Radiobutton(
                content_row, text=t(key), value=value,
                variable=self._transcript_content,
            ), key)
            radio.grid(row=0, column=col, padx=(0, 8))
            self._transcript_dependents.append(radio)
        speaker_row = ttk.Frame(rec)
        speaker_row.grid(row=2, column=0, sticky="w",
                         padx=(18, 0), pady=(2, 0))
        speaker_check = reg(ttk.Checkbutton(
            speaker_row, text=t("speaker_labels"),
            variable=self._speaker_labels,
        ), "speaker_labels")
        speaker_check.grid(row=0, column=0)
        self._transcript_dependents.append(speaker_check)
        # small help link explaining how speaker labels work
        self._speaker_help = reg(tk.Label(
            speaker_row, text=t("speaker_help_link"),
            fg="#0066cc", cursor="hand2",
            font=("TkDefaultFont", 8, "underline"),
        ), "speaker_help_link")
        self._speaker_help.grid(row=0, column=1, padx=(6, 0))
        self._speaker_help.bind("<Button-1>", self._show_speaker_help)
        reg(ttk.Checkbutton(
            rec, text=t("capture_mic"), variable=self._capture_mic,
        ), "capture_mic").grid(row=3, column=0, sticky="w", pady=(6, 0))

        # --- window ---
        win = reg(ttk.LabelFrame(frame, text=t("section_window"),
                                 padding=8), "section_window")
        win.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        win.columnconfigure(0, weight=1)
        reg(ttk.Label(win, text=t("opacity")),
            "opacity").grid(row=0, column=0, sticky="w")
        ttk.Scale(
            win, from_=0.3, to=1.0, variable=self._alpha,
            orient="horizontal", length=140,
            command=lambda _v: self._schedule_preview(),
        ).grid(row=0, column=1, sticky="e")
        reg(ttk.Label(win, text=t("window_width")),
            "window_width").grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Scale(
            win, from_=0.3, to=1.0, variable=self._width_ratio,
            orient="horizontal", length=140,
            command=lambda _v: self._schedule_preview(),
        ).grid(row=1, column=1, sticky="e", pady=(6, 0))

        # --- interface language ---
        lang = ttk.Frame(frame)
        lang.grid(row=5, column=0, sticky="ew", pady=(10, 0))
        lang.columnconfigure(0, weight=1)
        reg(ttk.Label(lang, text=t("ui_language")),
            "ui_language").grid(row=0, column=0, sticky="w")
        # language names always shown in their own language
        ttk.Radiobutton(
            lang, text="English", value="en", variable=self._language,
        ).grid(row=0, column=1, padx=(0, 8))
        ttk.Radiobutton(
            lang, text="中文", value="zh-TW", variable=self._language,
        ).grid(row=0, column=2)

        buttons = ttk.Frame(frame)
        buttons.grid(row=6, column=0, sticky="e", pady=(14, 0))
        reg(ttk.Button(buttons, text=t("cancel"), command=self._cancel),
            "cancel").grid(row=0, column=0, padx=(0, 8))
        reg(ttk.Button(buttons, text=t("apply"), command=self._apply),
            "apply").grid(row=0, column=1)

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
        # closing the dialog (title-bar X) must also undo the preview
        top.protocol("WM_DELETE_WINDOW", self._cancel)

        # text options preview live too (traces fire on every change,
        # including typing — _preview guards partial/invalid input)
        for var in (self._font_size, self._max_lines, self._show_source,
                    self._source_lines, self._source_font_size):
            var.trace_add("write", lambda *_: self._schedule_preview())
        self._language.trace_add(
            "write", lambda *_: self._on_language_change())
        self._save_transcript.trace_add(
            "write", lambda *_: self._update_dependents())
        self._update_dependents()
        window.set_preview(True)  # placeholder text while dialog is open

    def _update_dependents(self) -> None:
        """Grey out transcript sub-options while the transcript is off."""
        on = bool(self._save_transcript.get())
        for widget in self._transcript_dependents:
            widget.state(["!disabled"] if on else ["disabled"])
        self._speaker_help.config(
            state="normal" if on else "disabled",
            cursor="hand2" if on else "arrow")

    def _show_speaker_help(self, _event) -> None:
        if str(self._speaker_help.cget("state")) == "disabled":
            return
        messagebox.showinfo(t("speaker_help_title"),
                            t("speaker_help_body"), parent=self._top)

    def _schedule_preview(self) -> None:
        """Debounce widget changes, then apply to the live window."""
        if self._preview_after is not None:
            self._top.after_cancel(self._preview_after)
        self._preview_after = self._top.after(50, self._preview)

    def _preview(self) -> None:
        self._preview_after = None
        self._pull_appearance()
        self._window.apply_settings()

    def _on_language_change(self) -> None:
        """Relabel the dialog and the subtitle window immediately."""
        config.UI_LANGUAGE = self._language.get()
        self._top.title(t("settings_title"))
        for widget, key in self._i18n:
            widget.config(text=t(key))
        self._window.apply_settings()

    def _pull_appearance(self) -> None:
        """Copy appearance widget values into config (with guards)."""
        config.WINDOW_ALPHA = round(max(0.3, min(1.0, self._alpha.get())), 2)
        config.WINDOW_WIDTH_RATIO = round(
            max(0.3, min(1.0, self._width_ratio.get())), 2)
        config.FONT_SIZE = self._int_or(
            self._font_size, config.FONT_SIZE, 10, 32)
        config.SOURCE_FONT_SIZE = self._int_or(
            self._source_font_size, config.SOURCE_FONT_SIZE, 8, 28)
        config.MAX_LINES = self._int_or(
            self._max_lines, config.MAX_LINES, 1, 10)
        config.SOURCE_MAX_LINES = self._int_or(
            self._source_lines, config.SOURCE_MAX_LINES, 1, 5)
        config.SHOW_SOURCE_TEXT = bool(self._show_source.get())

    def _cancel(self) -> None:
        """Undo any live preview, then close without saving."""
        for name, value in self._orig.items():
            setattr(config, name, value)
        self._window.set_preview(False)
        self._window.apply_settings()
        self._top.destroy()

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
        self._pull_appearance()
        config.SAVE_TRANSCRIPT = bool(self._save_transcript.get())
        # content mode is checked at write time — applies live, no restart
        config.TRANSCRIPT_CONTENT = self._transcript_content.get()
        config.SPEAKER_LABELS = bool(self._speaker_labels.get())
        config.CAPTURE_MICROPHONE = bool(self._capture_mic.get())

        config.save_user_settings()
        self._window.set_preview(False)
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
