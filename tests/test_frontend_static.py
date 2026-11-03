"""Static regression guards for the frontend feedback helpers (issue #157).

Native alert()/confirm() block the page, can't be styled or translated
consistently, and are suppressed in some embedded browsers. All feedback
goes through js/ui.js (window.WtaUI); app code may only fall back to the
native dialogs when that helper is missing.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LANGS = ("en", "zh", "ja", "ar", "ru", "es", "pt", "fr", "de")
NEW_KEYS = (
    "ui.close",
    "ui.cancel",
    "ui.confirm",
    "analysis.statusFailed",
    "analysis.failed.generic",
    "analysis.failed.network",
    "analysis.failed.hint",
    "market.loadFailed",
    "market.retry",
    "profile.saveFailed",
)


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


class FrontendFeedbackTests(unittest.TestCase):
    def test_index_loads_ui_helpers_before_app(self):
        html = _read("index.html")
        self.assertIn("js/ui.js?v=", html)
        self.assertLess(html.index("js/ui.js"), html.index("js/app.v5.js"))

    def test_ui_helpers_expose_toast_and_confirm(self):
        src = _read("js/ui.js")
        self.assertIn("window.WtaUI", src)
        self.assertIn("aria-live", src)

    def test_no_unguarded_native_dialogs(self):
        # Native dialogs are allowed only on a line that also checks for
        # the WtaUI helper (the fallback path), or inside ui.js itself.
        pattern = re.compile(r"(?<![\w.])(?:window\.)?(alert|confirm)\(")
        for rel in ("js/app.v5.js", "js/community.js"):
            lines = _read(rel).splitlines()
            for no, line in enumerate(lines, 1):
                if not pattern.search(line):
                    continue
                context = "\n".join(lines[max(0, no - 3):no])
                self.assertIn(
                    "WtaUI", context,
                    f"{rel}:{no} uses a native dialog without a WtaUI fallback guard",
                )

    def test_new_strings_exist_in_every_language(self):
        src = _read("js/i18n.strings.js")
        blocks = {lang: "" for lang in LANGS}
        for match in re.finditer(r"R\('(\w+)',\s*\{(.*?)\}\);", src, re.S):
            lang, body = match.group(1), match.group(2)
            if lang in blocks:
                blocks[lang] += body
        for lang in LANGS:
            for key in NEW_KEYS:
                self.assertIn(f"'{key}'", blocks[lang], f"{key} missing for {lang}")

    def test_failed_analysis_has_warn_styles(self):
        css = _read("css/style.css")
        self.assertIn(".status-badge.warn", css)
        self.assertIn(".analysis-item .value.warn", css)


class FrontendResilienceTests(unittest.TestCase):
    """Regression guards for issue #159."""

    def test_market_error_state_is_distinct_from_empty(self):
        html = _read("index.html")
        self.assertIn('id="market-error"', html)
        self.assertIn('id="market-retry"', html)
        self.assertIn('id="market-empty"', html)

    def test_market_ignores_stale_responses(self):
        src = _read("js/app.v5.js")
        self.assertIn("marketRequestSeq", src)
        self.assertIn("seq !== marketRequestSeq", src)

    def test_profile_modal_closes_on_escape(self):
        src = _read("js/app.v5.js")
        self.assertIn("profileReturnFocus", src)
        self.assertRegex(src, r"e\.key !== 'Escape'[\s\S]{0,200}closeProfileModal\(\)")

    def test_nav_scroll_uses_class_not_inline_style(self):
        src = _read("js/app.v5.js")
        self.assertNotIn("nav.style.background", src)
        self.assertIn("is-scrolled", src)
        self.assertIn("#nav.is-scrolled", _read("css/style.css"))

    def test_chinese_market_empty_text_typo_fixed(self):
        self.assertNotIn("公链应用", _read("js/i18n.strings.js"))


if __name__ == "__main__":
    unittest.main()
