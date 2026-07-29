"""Provider-aware target-language metadata for Yimu.

Both live translation engines detect the spoken input language
automatically. They only expose a target-language setting, and their target
language sets differ, so the settings UI must not offer an option that the
selected provider cannot honor.
"""

DEFAULT_TARGET_LANGUAGE = "zh-Hant"

# Gemini 3.5 Live Translate supports the BCP-47 codes below. Frequently used
# choices are intentionally first so the combobox is useful without scrolling.
GEMINI_TARGET_CODES = (
    "zh-Hant", "en", "ja", "ko", "zh-Hans", "es", "fr", "de",
    "pt-BR", "pt-PT", "vi", "th", "id", "it",
    "af", "ak", "sq", "am", "ar", "hy", "az", "eu", "be", "bn",
    "bg", "my", "ca", "hr", "cs", "da", "nl", "et", "fil", "fi",
    "gl", "ka", "el", "gu", "ha", "he", "hi", "hu", "is", "jv",
    "kn", "kk", "km", "rw", "lo", "lv", "lt", "mk", "ms", "ml",
    "mr", "mn", "ne", "no", "nb", "fa", "pl", "pa", "ro", "ru", "sr",
    "sd", "si", "sk", "sl", "su", "sw", "sv", "ta", "te", "tr",
    "uk", "ur", "uz", "zu",
)

# gpt-realtime-translate currently supports 13 output languages. Yimu keeps
# zh-Hant as its public code and maps it to OpenAI's generic "zh" at the
# transport boundary, then converts the returned text to Taiwan Traditional
# Chinese locally.
OPENAI_TARGET_CODES = (
    "zh-Hant", "en", "ja", "ko", "es", "fr", "de", "pt", "it",
    "vi", "id", "hi", "ru",
)

_TARGET_CODES = {
    "gemini": GEMINI_TARGET_CODES,
    "openai": OPENAI_TARGET_CODES,
}

_LANGUAGE_NAMES_EN = {
    "af": "Afrikaans",
    "ak": "Akan",
    "sq": "Albanian",
    "am": "Amharic",
    "ar": "Arabic",
    "hy": "Armenian",
    "az": "Azerbaijani",
    "eu": "Basque",
    "be": "Belarusian",
    "bn": "Bengali",
    "bg": "Bulgarian",
    "my": "Burmese (Myanmar)",
    "ca": "Catalan",
    "zh-Hans": "Chinese (Simplified)",
    "zh-Hant": "Chinese (Traditional)",
    "hr": "Croatian",
    "cs": "Czech",
    "da": "Danish",
    "nl": "Dutch",
    "en": "English",
    "et": "Estonian",
    "fil": "Filipino",
    "fi": "Finnish",
    "fr": "French",
    "gl": "Galician",
    "ka": "Georgian",
    "de": "German",
    "el": "Greek",
    "gu": "Gujarati",
    "ha": "Hausa",
    "he": "Hebrew",
    "hi": "Hindi",
    "hu": "Hungarian",
    "is": "Icelandic",
    "id": "Indonesian",
    "it": "Italian",
    "ja": "Japanese",
    "jv": "Javanese",
    "kn": "Kannada",
    "kk": "Kazakh",
    "km": "Khmer",
    "rw": "Kinyarwanda",
    "ko": "Korean",
    "lo": "Lao",
    "lv": "Latvian",
    "lt": "Lithuanian",
    "mk": "Macedonian",
    "ms": "Malay",
    "ml": "Malayalam",
    "mr": "Marathi",
    "mn": "Mongolian",
    "ne": "Nepali",
    "no": "Norwegian",
    "nb": "Norwegian Bokmål",
    "fa": "Persian",
    "pl": "Polish",
    "pt": "Portuguese",
    "pt-BR": "Portuguese (Brazil)",
    "pt-PT": "Portuguese (Portugal)",
    "pa": "Punjabi",
    "ro": "Romanian",
    "ru": "Russian",
    "sr": "Serbian",
    "sd": "Sindhi",
    "si": "Sinhala",
    "sk": "Slovak",
    "sl": "Slovenian",
    "es": "Spanish",
    "su": "Sundanese",
    "sw": "Swahili",
    "sv": "Swedish",
    "ta": "Tamil",
    "te": "Telugu",
    "th": "Thai",
    "tr": "Turkish",
    "uk": "Ukrainian",
    "ur": "Urdu",
    "uz": "Uzbek",
    "vi": "Vietnamese",
    "zu": "Zulu",
}

