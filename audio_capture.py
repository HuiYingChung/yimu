"""Capture system playback audio via WASAPI loopback as 16 kHz mono PCM.

Chunks of raw 16-bit little-endian PCM (CHUNK_MS each) are pushed into an
asyncio.Queue for the translator. Run standalone to record a 5-second wav
for acceptance testing:  python audio_capture.py
"""

import asyncio
import threading

import numpy as np
import pyaudiowpatch as pyaudio
from scipy.signal import resample_poly

import config

BYTES_PER_SAMPLE = 2  # int16


class LoopbackNotFoundError(RuntimeError):
    """No WASAPI loopback device for the default output could be found."""


def find_default_loopback(p: "pyaudio.PyAudio") -> dict:
    """Return device info for the loopback of the default output device."""
    try:
        return p.get_default_wasapi_loopback()
    except (AttributeError, OSError):
        pass  # older PyAudioWPatch or lookup failure; fall back to scanning
    try:
        wasapi = p.get_host_api_info_by_type(pyaudio.paWASAPI)
        default_out = p.get_device_info_by_index(wasapi["defaultOutputDevice"])
    except OSError as exc:
        raise LoopbackNotFoundError(
            "WASAPI is not available on this system."
        ) from exc
    for dev in p.get_loopback_device_info_generator():
        if default_out["name"] in dev["name"]:
            return dev
    raise LoopbackNotFoundError(
        "No loopback device matches the default output device "
        f"({default_out['name']!r}). Check your default playback device."
    )


class AudioCapture:
    """Reads loopback audio on a background thread and emits PCM chunks.

    Emitted chunks are mono int16 little-endian bytes at sample_rate
    (each engine needs its own: Gemini 16 kHz, OpenAI 24 kHz),
    config.CHUNK_MS milliseconds each.
    """

    def __init__(self, loop: asyncio.AbstractEventLoop, queue: asyncio.Queue,
                 sample_rate: int = config.TARGET_SAMPLE_RATE):
        self._loop = loop
        self._queue = queue
        self._rate = sample_rate
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.device_name = ""

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)

    def _run(self) -> None:
        try:
            self._capture_loop()
        except Exception as exc:  # surface errors instead of dying silently
            self._push(exc)

    def _push(self, item) -> None:
        """Hand an item to the asyncio queue; stop if the loop is gone.

        During a pipeline restart the loop closes while this thread may
        still be mid-read — that's a normal shutdown, not an error.
        """
        try:
            self._loop.call_soon_threadsafe(self._queue.put_nowait, item)
        except RuntimeError:
            self._stop.set()

    def _capture_loop(self) -> None:
        with pyaudio.PyAudio() as p:
            dev = find_default_loopback(p)
            self.device_name = dev["name"]
            rate = int(dev["defaultSampleRate"])
            channels = int(dev["maxInputChannels"])
            native_frames = int(rate * config.CHUNK_MS / 1000)

            with p.open(
                format=pyaudio.paInt16,
                channels=channels,
                rate=rate,
                input=True,
                input_device_index=dev["index"],
                frames_per_buffer=native_frames,
            ) as stream:
                out_bytes_per_chunk = int(
                    self._rate * config.CHUNK_MS / 1000
                ) * BYTES_PER_SAMPLE
                pending = bytearray()
                while not self._stop.is_set():
                    raw = stream.read(native_frames, exception_on_overflow=False)
                    pending.extend(
                        convert_block(raw, channels, rate, self._rate)
                    )
                    while len(pending) >= out_bytes_per_chunk:
                        chunk = bytes(pending[:out_bytes_per_chunk])
                        del pending[:out_bytes_per_chunk]
                        self._push(chunk)


def convert_block(raw: bytes, channels: int, src_rate: int,
                  dst_rate: int) -> bytes:
    """Convert an int16 interleaved block to mono int16 at dst_rate."""
    samples = np.frombuffer(raw, dtype=np.int16)
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
    mono = samples.astype(np.float32)
    if src_rate != dst_rate:
        g = np.gcd(src_rate, dst_rate)
        mono = resample_poly(mono, dst_rate // g, src_rate // g)
    return np.clip(mono, -32768, 32767).astype("<i2").tobytes()


def _record_test_wav(seconds: int = 5, path: str = "capture_test.wav") -> None:
    """Standalone acceptance test: record system audio and save a wav."""
    import wave

    async def record() -> bytes:
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()
        capture = AudioCapture(loop, queue)
        capture.start()
        collected = bytearray()
        target = seconds * config.TARGET_SAMPLE_RATE * BYTES_PER_SAMPLE
        try:
            while len(collected) < target:
                item = await asyncio.wait_for(queue.get(), timeout=10)
                if isinstance(item, Exception):
                    raise item
                collected.extend(item)
                print(f"\rcaptured {len(collected) / target * 100:5.1f}%",
                      end="", flush=True)
        finally:
            capture.stop()
        print(f"\ndevice: {capture.device_name}")
        return bytes(collected)

    data = asyncio.run(record())
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(BYTES_PER_SAMPLE)
        wf.setframerate(config.TARGET_SAMPLE_RATE)
        wf.writeframes(data)
    print(f"saved {seconds}s to {path} — play it back to verify "
          "content, speed, and pitch.")


if __name__ == "__main__":
    print("Recording 5 seconds of system audio... play something now.")
    _record_test_wav()
