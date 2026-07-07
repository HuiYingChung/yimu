"""UI strings for both interface languages.

t(key, **fmt) resolves against config.UI_LANGUAGE at call time, so a
language switch affects every message from that moment on. Subtitle
output itself is untouched — it is translation content, not UI.
"""

import config

_STRINGS = {
    # subtitle window
    "waiting":          {"en": "Waiting for audio…",
                         "zh": "等待聲音…"},
    "menu_settings":    {"en": "Settings…",
                         "zh": "設定…"},
    "menu_quit":        {"en": "Quit",
                         "zh": "結束"},

    # settings panel
    "settings_title":   {"en": "Yimu Settings",
                         "zh": "譯幕 設定"},
    "engine":           {"en": "Translation engine",
                         "zh": "翻譯引擎"},
    "engine_gemini":    {"en": "Gemini (free tier)",
                         "zh": "Gemini（免費額度）"},
    "engine_openai":    {"en": "OpenAI (paid, ~$2/hour)",
                         "zh": "OpenAI（付費，約 $2/小時）"},
    "section_subtitle": {"en": "Translation",
                         "zh": "譯文"},
    "section_window":   {"en": "Window",
                         "zh": "視窗"},
    "section_source":   {"en": "Source text",
                         "zh": "原文"},
    "section_record":   {"en": "Recording",
                         "zh": "記錄"},
    "font_size":        {"en": "Font size",
                         "zh": "字級"},
    "lines":            {"en": "Lines shown",
                         "zh": "顯示行數"},
    "show_source":      {"en": "Show source text",
                         "zh": "顯示原文"},
    "source_lines":     {"en": "Source lines",
                         "zh": "原文行數"},
    "source_font_size": {"en": "Source font size",
                         "zh": "原文字級"},
    "opacity":          {"en": "Opacity",
                         "zh": "透明度"},
    "window_width":     {"en": "Window width",
                         "zh": "視窗寬度"},
    "save_transcript":  {"en": "Save transcript (Downloads folder)",
                         "zh": "儲存逐字稿（Downloads 資料夾）"},
    "ts_both":          {"en": "Both",
                         "zh": "原文＋譯文"},
    "ts_translation":   {"en": "Translation only",
                         "zh": "只有譯文"},
    "ts_source":        {"en": "Source only",
                         "zh": "只有原文"},
    "speaker_labels":   {"en": "Label speakers (local, heuristic)",
                         "zh": "標記講者（本機辨識，非精確）"},
    "speaker_help_link": {"en": "how it works",
                          "zh": "說明"},
    "speaker_help_title": {"en": "Speaker labels",
                           "zh": "標記講者"},
    "speaker_help_body": {
        "en": "Analyzes voice characteristics locally on this computer "
              "and writes 講者 1/2/… headings into the transcript when "
              "the speaker changes.\n\n"
              "Requirements:\n"
              "• 'Save transcript' must be enabled\n"
              "• One-time install: pip install resemblyzer "
              "(pulls PyTorch, ~1-2 GB)\n"
              "• The audio needs more than one voice to show any effect\n\n"
              "No API calls, no extra cost. Detection is heuristic — "
              "speaker count and switch timing may be imperfect.",
        "zh": "在你的電腦本機分析聲音特徵，聲音換人時在逐字稿裡插入"
              "「講者 1／2…」標題。\n\n"
              "條件：\n"
              "• 需勾選「儲存逐字稿」\n"
              "• 需安裝一次套件：pip install resemblyzer"
              "（含 PyTorch 約 1–2 GB）\n"
              "• 音訊要有多位講者才看得出效果\n\n"
              "不呼叫 API、不另外收費。辨識為推測性質，"
              "人數與切換時間可能不完全準確。"},
    "capture_mic":      {"en": "Capture microphone (meetings; "
                               "use headphones)",
                         "zh": "擷取麥克風（開會用；建議戴耳機）"},
    "transcript_on":    {"en": "transcript will start on reconnect",
                         "zh": "逐字稿將於重新連線後開始記錄"},
    "ui_language":      {"en": "Interface language",
                         "zh": "介面語言"},
    "cancel":           {"en": "Cancel",
                         "zh": "取消"},
    "apply":            {"en": "Apply",
                         "zh": "套用"},
    "switching_engine": {"en": "Switching to {provider}, reconnecting…",
                         "zh": "切換引擎：{provider}，重新連線中…"},

    # settings live-preview placeholders
    "preview_line":     {"en": "Subtitle preview text 字幕預覽",
                         "zh": "字幕預覽文字 subtitle preview"},
    "preview_source":   {"en": "Source text preview appears here",
                         "zh": "原文預覽 source text preview"},

    # status line
    "listening":        {"en": "listening…",
                         "zh": "聆聽中…"},
    "connected":        {"en": "connected",
                         "zh": "已連線"},
    "reconnecting":     {"en": "session ended, reconnecting…",
                         "zh": "session 結束，重新連線中…"},
    "rate_limited":     {"en": "rate limited (429), retrying in {delay}s…",
                         "zh": "額度受限（429），{delay} 秒後重試…"},
    "conn_lost":        {"en": "connection lost, retrying in {delay}s…",
                         "zh": "連線中斷，{delay} 秒後重試…"},

    # errors
    "err_prefix":       {"en": "Error: {msg}",
                         "zh": "錯誤：{msg}"},
    "err_unexpected":   {"en": "Unexpected error: {msg}",
                         "zh": "未預期的錯誤：{msg}"},
    "err_gemini_key":   {"en": "Gemini rejected the API key. Check "
                               "GEMINI_API_KEY in .env ({detail})",
                         "zh": "Gemini 拒絕了這把 key。檢查 .env 的 "
                               "GEMINI_API_KEY（{detail}）"},
    "err_openai_key":   {"en": "OpenAI rejected the API key. Check "
                               "OPENAI_API_KEY in .env ({detail})",
                         "zh": "OpenAI 拒絕了這把 key。檢查 .env 的 "
                               "OPENAI_API_KEY（{detail}）"},
    "err_capture":      {"en": "audio capture failed: {detail}",
                         "zh": "音訊擷取失敗：{detail}"},
    "err_diarizer":     {"en": "speaker labels off — run: "
                               "pip install resemblyzer",
                         "zh": "講者標記未啟用——請先執行 "
                               "pip install resemblyzer"},
    "err_bad_provider": {"en": "Invalid PROVIDER value: {value}.\n"
                               "Valid options: {options}",
                         "zh": "設定裡的 PROVIDER 值不合法:{value}。\n"
                               "可用值:{options}"},
    "err_missing_key":  {"en": "{key} is not set (PROVIDER = {provider}).\n\n"
                               "1. Get an API key (Gemini: "
                               "https://aistudio.google.com/apikey)\n"
                               "2. Copy .env.example to .env and paste "
                               "your key\n"
                               "3. Run python main.py again",
                         "zh": "{key} 未設定（PROVIDER = {provider}）。\n\n"
                               "1. 取得 API key（Gemini:"
                               "https://aistudio.google.com/apikey）\n"
                               "2. 複製 .env.example 為 .env，貼上你的 key\n"
                               "3. 重新執行 python main.py"},
}


def t(key: str, **fmt) -> str:
    lang = "zh" if str(config.UI_LANGUAGE).lower().startswith("zh") else "en"
    text = _STRINGS[key][lang]
    return text.format(**fmt) if fmt else text
