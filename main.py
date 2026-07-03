"""Realtime subtitle translator entry point.

Wires the pipeline: system audio capture -> Gemini Live translation ->
floating subtitle window. tkinter owns the main thread; the asyncio
pipeline runs on a daemon thread and feeds the window thread-safely.

Usage: python main.py  (needs GEMINI_API_KEY in .env)
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
    messagebox.showerror("Realtime Subtitle Translator", message)
    sys.exit(1)


async def _pipeline(window: SubtitleWindow) -> None:
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()
    capture = AudioCapture(loop, queue)
    capture.start()
    window.push_status("listening...")

    translator = _translator_class()(
        queue,
        on_text=window.push_text,
        on_source_text=(window.push_source_text
                        if config.SHOW_SOURCE_TEXT else None),
        on_status=window.push_status,
    )
    try:
        await translator.run()
    finally:
        capture.stop()


def _run_backend(window: SubtitleWindow) -> None:
    try:
        asyncio.run(_pipeline(window))
    except FatalTranslatorError as exc:
        # unrecoverable: leave the message on screen instead of dying silently
        print(f"fatal: {exc}", file=sys.stderr)
        window.push_status(f"錯誤：{exc}")
    except Exception as exc:  # noqa: BLE001 — last-resort surface, not a retry
        print(f"unexpected error: {exc}", file=sys.stderr)
        window.push_status(f"未預期的錯誤：{exc}")


def main() -> None:
    load_dotenv()
    if config.PROVIDER not in _PROVIDERS:
        _fail_startup(
            f"config.py 的 PROVIDER 值不合法：{config.PROVIDER!r}。\n"
            f"可用值：{', '.join(_PROVIDERS)}"
        )
    env_key = _PROVIDERS[config.PROVIDER][1]
    if not os.environ.get(env_key):
        _fail_startup(
            f"{env_key} 未設定（PROVIDER = {config.PROVIDER!r}）。\n\n"
            "1. 取得 API key（Gemini：https://aistudio.google.com/apikey）\n"
            "2. 複製 .env.example 為 .env，貼上你的 key\n"
            "3. 重新執行 python main.py"
        )

    root = tk.Tk()
    window = SubtitleWindow(root)  # Esc / right-click menu closes the app;
    threading.Thread(               # backend is a daemon thread, exits with us
        target=_run_backend, args=(window,), daemon=True
    ).start()
    root.mainloop()


if __name__ == "__main__":
    main()
