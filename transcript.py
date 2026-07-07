"""Transcript recorder: accumulates text deltas into a Markdown file.

Sits between the translator callbacks and the UI (see main.py). Both
streams (source transcription and zh-Hant translation) arrive as
incremental deltas; a segment is flushed to the file when it ends with
sentence punctuation or when no new delta arrived for a pause.

Output: yimu_YYYYMMDD_HHMMSS.md in config.TRANSCRIPT_DIR (default:
the user's Downloads folder).

Lines carry no 原文/譯文 labels — the languages tell themselves apart.
In "both" mode the translation is blockquoted under its source line;
in single-stream modes every line is plain with a timestamp:

    **[14:03:21]** So today we're going to talk about AI.
    > 所以今天我們要談談 AI。

With speaker labels on (config.SPEAKER_LABELS + diarizer.py), a heading
is inserted whenever the voice changes:

    ### 講者 1（14:03:21）

    **[14:03:21]** So today we're going to talk about AI.

Speaker lookups use the source segment's start time; translation lines
lag the audio by a couple of seconds and never switch the heading.

The file is created lazily on the first flush, so enabling the option
without playing audio never leaves empty files behind.
"""

import os
import threading
import time
from datetime import datetime

import config

# config.SENTENCE_ENDINGS is tuned for zh subtitles and lacks the ASCII
# period, but the source stream is usually English — without "." source
# sentences would only ever flush on pause and clump together.
_ENDINGS = tuple(config.SENTENCE_ENDINGS + ".")
# config.TRANSCRIPT_CONTENT values that include each stream; checked at
# write time, so switching in settings applies without a reconnect
_STREAM_MODES = {"source": ("both", "source"),
                 "translation": ("both", "translation")}


class _Segment:
    __slots__ = ("text", "started_at", "last_delta_at")

    def __init__(self):
        self.text = ""
        self.started_at = 0.0
        self.last_delta_at = 0.0


class TranscriptRecorder:
    """Collects deltas from both streams, writes timestamped Markdown.

    speaker_lookup: optional callable(monotonic_time) -> int | None,
    normally Diarizer.speaker_at. When given, speaker headings are
    written on voice changes.

    Thread-safe: callbacks come from the backend thread, close() from
    the tkinter thread on shutdown or provider switch.
    """

    def __init__(self, speaker_lookup=None):
        self._lock = threading.Lock()
        self._segments = {"source": _Segment(), "translation": _Segment()}
        self._file = None
        self._path = None
        self._closed = False
        self._speaker_lookup = speaker_lookup
        self._current_speaker = None

    # --- callbacks (wrap the UI callbacks in main.py) ---

    def add_source(self, delta: str) -> None:
        self._add("source", delta)

    def add_translation(self, delta: str) -> None:
        self._add("translation", delta)

    def _add(self, stream: str, delta: str) -> None:
        if config.TRANSCRIPT_CONTENT not in _STREAM_MODES[stream]:
            return
        now = time.monotonic()
        with self._lock:
            if self._closed:
                return
            # a long-enough pause ends the pending sentence of any stream
            self._flush_stale(now)
            seg = self._segments[stream]
            if not seg.text:
                seg.started_at = now
            seg.text += delta
            seg.last_delta_at = now
            if seg.text.rstrip().endswith(_ENDINGS):
                self._flush(stream)

    # --- lifecycle ---

    def close(self) -> None:
        """Flush pending segments and close the file. Idempotent."""
        with self._lock:
            if self._closed:
                return
            for stream in self._segments:
                self._flush(stream)
            self._closed = True
            if self._file is not None:
                self._file.close()
                self._file = None

    @property
    def path(self) -> str | None:
        """Transcript file path, or None if nothing was written yet."""
        return self._path

    # --- internals (caller holds the lock) ---

    def _flush_stale(self, now: float) -> None:
        for stream, seg in self._segments.items():
            if seg.text and now - seg.last_delta_at >= config.SENTENCE_PAUSE_S:
                self._flush(stream)

    def _flush(self, stream: str) -> None:
        seg = self._segments[stream]
        text = seg.text.strip()
        seg.text = ""
        if not text:
            return
        self._ensure_file()
        clock = datetime.now().strftime("%H:%M:%S")
        # only source lines can switch the speaker: translation text lags
        # the audio, so its timestamps point at the wrong voice. In
        # translation-only mode fall back to translation lines (less
        # accurate timing) so speaker headings still appear.
        heading_stream = ("translation"
                          if config.TRANSCRIPT_CONTENT == "translation"
                          else "source")
        if self._speaker_lookup is not None and stream == heading_stream:
            speaker = self._speaker_lookup(seg.started_at)
            if speaker is not None and speaker != self._current_speaker:
                self._current_speaker = speaker
                self._file.write(f"\n### 講者 {speaker + 1}（{clock}）\n\n")
        # trailing two spaces: Markdown hard line break. In "both" mode
        # the translation is blockquoted under its source line (which
        # already carries the timestamp); otherwise plain + timestamp.
        if stream == "translation" and config.TRANSCRIPT_CONTENT == "both":
            self._file.write(f"> {text}  \n")
        else:
            self._file.write(f"**[{clock}]** {text}  \n")
        self._file.flush()  # crash/kill must not lose the transcript

    def _ensure_file(self) -> None:
        if self._file is not None:
            return
        os.makedirs(config.TRANSCRIPT_DIR, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._path = os.path.join(config.TRANSCRIPT_DIR, f"yimu_{stamp}.md")
        self._file = open(self._path, "a", encoding="utf-8")
        title = datetime.now().strftime("%Y-%m-%d %H:%M")
        self._file.write(f"# 譯幕逐字稿 {title}\n\n")
