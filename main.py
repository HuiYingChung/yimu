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
from translator import FatalTranslatorError, Translator


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

    translator = Translator(
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
    if not os.environ.get("GEMINI_API_KEY"):
        _fail_startup(
            "GEMINI_API_KEY 未設定。\n\n"
            "1. 到 https://aistudio.google.com/apikey 取得免費 key\n"
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
