"""Realtime subtitle translator entry point.

Wires the pipeline: system audio capture -> translation provider ->
floating subtitle window. tkinter owns the main thread; the asyncio
pipeline runs on a daemon thread (Backend) and can be restarted when
the user switches provider in the settings panel.

Usage: python main.py  (needs the provider's API key in .env)
"""

import asyncio
import os
import sys
import threading
import tkinter as tk
from tkinter import messagebox

from dotenv import load_dotenv

import config
from audio_capture import AudioCapture
from strings import t
from subtitle_ui import SubtitleWindow
from translator import FatalTranslatorError

# provider -> (translator module name, required .env key)
_PROVIDERS = {
    "gemini": ("translator", "GEMINI_API_KEY"),
    "openai": ("translator_openai", "OPENAI_API_KEY"),
}


def _translator_class():
    import importlib

    module_name, _ = _PROVIDERS[config.PROVIDER]
    return importlib.import_module(module_name).Translator


def _fail_startup(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("譯幕 Yimu", message)
    sys.exit(1)


class Backend:
    """Owns the asyncio pipeline thread. Restartable for provider switch."""

    def __init__(self, window: SubtitleWindow):
        self._window = window
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._loop is not None and self._task is not None:
            try:
                self._loop.call_soon_threadsafe(self._task.cancel)
            except RuntimeError:
                pass  # loop already closed (pipeline died on its own)
        if self._thread is not None:
            self._thread.join(timeout=5)
        self._loop = self._task = self._thread = None

    def restart(self) -> None:
        self.stop()
        self.start()

    def _run(self) -> None:
        try:
            asyncio.run(self._pipeline())
        except asyncio.CancelledError:
            pass  # normal shutdown via stop()
        except FatalTranslatorError as exc:
            # unrecoverable: leave the message on screen, don't die silently
            print(f"fatal: {exc}", file=sys.stderr)
            self._window.push_status(t("err_prefix", msg=exc))
        except Exception as exc:  # noqa: BLE001 — last-resort surface
            print(f"unexpected error: {exc}", file=sys.stderr)
            self._window.push_status(t("err_unexpected", msg=exc))

    async def _pipeline(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._task = asyncio.current_task()
        translator_cls = _translator_class()
        queue: asyncio.Queue = asyncio.Queue()

        # optional local speaker labeling (no API cost, heuristic)
        diarizer = None
        if config.SAVE_TRANSCRIPT and config.SPEAKER_LABELS:
            try:
                from diarizer import Diarizer

                diarizer = Diarizer(translator_cls.SAMPLE_RATE)
                diarizer.start()
            except Exception as exc:  # noqa: BLE001 — feature is optional
                print(f"speaker labels disabled: {exc}", file=sys.stderr)
                self._window.push_status(t("err_diarizer"))
                diarizer = None

        capture = AudioCapture(
            self._loop, queue,
            sample_rate=translator_cls.SAMPLE_RATE,
            tap=diarizer.feed if diarizer is not None else None,
        )
        capture.start()
        self._window.push_status(t("listening"))

        # transcript recorder taps both text streams before the UI
        recorder = None
        on_text = self._window.push_text
        on_source_text = self._window.push_source_text
        if config.SAVE_TRANSCRIPT:
            from transcript import TranscriptRecorder

            recorder = TranscriptRecorder(
                speaker_lookup=(diarizer.speaker_at
                                if diarizer is not None else None))

            def on_text(delta, _ui=on_text):  # noqa: F811
                recorder.add_translation(delta)
                _ui(delta)

            def on_source_text(delta, _ui=on_source_text):  # noqa: F811
                recorder.add_source(delta)
                _ui(delta)

        translator = translator_cls(
            queue,
            on_text=on_text,
            on_source_text=on_source_text,
            on_status=self._window.push_status,
        )
        try:
            await translator.run()
        finally:
            capture.stop()
            if recorder is not None:
                recorder.close()
            if diarizer is not None:
                diarizer.stop()


def main() -> None:
    load_dotenv()
    if config.PROVIDER not in _PROVIDERS:
        _fail_startup(t("err_bad_provider", value=repr(config.PROVIDER),
                        options=", ".join(_PROVIDERS)))
    env_key = _PROVIDERS[config.PROVIDER][1]
    if not os.environ.get(env_key):
        _fail_startup(t("err_missing_key", key=env_key,
                        provider=repr(config.PROVIDER)))

    root = tk.Tk()
    icon = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "assets", "icon.ico")
    try:
        root.iconbitmap(default=icon)
    except tk.TclError:
        pass  # icon missing/corrupt — cosmetic, keep running

    def open_settings() -> None:
        from settings_ui import SettingsDialog

        SettingsDialog(root, window, backend)

    window = SubtitleWindow(root, on_open_settings=open_settings)
    backend = Backend(window)
    backend.start()
    root.mainloop()


if __name__ == "__main__":
    main()
