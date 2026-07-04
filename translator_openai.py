"""OpenAI gpt-realtime-translate session over WebSocket.

Same contract as translator.Translator: PCM chunks in via
asyncio.Queue, translated text out via callbacks. This engine expects
24 kHz mono PCM16 (Gemini uses 16 kHz — main.py reads SAMPLE_RATE).

Docs: https://developers.openai.com/api/docs/guides/realtime-translation
Run standalone to test:  python translator_openai.py
"""

import asyncio
import base64
import hashlib
import json
import os
import sys
import traceback

import websockets
from opencc import OpenCC

import config
from translator import FatalTranslatorError, _CJK_RE, _leaf_errors, _normalize

# The endpoint only outputs generic 'zh' (Simplified); convert client-side
# to Traditional with Taiwan phrasing so subtitles match the Gemini engine.
_to_traditional = OpenCC("s2twp").convert

_WS_URL = ("wss://api.openai.com/v1/realtime/translations"
           f"?model={config.OPENAI_MODEL_NAME}")


def _openai_language(code: str) -> str:
    """Map our BCP-47 target code to OpenAI's two-letter codes.

    The endpoint only accepts bare ISO 639-1 codes (verified 2026-07:
    'zh-Hant' is rejected, 'zh' is the only Chinese option).
    """
    return code.split("-")[0].lower()

# Errors that retrying will not fix — stop instead of reconnect-looping.
_FATAL_MARKERS = (
    "invalid_api_key",
    "authentication",
    "insufficient_quota",
    "HTTP 401",
    "HTTP 403",
)


class Translator:
    """Streams audio to gpt-realtime-translate, emits translated deltas.

    Same callbacks as the Gemini engine: on_text / on_source_text /
    on_status. Returned audio deltas are intentionally discarded.
    """

    SAMPLE_RATE = 24000  # PCM rate this engine expects from the capture

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
                self._on_status("session ended, reconnecting...")
                delay = config.RECONNECT_BASE_DELAY_S
            except FatalTranslatorError:
                raise
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                traceback.print_exc(file=sys.stderr)
                leaves = _leaf_errors(exc)
                for leaf in leaves:
                    if isinstance(leaf, FatalTranslatorError):
                        raise leaf
                message = " | ".join(str(leaf) for leaf in leaves)
                if any(marker in message for marker in _FATAL_MARKERS):
                    raise FatalTranslatorError(
                        "OpenAI 拒絕了這把 key。檢查 .env 的 OPENAI_API_KEY "
                        f"（{message[:120]}）"
                    ) from exc
                if self._got_message:
                    delay = config.RECONNECT_BASE_DELAY_S
                if "429" in message or "rate_limit" in message:
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
        api_key = os.environ.get("OPENAI_API_KEY", "")
        # stable anonymous id for the single local user, as the docs ask
        safety_id = hashlib.sha256(b"desktop-realtime-translator").hexdigest()
        headers = {
            "Authorization": f"Bearer {api_key}",
            "OpenAI-Safety-Identifier": safety_id,
        }
        async with websockets.connect(
            _WS_URL, additional_headers=headers, max_size=None
        ) as ws:
            await ws.send(json.dumps({
                "type": "session.update",
                "session": {
                    "audio": {
                        "output": {
                            "language": _openai_language(
                                config.TARGET_LANGUAGE_CODE),
                        }
                    }
                },
            }))
            self._on_status("connected")
            async with asyncio.TaskGroup() as tg:
                tg.create_task(self._sender(ws))
                tg.create_task(self._receiver(ws))

    async def _sender(self, ws) -> None:
        while True:
            chunk = await self._queue.get()
            if isinstance(chunk, Exception):
                # audio capture thread died — nothing to translate anymore
                raise FatalTranslatorError(
                    f"audio capture failed: {chunk}"
                ) from chunk
            await ws.send(json.dumps({
                "type": "session.input_audio_buffer.append",
                "audio": base64.b64encode(chunk).decode("ascii"),
            }))

    async def _receiver(self, ws) -> None:
        async for raw in ws:
            self._got_message = True
            event = json.loads(raw)
            kind = event.get("type", "")
            if kind == "session.input_transcript.delta":
                delta = event.get("delta", "")
                if delta:
                    # keep both scripts so echo matching works either way
                    self._recent_input = (
                        self._recent_input + _normalize(delta)
                        + _normalize(_to_traditional(delta))
                    )[-600:]
                    if self._on_source_text:
                        self._on_source_text(delta)
            elif kind == "session.output_transcript.delta":
                delta = event.get("delta", "")
                if delta and not self._is_echo(delta):
                    self._on_text(_to_traditional(delta))
            elif kind == "error":
                raise ConnectionError(
                    f"server error: {json.dumps(event.get('error', event), ensure_ascii=False)[:200]}"
                )
            # session.output_audio.delta is intentionally discarded
        raise ConnectionError("translation session closed by server")

    def _is_echo(self, delta: str) -> bool:
        """Drop output deltas that just repeat the source speech.

        The docs say the model "tries not to translate" same-language
        input but don't promise silent transcripts, so keep the same
        client-side filter the Gemini engine needs. Compared in both
        scripts because the echo may come back Simplified while the
        source transcript is Traditional (or vice versa).
        """
        if not _CJK_RE.search(delta):
            return False  # pure-ASCII deltas can't be echoes of zh input
        norm = _normalize(delta)
        if not norm:
            return False
        return (norm in self._recent_input
                or _normalize(_to_traditional(delta)) in self._recent_input)


async def _standalone() -> None:
    """Acceptance test: capture system audio, print deltas to terminal."""
    from dotenv import load_dotenv

    from audio_capture import AudioCapture

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    load_dotenv()
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()
    capture = AudioCapture(loop, queue, sample_rate=Translator.SAMPLE_RATE)
    capture.start()
    print("Capturing system audio — play an English video now. Ctrl+C quits.")

    translator = Translator(
        queue,
        on_text=lambda d: print(d, end="", flush=True),
        on_status=lambda msg: print(f"\n[status] {msg}", flush=True),
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
