"""Central configuration for the realtime subtitle translator.

Values below are the defaults. User-adjustable ones (see
_USER_SETTINGS) can be overridden by settings.json, written by the
in-app settings panel; that file is gitignored and safe to delete.
"""

import json
import os
import sys

# --- Translation ---
# "gemini" or "openai" — switchable in the settings panel; the OpenAI
# track is a placeholder, not implemented
PROVIDER = "gemini"
MODEL_NAME = "gemini-3.5-live-translate-preview"
OPENAI_MODEL_NAME = "gpt-realtime-translate"
TARGET_LANGUAGE_CODE = "zh-Hant"
# Stay silent when the source audio is already in the target language.
ECHO_TARGET_LANGUAGE = False
# Also show the source-language transcription above the translation.
SHOW_SOURCE_TEXT = False

# --- Audio ---
TARGET_SAMPLE_RATE = 16000  # required by the Live API
CHUNK_MS = 100              # one audio chunk sent per 100 ms

# --- Reconnect ---
RECONNECT_BASE_DELAY_S = 1.0
RECONNECT_MAX_DELAY_S = 30.0

# --- Subtitle window ---
WINDOW_WIDTH_RATIO = 0.7    # fraction of screen width
WINDOW_BOTTOM_MARGIN = 80   # px from bottom of screen
WINDOW_ALPHA = 0.85
FONT_FAMILY = "Microsoft JhengHei UI"
FONT_SIZE = 16
MAX_LINES = 3               # subtitle lines kept on screen
SENTENCE_PAUSE_S = 2.0      # break line after this long without new text
SENTENCE_ENDINGS = "。？！?!"

# --- User settings persistence (settings.json) ---

_SETTINGS_PATH = os.path.join(os.path.dirname(__file__), "settings.json")

# name -> validator; invalid or missing values keep the default above
_USER_SETTINGS = {
    "PROVIDER": lambda v: v in ("gemini", "openai"),
    "FONT_SIZE": lambda v: isinstance(v, int) and 10 <= v <= 32,
    "SHOW_SOURCE_TEXT": lambda v: isinstance(v, bool),
    "WINDOW_ALPHA": lambda v: (isinstance(v, (int, float))
                               and not isinstance(v, bool)
                               and 0.3 <= v <= 1.0),
}


def load_user_settings() -> None:
    """Overlay settings.json onto the defaults. Called at import."""
    try:
        with open(_SETTINGS_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return
    except (json.JSONDecodeError, OSError) as exc:
        print(f"warning: ignoring unreadable settings.json ({exc})",
              file=sys.stderr)
        return
    for name, valid in _USER_SETTINGS.items():
        if name in data and valid(data[name]):
            globals()[name] = data[name]


def save_user_settings() -> None:
    """Write the current user-adjustable values to settings.json."""
    data = {name: globals()[name] for name in _USER_SETTINGS}
    with open(_SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


load_user_settings()
