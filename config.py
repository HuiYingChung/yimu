"""Central configuration for the realtime subtitle translator."""

# --- Translation ---
MODEL_NAME = "gemini-3.5-live-translate-preview"
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
FONT_SIZE = 22
MAX_LINES = 2               # subtitle lines kept on screen
SENTENCE_PAUSE_S = 2.0      # break line after this long without new text
SENTENCE_ENDINGS = "。？！?!"
