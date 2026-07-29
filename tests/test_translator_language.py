import asyncio
import unittest

import config
from translator import Translator as GeminiTranslator
from translator_openai import _display_text, _openai_language


class OpenAILanguageTests(unittest.TestCase):
    def test_transport_uses_base_language_codes(self):
        self.assertEqual(_openai_language("zh-Hant"), "zh")
        self.assertEqual(_openai_language("pt-BR"), "pt")
        self.assertEqual(_openai_language("ja"), "ja")

    def test_taiwan_conversion_only_applies_to_chinese_target(self):
        self.assertEqual(_display_text("人工智能", "zh-Hant"), "人工智慧")
        self.assertEqual(_display_text("人工智能", "ja"), "人工智能")


class GeminiEchoFilterTests(unittest.TestCase):
    def setUp(self):
        self._original_target = config.TARGET_LANGUAGE_CODE
        self._translator = GeminiTranslator(
            asyncio.Queue(), on_text=lambda _text: None)
        self._translator._recent_input = "測試字幕"

    def tearDown(self):
        config.TARGET_LANGUAGE_CODE = self._original_target

    def test_chinese_target_filters_matching_source_echo(self):
        config.TARGET_LANGUAGE_CODE = "zh-Hant"
        self.assertTrue(self._translator._is_echo("測試字幕"))

    def test_non_chinese_target_does_not_use_chinese_echo_heuristic(self):
        config.TARGET_LANGUAGE_CODE = "ja"
        self.assertFalse(self._translator._is_echo("測試字幕"))


if __name__ == "__main__":
    unittest.main()
