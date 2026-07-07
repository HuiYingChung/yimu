# Yimu 譯幕 — Live Translated Subtitles for Your Desktop

> 繁體中文文件：[README.zh-TW.md](README.zh-TW.md)

**Yimu** captures whatever your Windows machine is playing — YouTube,
online meetings, livestreams, podcasts — and shows live **Traditional
Chinese** subtitles in a floating window. Translation is speech-native
(the audio stream goes straight into a translation model), so no
caption track is needed and no platform is off-limits.

- Dual engines, switchable in-app: **Gemini Live** (free tier) or
  **OpenAI gpt-realtime-translate** (metered)
- Localized for Taiwan: OpenAI's Simplified-only output is converted
  client-side with OpenCC (Taiwan phrasing — 人工智慧, not 人工智能)
- Single-user, local-first: no server, no account, keys stay in a
  local `.env`
- Windows only (audio capture uses WASAPI loopback)
- Subtitles only — the translated audio is discarded, and the window
  stays quiet when the source is already Chinese
- **Meeting-ready**: optional Markdown transcripts (saved to
  Downloads), local speaker labels, and microphone mixing so your own
  voice makes it into the record

The full design story is in the
[case study](https://www.huiyingchung.com/yimu-case-study.html).

## Install

Requires Python 3.11+.

```
pip install -r requirements.txt
```

Optional — only if you want speaker labels in transcripts (pulls
PyTorch, ~1–2 GB):

```
pip install resemblyzer
```

## API keys

Copy `.env.example` to `.env`, then fill in the key(s) for the
engine(s) you plan to use:

**Gemini (default engine, free tier)**
1. Open [Google AI Studio](https://aistudio.google.com/apikey) and
   sign in with a Google account.
2. Click "Create API key" and paste it into `.env`:
   `GEMINI_API_KEY=...`

The free tier is rate-limited but generally enough for personal use;
when the limit hits, the subtitle window shows a 429 status and
retries with backoff.

**OpenAI (optional second engine, metered)**
1. Create a key at [platform.openai.com](https://platform.openai.com/api-keys)
   (requires a funded API account).
2. Paste it into `.env`: `OPENAI_API_KEY=...`

Billing is by audio duration — roughly **$0.034/minute (~$2/hour)**.
The settings panel repeats this price next to the engine switch, on
purpose.

## Run

```
python main.py
```

Or double-click `start_translator.bat` (no console window; the
desktop shortcut "譯幕 Yimu" points to it).

- The subtitle window appears bottom-center: always on top,
  semi-transparent, black bar with white text.
- Play anything in English (or most other languages) — Chinese
  subtitles appear within 2–3 seconds.
- **Drag** anywhere on the window to move it.
- **Settings**: right-click → 設定….
- **Quit**: press `Esc`, or right-click → 結束.

## Settings panel

Right-click → 設定…. Appearance options **preview live** as you change
them (an empty window shows placeholder text while the dialog is
open); Cancel undoes the preview, Apply persists to `settings.json`
(delete the file to reset). Options are grouped into sections:

- **Engine** — Gemini (default, free) / OpenAI (metered; needs
  `OPENAI_API_KEY`). Switching reconnects in place, no restart.
- **Translation** — font size (10–32 pt) and lines shown (1–10; the
  window height follows automatically).
- **Source text** — show the source-language transcription above the
  translation, with its own font size and line count (greyed out
  while the toggle is off).
- **Recording** — save a timestamped Markdown transcript to your
  Downloads folder (content: both / translation only / source only;
  in "both" the translation is blockquoted under its source line).
  **Label speakers** marks voice changes as 講者 1/2/… headings —
  local, free, heuristic; needs the optional `resemblyzer` install
  (a "how it works" link next to the option explains the details).
  **Capture microphone** mixes your mic into the stream so meetings
  include your side — wear headphones to avoid echo. No extra API
  cost: billing is by duration, not loudness.
- **Window** — opacity (30–100%) and window width (30–100% of the
  screen), both with live preview.
- **Interface language** — English (default) / 中文, switches the UI
  instantly. Subtitle output is always Traditional Chinese.

Advanced defaults (target language, transcript folder, etc.) live in
`config.py`.

## FAQ

**No subtitles appearing?**
- Check that audio is playing through the **default output device** —
  the tool only captures the default speakers/headphones. Restart the
  app after switching devices.
- Check the console/status line for errors (an invalid key or a
  missing loopback device is reported in plain language).

**429 / rate limited?**
The free quota is exhausted; the tool backs off and reconnects
automatically. Wait a bit, or check your quota in AI Studio.

**No subtitles on Chinese content?**
Expected: the translator stays silent when the source is already
Chinese (`ECHO_TARGET_LANGUAGE = False` in `config.py`).

**Model name stopped working?**
Both models are current as of mid-2026 and may be renamed. Check the
[Gemini live-translation docs](https://ai.google.dev/gemini-api/docs/live-api/live-translate)
or OpenAI's realtime translation docs, then update `MODEL_NAME` /
`OPENAI_MODEL_NAME` in `config.py`.

## Architecture

```
audio_capture.py      WASAPI loopback → mono PCM chunks at the engine's
                      rate (16 kHz Gemini / 24 kHz OpenAI) → asyncio.Queue;
                      optional mic mixing (mic-clocked, so silent loopback
                      can't stall the stream)
translator.py         Gemini Live session — audio queue in, text deltas out
translator_openai.py  OpenAI gpt-realtime-translate over WebSocket
                      (same contract; OpenCC Traditional-Chinese layer,
                      echo filter, capped silence tail)
transcript.py         sentence-level Markdown transcript writer
                      (timestamps, content modes, speaker headings)
diarizer.py           optional local speaker labeling (resemblyzer
                      embeddings + online cosine clustering)
subtitle_ui.py        tkinter floating subtitle window (topmost, draggable,
                      live-preview placeholders)
settings_ui.py        sectioned settings panel with live preview and
                      in-place language switching
main.py               tkinter main thread + restartable asyncio Backend
config.py             defaults + settings.json load/save
```

Each engine is one module behind one contract — audio queue in, text
callback out. Adding an engine means adding a module.

---

Built in collaboration with AI; the design decisions, content, and
direction are mine.
