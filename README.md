# Yimu 譯幕 — Live Translated Subtitles for Your Desktop

[![CI](https://github.com/HuiYingChung/yimu/actions/workflows/ci.yml/badge.svg)](https://github.com/HuiYingChung/yimu/actions/workflows/ci.yml)

> 繁體中文文件：[README.zh-TW.md](README.zh-TW.md)

**Yimu** captures whatever your Windows machine is playing — YouTube,
online meetings, livestreams, podcasts — and shows live subtitles in the
**target language you choose** (Traditional Chinese by default) in a floating
window. Translation is speech-native
(the audio stream goes straight into a translation model), so no
caption track is needed and no platform is off-limits.

- Dual engines, switchable in-app: **Gemini Live** (free tier) or
  **OpenAI gpt-realtime-translate** (metered)
- Source speech is detected automatically; choose the target language in
  Settings. The available list follows the selected engine (70+ targets on
  Gemini, 13 on OpenAI).
- Localized for Taiwan: OpenAI's Simplified-only output is converted
  client-side with OpenCC (Taiwan phrasing — 人工智慧, not 人工智能)
- Single-user, local-first: no server, no account, keys stay in a
  local `.env`
- Windows only (audio capture uses WASAPI loopback)
- Subtitles only — the translated audio is discarded, and the window
  stays quiet when the source is already in the selected target language
- **Meeting-ready**: optional Markdown transcripts (saved to
  Downloads), local speaker labels, and microphone mixing so your own
  voice makes it into the record
- **On-demand AI summaries**: with **Save transcript** enabled, finish a
  recorded session, review exactly what will leave the computer, then create
  a structured Markdown summary in the selected target language with the
  active Gemini or OpenAI engine

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

### AI summary requests

Summaries reuse the API key for the active engine, but their text-token
charges are separate from live audio translation:

- Gemini summaries use
  [`gemini-3.6-flash`](https://ai.google.dev/gemini-api/docs/models/gemini-3.6-flash).
  The [published pricing](https://ai.google.dev/gemini-api/docs/pricing) is
  $1.50 input / $7.50 output per 1 million tokens on the paid tier; a free
  tier is also available. Google states that free-tier content may be used
  to improve its products, while paid-tier content is not.
- OpenAI summaries use
  [`gpt-5.6-terra`](https://developers.openai.com/api/docs/models/gpt-5.6-terra)
  at $2.50 input / $15 output per 1 million tokens. Yimu sets `store=False`
  on every summary request.

Long transcripts may require multiple requests. Before anything is sent,
Yimu shows the provider, character count, and estimated request count and
waits for confirmation.

## Run

```
python main.py
```

Or double-click `start_translator.bat` (no console window; the
desktop shortcut "譯幕 Yimu" points to it).

- The subtitle window appears bottom-center: always on top,
  semi-transparent, black bar with white text.
- Play speech in any supported source language — subtitles in your selected
  target language appear within 2–3 seconds.
- **Drag** anywhere on the window to move it.
- **Pause / resume**: use the button at the top-right of the subtitle window,
  or the first item in the right-click menu. Pausing stops both audio capture
  and the live translation connection without splitting the current
  transcript.
- **Finish + summarize**: when **Save transcript** is enabled, choose
  **Finish** to close the current transcript. Yimu then shows the provider,
  character count, and estimated number of requests; the transcript is sent
  only if you confirm. If saving is disabled, **Finish** simply stops the
  session without a dialog or summary. A saved session can be retried later
  from **Summarize last session…** in the right-click menu. After restarting
  Yimu, pause live translation first to enable that menu item. The summary
  follows the current subtitle target language; there is no separate summary
  language setting.
- **Settings**: right-click → 設定….
- **Quit**: press `Esc`, or right-click → 結束.

## Settings panel

Right-click → 設定…. Appearance options **preview live** as you change
them (an empty window shows placeholder text while the dialog is
open); Cancel undoes the preview, Apply persists to `settings.json`
(delete the file to reset). Options are grouped into sections:

- **Engine** — Gemini (default, free) / OpenAI (metered; needs
  `OPENAI_API_KEY`). Switching reconnects in place, no restart.
- **Translation** — source speech is auto-detected; choose a target language
  supported by the active engine. Changing it reconnects automatically.
  Font size (10–32 pt) and lines shown (1–10; the window height follows
  automatically) remain adjustable.
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
  cost: billing is by duration, not loudness. Pause/resume keeps writing to
  the same logical session; **Finish** closes it. AI summary uses the source
  transcript when available, otherwise the translation, and saves a sibling
  `*_summary.md` file without overwriting earlier summaries. Summaries are
  available only when **Save transcript** is enabled.
- **Window** — opacity (30–100%) and window width (30–100% of the
  screen), both with live preview.
- **Interface language** — English (default) / 中文, switches the UI
  instantly. This is independent from the subtitle target language; AI
  summaries follow the target language, not the interface language.

Advanced defaults (transcript folder, reconnect timing, etc.) live in
`config.py`.

## Development checks

Every push and pull request runs the offline test suite on Windows with
Python 3.11. CI does not receive API keys and does not make live translation
requests.

Run the same checks locally:

```powershell
python -m compileall -q config.py languages.py main.py settings_ui.py strings.py subtitle_ui.py summarizer.py transcript.py translator.py translator_openai.py tests
python -m unittest discover -s tests -v
```

All summary tests use local fakes. They do not load `.env`, use API keys, or
send transcript text to either provider.

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
The four configured model names were verified in July 2026 and may change.
Check the current
[Gemini live-translation](https://ai.google.dev/gemini-api/docs/live-api/live-translate),
[Gemini summary](https://ai.google.dev/gemini-api/docs/models/gemini-3.6-flash),
[OpenAI realtime translation](https://developers.openai.com/api/docs/guides/realtime-translation),
or [OpenAI summary](https://developers.openai.com/api/docs/models/gpt-5.6-terra)
documentation, then update `MODEL_NAME`, `OPENAI_MODEL_NAME`,
`GEMINI_SUMMARY_MODEL`, or `OPENAI_SUMMARY_MODEL` in `config.py`.

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
                      (logical sessions, timestamps, content modes,
                      speaker headings)
summarizer.py          confirmed, on-demand structured summary through the
                      selected provider; long-transcript map/reduce and
                      collision-safe Markdown output
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
