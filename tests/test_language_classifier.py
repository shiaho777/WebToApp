"""Heuristic language backfill for existing apps (#195)."""

import unittest

from server.scripts.classify_app_languages import infer_languages


class LanguageClassifierTests(unittest.TestCase):
    def test_scripts_are_detected(self):
        self.assertEqual(infer_languages({"name": "班级工作台"}), ["zh"])
        self.assertEqual(infer_languages({"name": "전쟁 게임"}), ["ko"])
        self.assertEqual(infer_languages({"name": "ポイ活管理"}), ["ja"])
        self.assertEqual(infer_languages({"name": "آب‌یار"}), ["ar"])
        self.assertEqual(infer_languages({"name": "Флибуста"}), ["ru"])

    def test_latin_stopwords_and_tld(self):
        self.assertEqual(
            infer_languages({"name": "News", "description": "The best app with news for you"}),
            ["en"],
        )
        self.assertEqual(
            infer_languages({"name": "Tienda", "description": "La mejor tienda para comprar con una app"}),
            ["es"],
        )
        self.assertEqual(infer_languages({"name": "Site", "url": "https://example.jp"}), ["ja"])

    def test_empty_text_is_unspecified(self):
        self.assertEqual(infer_languages({"name": "π"}), ["und"])


if __name__ == "__main__":
    unittest.main()
