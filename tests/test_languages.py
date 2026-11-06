"""Language metadata and market bucketing (#195)."""

import unittest

from server.languages import language_category, normalize_languages


class LanguageMetadataTests(unittest.TestCase):
    def test_normalize_keeps_order_and_deduplicates(self):
        self.assertEqual(normalize_languages(["zh", "en", "zh"]), ["zh", "en"])
        self.assertEqual(normalize_languages("ko"), ["ko"])

    def test_unknown_and_empty_become_unspecified(self):
        self.assertEqual(normalize_languages([]), ["und"])
        self.assertEqual(normalize_languages(["xx"]), ["und"])
        self.assertEqual(normalize_languages(["und", "en"]), ["en"])

    def test_category_buckets(self):
        self.assertEqual(language_category(["zh"]), "zh")
        self.assertEqual(language_category(["zh", "en"]), "mul")
        self.assertEqual(language_category(["en", "other"]), "mul")
        self.assertEqual(language_category(["other"]), "other")
        self.assertEqual(language_category([]), "und")
        self.assertEqual(language_category(["und"]), "und")


if __name__ == "__main__":
    unittest.main()
