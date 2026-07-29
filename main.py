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
    """Owns the restartable, pausable asyncio translation pipeline."""

    _ACTIVE_STATES = {"starting", "running"}

    def __init__(self, window: SubtitleWindow):
        self._window = window
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._task: asyncio.Task | None = None
        self._state = "stopped"
        self._state_lock = threading.Lock()
        self._stop_requested = threading.Event()
        self._stop_requested.set()

    @property
    def state(self) -> str:
        with self._state_lock:
            return self._state

    @property
    def is_running(self) -> bool:
        return self.state in self._ACTIVE_STATES

    def _set_state(self, state: str, message: str) -> None:
        with self._state_lock:
            self._state = state
        self._window.push_runtime_state(state, message)

    def start(self, message: str | None = None) -> bool:
        """Start or resume translation. Returns False if already active."""
        with self._state_lock:
            if self._state in self._ACTIVE_STATES:
                return False
            if self._thread is not None and self._thread.is_alive():
                return False
            self._state = "starting"
            self._stop_requested.clear()
            thread = threading.Thread(target=self._run, daemon=True)
            self._thread = thread
        self._window.push_runtime_state(
            "starting", message or t("starting_translation"))
        thread.start()
        return True

    def stop(self, final_state: str | None = None) -> bool:
        """Stop capture and translation, optionally publishing a final state."""
        self._stop_requested.set()
        with self._state_lock:
            loop = self._loop
            task = self._task
            thread = self._thread
        if loop is not None and task is not None:
            try:
                loop.call_soon_threadsafe(task.cancel)
            except RuntimeError:
                pass  # loop already closed (pipeline died on its own)
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=5)
            if thread.is_alive():
                self._set_state("error", t("err_stop_timeout"))
                return False
        with self._state_lock:
            if self._thread is thread:
                self._loop = self._task = self._thread = None
            self._state = final_state or "stopped"
        if final_state is not None:
            self._window.push_runtime_state(final_state, t(final_state))
        return True

    def pause(self) -> bool:
        if not self.is_running:
            return False
        return self.stop(final_state="paused")

    def resume(self) -> bool:
        return self.start()

    def toggle(self) -> None:
        if self.is_running:
            self.pause()
        else:
            self.resume()

    def restart(self, message: str | None = None) -> bool:
        """Restart active translation; preserve an intentional pause."""
        if self.state == "paused":
            self._window.push_runtime_state("paused", t("paused"))
            return False
        if not self.stop():
            return False
        return self.start(message)

    def _run(self) -> None:
        failure_message = None
        try:
            asyncio.run(self._pipeline())
        except asyncio.CancelledError:
            pass  # normal shutdown via stop()
        except FatalTranslatorError as exc:
            # unrecoverable: leave the message on screen, don't die silently
            print(f"fatal: {exc}", file=sys.stderr)
            failure_message = t("err_prefix", msg=exc)
        except Exception as exc:  # noqa: BLE001 — last-resort surface
            print(f"unexpected error: {exc}", file=sys.stderr)
            failure_message = t("err_unexpected", msg=exc)
        finally:
            with self._state_lock:
                self._loop = self._task = None
            if failure_message is not None and not self._stop_requested.is_set():
                self._set_state("error", failure_message)
            elif not self._stop_requested.is_set():
                self._set_state("stopped", t("stopped"))

    async def _pipeline(self) -> None:
        with self._state_lock:
            self._loop = asyncio.get_running_loop()
            self._task = asyncio.current_task()
        if self._stop_requested.is_set():
            raise asyncio.CancelledError
        translator_cls = _translator_class()
        queue: asyncio.Queue = asyncio.Queue()

        # optional local speaker labeling (no API cost, heuristic)
        diarizer = None
        capture = None
        recorder = None
        try:
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
            self._set_state("running", t("listening"))

            # transcript recorder taps both text streams before the UI
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
            await translator.run()
        finally:
            if capture is not None:
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

    backend = None

    def open_settings() -> None:
        from settings_ui import SettingsDialog

        SettingsDialog(root, window, backend)

    def toggle_translation() -> None:
        if backend is not None:
            backend.toggle()

    def shutdown() -> None:
        if backend is not None:
            backend.stop()

    window = SubtitleWindow(
        root,
        on_close=shutdown,
        on_open_settings=open_settings,
        on_toggle_translation=toggle_translation,
    )
    backend = Backend(window)
    backend.start()
    root.mainloop()


if __name__ == "__main__":
    main()
