"""Gemini Live translation session (the default engine).

Interface: PCM chunks in via asyncio.Queue, translated text out via
callback. Keep this contract stable — every engine implements it in
its own module (see translator_openai.py) and main.py picks one via
config.PROVIDER.

Run standalone to test:  python translator.py
(plays nothing itself — start an English video, Chinese deltas print
to the terminal)
"""

import asyncio
import re
import sys
import traceback

from google import genai
from google.genai import types

import config

# Errors that retrying will not fix — stop instead of reconnect-looping.
_FATAL_MARKERS = (
    "API_KEY_INVALID",
    "API key not valid",
    "PERMISSION_DENIED",
    "UNAUTHENTICATED",
)


class FatalTranslatorError(RuntimeError):
    """Unrecoverable error (bad API key, no permission)."""


# Keep only letters, digits and CJK so half/full-width punctuation and
# spacing differences don't break echo comparison.
_NORM_RE = re.compile(r"[^0-9a-z一-鿿]+")


def _normalize(text: str) -> str:
    return _NORM_RE.sub("", text.lower())


class Translator:
    """Streams audio chunks to Gemini Live, emits translation deltas.

    on_text(str):        incremental zh-Hant translation text (delta)
    on_source_text(str): incremental source-language transcription (optional)
    on_status(str):      human-readable connection status for the UI
    """

    def __init__(self, audio_queue: asyncio.Queue, on_text,
                 on_source_text=None, on_status=None):
        self._queue = audio_queue
        self._on_text = on_text
        self._on_source_text = on_source_text
        self._on_status = on_status or (lambda msg: None)
        self._got_message = False
        self._recent_input = ""

    async def run(self) -> None:
        """Session loop: connect, stream, reconnect with backoff on drop."""
        delay = config.RECONNECT_BASE_DELAY_S
        while True:
            self._got_message = False
            try:
                await self._run_session()
                # server closed the session normally (time limit) — reconnect
                self._on_status("session ended, reconnecting...")
                delay = config.RECONNECT_BASE_DELAY_S
            except FatalTranslatorError:
                raise
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                traceback.print_exc(file=sys.stderr)
                message = str(exc)
                if any(marker in message for marker in _FATAL_MARKERS):
                    raise FatalTranslatorError(
                        "Gemini rejected the API key. Check GEMINI_API_KEY "
                        f"in .env ({message[:120]})"
                    ) from exc
                if self._got_message:
                    delay = config.RECONNECT_BASE_DELAY_S
                if "429" in message or "RESOURCE_EXHAUSTED" in message:
                    self._on_status(
                        f"rate limited (429), retrying in {delay:.0f}s..."
                    )
                else:
                    self._on_status(
                        f"connection lost, retrying in {delay:.0f}s..."
                    )
                await asyncio.sleep(delay)
                delay = min(delay * 2, config.RECONNECT_MAX_DELAY_S)

    async def _run_session(self) -> None:
        client = genai.Client()  # reads GEMINI_API_KEY from environment
        live_config = types.LiveConnectConfig(
            # The translate model only supports AUDIO responses; subtitles
            # come from the transcription streams. Received audio is dropped.
            response_modalities=["AUDIO"],
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            translation_config=types.TranslationConfig(
                target_language_code=config.TARGET_LANGUAGE_CODE,
                echo_target_language=config.ECHO_TARGET_LANGUAGE,
            ),
        )
        async with client.aio.live.connect(
            model=config.MODEL_NAME, config=live_config
        ) as session:
            self._on_status("connected")
            async with asyncio.TaskGroup() as tg:
                tg.create_task(self._sender(session))
                tg.create_task(self._receiver(session))

    async def _sender(self, session) -> None:
        while True:
            chunk = await self._queue.get()
            if isinstance(chunk, Exception):
                # audio capture thread died — nothing to translate anymore
                raise FatalTranslatorError(
                    f"audio capture failed: {chunk}"
                ) from chunk
            await session.send_realtime_input(
                audio=types.Blob(
                    data=chunk,
                    mime_type=f"audio/pcm;rate={config.TARGET_SAMPLE_RATE}",
                )
            )

    async def _receiver(self, session) -> None:
        async for response in session.receive():
            self._got_message = True
            content = response.server_content
            if content is None:
                continue
            src = content.input_transcription
            if src is not None and src.text:
                self._recent_input = (self._recent_input
                                      + _normalize(src.text))[-300:]
                if self._on_source_text:
                    self._on_source_text(src.text)
            out = content.output_transcription
            if out is not None and out.text and not self._is_echo(out.text):
                self._on_text(out.text)
            # content.model_turn audio parts are intentionally discarded
        # receive() ending means the server closed the session
        raise ConnectionError("Live session closed by server")

    def _is_echo(self, delta: str) -> bool:
        """True when the output delta just repeats the source speech.

        With echo_target_language=False the model stays silent in AUDIO
        for target-language input, but output_transcription still streams
        the input verbatim (verified 2026-07 against the live API) — so
        subtitles must drop deltas already present in the recent input.
        """
        norm = _normalize(delta)
        return bool(norm) and norm in self._recent_input


async def _standalone() -> None:
    """Acceptance test: capture system audio, print deltas to terminal."""
    from dotenv import load_dotenv

    from audio_capture import AudioCapture

    # Windows consoles often default to cp1252, which cannot print Chinese
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    load_dotenv()
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()
    capture = AudioCapture(loop, queue)
    capture.start()
    print("Capturing system audio — play an English video now. Ctrl+C quits.")

    def show_text(delta: str) -> None:
        print(delta, end="", flush=True)

    translator = Translator(
        queue,
        on_text=show_text,
        on_status=lambda msg: print(f"\n[status] {msg}"),
    )
    try:
        await translator.run()
    finally:
        capture.stop()


if __name__ == "__main__":
    try:
        asyncio.run(_standalone())
    except KeyboardInterrupt:
        print("\nstopped")
