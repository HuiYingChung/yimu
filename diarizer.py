"""Local speaker diarization for transcript speaker labels.

Runs entirely on this machine — no API calls, no extra cost. A worker
thread consumes the same PCM chunks the translator gets (via the
AudioCapture tap), computes a voice embedding per window with
resemblyzer (GE2E, CPU-friendly), and clusters embeddings online by
cosine similarity: close to an existing speaker centroid -> that
speaker, otherwise a new speaker. The result is a timeline of
(start, end, speaker_id) in time.monotonic() terms that the transcript
recorder queries when it flushes a sentence.

Accuracy is heuristic — good enough to tell 2-3 voices apart in a
meeting, not a biometric. The transcript labels speakers 講者 1/2/…
in order of first appearance.

Requires the optional dependency:  pip install resemblyzer
(pulls PyTorch, ~1-2 GB on disk; first run downloads model weights)
"""

import queue
import threading
import time

import numpy as np

# resemblyzer's GE2E encoder is trained on 16 kHz audio
_ENCODER_RATE = 16000
_WINDOW_S = 1.5          # embedding window
_HOP_S = 0.75            # window hop (50% overlap)
_SIM_THRESHOLD = 0.75    # cosine similarity to join an existing speaker
_MAX_SPEAKERS = 6        # stop inventing new speakers beyond this
_RMS_GATE = 300.0        # int16 RMS below this is treated as silence
_CENTROID_ALPHA = 0.05   # how fast a centroid drifts toward new samples


class DiarizerUnavailable(RuntimeError):
    """resemblyzer (and its PyTorch dependency) is not installed."""


class Diarizer:
    """Online speaker labeling over a PCM chunk stream.

    feed(chunk) is called from the audio capture thread; the heavy
    lifting happens on this object's own worker thread. speaker_at(t)
    is thread-safe and cheap.
    """

    def __init__(self, sample_rate: int):
        try:
            from resemblyzer import VoiceEncoder  # noqa: F401 — probe early
        except ImportError as exc:
            raise DiarizerUnavailable(
                "resemblyzer is not installed"
            ) from exc
        self._rate = sample_rate
        self._chunks: queue.Queue = queue.Queue(maxsize=256)
        self._lock = threading.Lock()
        self._timeline: list[tuple[float, float, int]] = []
        self._centroids: list[np.ndarray] = []
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=3)

    def feed(self, chunk: bytes) -> None:
        """Accept a PCM chunk (int16 mono bytes). Never blocks capture."""
        try:
            self._chunks.put_nowait((time.monotonic(), chunk))
        except queue.Full:
            pass  # diarizer lagging — drop; labels degrade, capture doesn't

    def speaker_at(self, t: float) -> int | None:
        """Speaker id (0-based) active at monotonic time t, or None."""
        with self._lock:
            best = None
            for start, end, spk in reversed(self._timeline):
                if start <= t <= end:
                    return spk
                # fall back to the nearest window within half a window
                if best is None and abs(t - (start + end) / 2) <= _WINDOW_S:
                    best = spk
            return best

    # --- worker thread ---

    def _run(self) -> None:
        from resemblyzer import VoiceEncoder

        encoder = VoiceEncoder("cpu")  # model load takes a few seconds
        window = int(_ENCODER_RATE * _WINDOW_S)
        hop = int(_ENCODER_RATE * _HOP_S)
        buf = np.zeros(0, dtype=np.float32)
        buf_end_t = 0.0  # monotonic time of the last sample in buf

        while not self._stop.is_set():
            try:
                arrived_at, chunk = self._chunks.get(timeout=0.5)
            except queue.Empty:
                continue
            samples = np.frombuffer(chunk, dtype=np.int16)
            if self._rate != _ENCODER_RATE:
                from scipy.signal import resample_poly

                g = np.gcd(self._rate, _ENCODER_RATE)
                samples = resample_poly(
                    samples.astype(np.float32),
                    _ENCODER_RATE // g, self._rate // g)
            buf = np.concatenate([buf, samples.astype(np.float32)])
            buf_end_t = arrived_at

            while len(buf) >= window:
                frame = buf[:window]
                buf = buf[hop:]
                frame_end_t = buf_end_t - len(buf) / _ENCODER_RATE
                self._process(encoder, frame, frame_end_t)

    def _process(self, encoder, frame: np.ndarray, end_t: float) -> None:
        rms = float(np.sqrt(np.mean(frame ** 2)))
        if rms < _RMS_GATE:
            return  # silence/noise — no speaker
        embed = encoder.embed_utterance(frame / 32768.0)
        embed = embed / (np.linalg.norm(embed) or 1.0)
        with self._lock:
            spk = self._assign(embed)
            self._timeline.append((end_t - _WINDOW_S, end_t, spk))
            if len(self._timeline) > 4000:  # ~50 min of speech — cap memory
                del self._timeline[:1000]

    def _assign(self, embed: np.ndarray) -> int:
        """Nearest-centroid online clustering (caller holds the lock)."""
        if self._centroids:
            sims = [float(np.dot(embed, c)) for c in self._centroids]
            best = int(np.argmax(sims))
            if sims[best] >= _SIM_THRESHOLD \
                    or len(self._centroids) >= _MAX_SPEAKERS:
                c = self._centroids[best]
                c = (1 - _CENTROID_ALPHA) * c + _CENTROID_ALPHA * embed
                self._centroids[best] = c / (np.linalg.norm(c) or 1.0)
                return best
        self._centroids.append(embed)
        return len(self._centroids) - 1
