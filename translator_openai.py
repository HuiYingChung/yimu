"""OpenAI GPT-Realtime-Translate track — placeholder, not implemented.

Keeps the same contract as translator.Translator: PCM chunks in via
asyncio.Queue, text deltas out via callbacks. When implementing, only
this file should need to change (plus OPENAI_* settings in config.py).
"""

import asyncio

from translator import FatalTranslatorError


class Translator:
    """Same interface as the Gemini translator. run() fails clearly."""

    def __init__(self, audio_queue: asyncio.Queue, on_text,
                 on_source_text=None, on_status=None):
        self._queue = audio_queue
        self._on_text = on_text
        self._on_source_text = on_source_text
        self._on_status = on_status or (lambda msg: None)

    async def run(self) -> None:
        raise FatalTranslatorError(
            "OpenAI 翻譯引擎尚未實作。請把 config.py 的 PROVIDER "
            "改回 \"gemini\"。"
        )
