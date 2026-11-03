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


class FrontendPerformanceTests(unittest.TestCase):
    """Regression guards for issue #161."""

    def _font_urls(self):
        pattern = re.compile(r'https://fonts\.googleapis\.com/css2\?[^"]+')
        return {
            rel: pattern.findall(_read(rel))
            for rel in ("index.html", "server/engine/distiller.py")
        }

    def test_font_request_skips_unused_weights(self):
        for rel, urls in self._font_urls().items():
            self.assertTrue(urls, f"{rel} has no font link")
            for url in urls:
                self.assertNotIn("900", url, rel)
                self.assertNotIn("Spectral:wght@400", url, rel)

    def test_nav_logo_uses_small_asset_with_dimensions(self):
        self.assertTrue((ROOT / "assets/site-logo-96.jpg").is_file())
        for rel in ("index.html", "server/engine/distiller.py"):
            src = _read(rel)
            self.assertRegex(
                src,
                r'<img src="/?assets/site-logo-96\.jpg" alt="WebToApp" width="28" height="28">',
                rel,
            )
            self.assertNotIn('src="assets/site-logo.jpg"', src, rel)
            self.assertNotIn('src="/assets/site-logo.jpg"', src, rel)

    def test_dynamic_images_are_lazy(self):
        src = _read("js/app.v5.js")
        for line in src.splitlines():
            if "<img " in line:
                self.assertIn('loading="lazy"', line, line.strip())

    def test_count_up_respects_reduced_motion(self):
        src = _read("js/app.v5.js")
        self.assertIn("prefers-reduced-motion: reduce", src)
        self.assertRegex(src, r"function animateCount[\s\S]{0,200}reducedMotionQuery")

    def test_no_stale_repository_links(self):
        for rel in ["index.html", *sorted(str(p.relative_to(ROOT)) for p in (ROOT / "docs").glob("DEPLOY*.md"))]:
            self.assertNotIn("shiahonb777", _read(rel), rel)

    def test_compression_middleware_is_installed(self):
        src = _read("server/main.py")
        self.assertIn("app.add_middleware(TextCompressionMiddleware)", src)


class FrontendDesignSystemTests(unittest.TestCase):
    """Guards for the token-based design system, dark mode and hero layout (#163)."""

    def setUp(self):
        self.css = _read("css/style.css")

    def test_dark_palette_is_defined(self):
        self.assertIn("@media (prefers-color-scheme: dark)", self.css)
        self.assertRegex(self.css, r"color-scheme:\s*dark")
        html = _read("index.html")
        self.assertIn('media="(prefers-color-scheme: dark)"', html)

    def test_no_hard_coded_ink_channels(self):
        # Ink-tinted colors must go through --ink-rgb so dark mode can flip them.
        root_end = self.css.index("}")
        body = self.css[root_end:]
        self.assertNotRegex(body, r"rgba\(\s*30\s*,\s*25\s*,\s*20\s*,")

    def test_every_custom_property_is_defined(self):
        css = re.sub(r"/\*[\s\S]*?\*/", "", self.css)
        used = set(re.findall(r"var\(\s*(--[\w-]+)", css))
        defined = set(re.findall(r"(--[\w-]+)\s*:", css))
        self.assertEqual(sorted(used - defined), [])

    def test_hero_is_not_forced_to_full_viewport(self):
        match = re.search(r"#hero\s*\{([^}]*)\}", self.css)
        self.assertIsNotNone(match)
        self.assertNotIn("100vh", match.group(1))

    def test_url_validation_uses_state_class(self):
        src = _read("js/app.v5.js")
        self.assertNotIn("urlInput.style.boxShadow", src)
        self.assertIn("classList.add('is-invalid')", src)
        self.assertIn(".url-input-wrap.is-invalid", self.css)

    def test_ui_helpers_follow_tokens_with_light_fallbacks(self):
        src = _read("js/ui.js")
        css_lines = [line for line in src.splitlines() if line.strip().startswith("'.wta-")]
        self.assertTrue(css_lines)
        for line in css_lines:
            stripped = re.sub(r"var\([^()]*(?:\([^()]*\)[^()]*)*\)", "", line)
            self.assertNotRegex(stripped, r"#[0-9a-fA-F]{3,6}\b", line.strip())


if __name__ == "__main__":
    unittest.main()