_LANGUAGE_NAMES_ZH = {
    "af": "南非語",
    "ak": "阿坎語",
    "sq": "阿爾巴尼亞語",
    "am": "阿姆哈拉語",
    "ar": "阿拉伯語",
    "hy": "亞美尼亞語",
    "az": "亞塞拜然語",
    "eu": "巴斯克語",
    "be": "白俄羅斯語",
    "bn": "孟加拉語",
    "bg": "保加利亞語",
    "my": "緬甸語",
    "ca": "加泰隆尼亞語",
    "zh-Hans": "中文（簡體）",
    "zh-Hant": "中文（繁體）",
    "hr": "克羅埃西亞語",
    "cs": "捷克語",
    "da": "丹麥語",
    "nl": "荷蘭語",
    "en": "英語",
    "et": "愛沙尼亞語",
    "fil": "菲律賓語",
    "fi": "芬蘭語",
    "fr": "法語",
    "gl": "加利西亞語",
    "ka": "喬治亞語",
    "de": "德語",
    "el": "希臘語",
    "gu": "古吉拉特語",
    "ha": "豪薩語",
    "he": "希伯來語",
    "hi": "印地語",
    "hu": "匈牙利語",
    "is": "冰島語",
    "id": "印尼語",
    "it": "義大利語",
    "ja": "日語",
    "jv": "爪哇語",
    "kn": "坎那達語",
    "kk": "哈薩克語",
    "km": "高棉語",
    "rw": "盧安達語",
    "ko": "韓語",
    "lo": "寮語",
    "lv": "拉脫維亞語",
    "lt": "立陶宛語",
    "mk": "馬其頓語",
    "ms": "馬來語",
    "ml": "馬拉雅拉姆語",
    "mr": "馬拉地語",
    "mn": "蒙古語",
    "ne": "尼泊爾語",
    "no": "挪威語",
    "nb": "挪威書面語",
    "fa": "波斯語",
    "pl": "波蘭語",
    "pt": "葡萄牙語",
    "pt-BR": "葡萄牙語（巴西）",
    "pt-PT": "葡萄牙語（葡萄牙）",
    "pa": "旁遮普語",
    "ro": "羅馬尼亞語",
    "ru": "俄語",
    "sr": "塞爾維亞語",
    "sd": "信德語",
    "si": "僧伽羅語",
    "sk": "斯洛伐克語",
    "sl": "斯洛維尼亞語",
    "es": "西班牙語",
    "su": "巽他語",
    "sw": "史瓦希利語",
    "sv": "瑞典語",
    "ta": "坦米爾語",
    "te": "泰盧固語",
    "th": "泰語",
    "tr": "土耳其語",
    "uk": "烏克蘭語",
    "ur": "烏都語",
    "uz": "烏茲別克語",
    "vi": "越南語",
    "zu": "祖魯語",
}

_KNOWN_TARGET_CODES = frozenset(
    code for codes in _TARGET_CODES.values() for code in codes
)


def target_language_codes(provider: str) -> tuple[str, ...]:
    """Return target codes supported by *provider*."""
    return _TARGET_CODES.get(provider, ())


def is_known_target_language(value) -> bool:
    """Return whether *value* is a target code understood by Yimu."""
    return isinstance(value, str) and value in _KNOWN_TARGET_CODES


def coerce_target_language(provider: str, code: str) -> str:
    """Keep a supported target or choose the nearest safe fallback."""
    supported = target_language_codes(provider)
    if code in supported:
        return code
    if provider == "openai" and code in ("pt-BR", "pt-PT"):
        return "pt"
    if provider == "gemini" and code == "pt":
        return "pt-BR"
    if DEFAULT_TARGET_LANGUAGE in supported:
        return DEFAULT_TARGET_LANGUAGE
    return supported[0] if supported else DEFAULT_TARGET_LANGUAGE


def language_name(code: str, ui_language: str = "en") -> str:
    """Return a localized display name, falling back to the code."""
    names = (_LANGUAGE_NAMES_ZH
             if str(ui_language).lower().startswith("zh")
             else _LANGUAGE_NAMES_EN)
    return names.get(code, _LANGUAGE_NAMES_EN.get(code, code))


def language_label(code: str, ui_language: str = "en") -> str:
    """Return an unambiguous combobox label."""
    return f"{language_name(code, ui_language)}  [{code}]"


def is_traditional_chinese(code: str) -> bool:
    return code == "zh-Hant"


def is_chinese(code: str) -> bool:
    return code in ("zh-Hans", "zh-Hant")
