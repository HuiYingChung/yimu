import unittest

from languages import (
    DEFAULT_TARGET_LANGUAGE,
    GEMINI_TARGET_CODES,
    OPENAI_TARGET_CODES,
    coerce_target_language,
    is_known_target_language,
    language_label,
    language_name,
    target_language_codes,
)


class LanguageRegistryTests(unittest.TestCase):
    def test_provider_lists_are_unique_and_have_safe_default(self):
        for provider in ("gemini", "openai"):
            codes = target_language_codes(provider)
            self.assertTrue(codes)
            self.assertEqual(len(codes), len(set(codes)))
            self.assertIn(DEFAULT_TARGET_LANGUAGE, codes)

    def test_openai_has_documented_thirteen_targets(self):
        self.assertEqual(len(OPENAI_TARGET_CODES), 13)

    def test_gemini_exposes_full_documented_target_set(self):
        self.assertGreaterEqual(len(GEMINI_TARGET_CODES), 70)

    def test_provider_switch_preserves_or_coerces_target(self):
        self.assertEqual(coerce_target_language("openai", "ja"), "ja")
        self.assertEqual(coerce_target_language("openai", "pl"), "zh-Hant")
        self.assertEqual(coerce_target_language("openai", "pt-BR"), "pt")
        self.assertEqual(coerce_target_language("gemini", "pt"), "pt-BR")

    def test_all_codes_have_readable_labels(self):
        codes = set(GEMINI_TARGET_CODES) | set(OPENAI_TARGET_CODES)
        for code in codes:
            self.assertTrue(is_known_target_language(code))
            self.assertNotEqual(language_name(code, "en"), code)
            self.assertNotEqual(language_name(code, "zh-TW"), code)
            self.assertIn(f"[{code}]", language_label(code, "en"))

    def test_unknown_provider_is_safe(self):
        self.assertEqual(target_language_codes("unknown"), ())
        self.assertEqual(
            coerce_target_language("unknown", "ja"),
            DEFAULT_TARGET_LANGUAGE,
        )


if __name__ == "__main__":
    unittest.main()
