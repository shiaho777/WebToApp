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
                r'<img src="/?assets/site-logo-96\.jpg\?v=[\w-]+" alt="WebToApp" width="28" height="28">',
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


def _hex_luminance(value):
    value = value.lstrip("#")
    channels = [int(value[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(a, b):
    hi, lo = sorted((_hex_luminance(a), _hex_luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


class BrandAndComponentSystemTests(unittest.TestCase):
    """Guards for the Anthropic-style component system and brand icon set (#165)."""

    ICONS = (
        "assets/site-logo.jpg",
        "assets/site-logo-96.jpg",
        "assets/apple-touch-icon.png",
        "assets/icon-192.png",
        "assets/icon-512.png",
    )

    def setUp(self):
        self.css = _read("css/style.css")
        self.root = self.css[: self.css.index("}")]

    def test_icon_files_exist(self):
        for rel in self.ICONS:
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_pages_reference_new_icon_set(self):
        html = _read("index.html")
        self.assertIn('href="assets/site-logo-96.jpg', html)
        self.assertIn('rel="apple-touch-icon"', html)
        self.assertIn('rel="manifest"', html)
        self.assertIn("assets/site-logo-96.jpg", _read("privacy.html"))
        self.assertIn("/assets/site-logo-96.jpg", _read("server/engine/distiller.py"))
        for rel in ("index.html", "privacy.html", "server/engine/distiller.py", "manifest.webmanifest"):
            self.assertNotIn("logo.svg", _read(rel), rel)

    def test_manifest_declares_installable_icons(self):
        import json

        manifest = json.loads(_read("manifest.webmanifest"))
        sizes = {icon.get("sizes") for icon in manifest.get("icons", [])}
        self.assertTrue({"192x192", "512x512"} <= sizes)
        for icon in manifest["icons"]:
            self.assertTrue((ROOT / icon["src"].lstrip("/").split("?")[0]).is_file(), icon["src"])

    def test_manifest_mime_type_is_registered(self):
        self.assertIn("application/manifest+json", _read("server/main.py"))

    def test_palette_matches_reference_tokens(self):
        # Original WebToApp palette (#169): warm paper, ink, terracotta.
        self.assertIn("--paper: #f7f3ec;", self.root)
        self.assertIn("--paper-deep: #efe7db;", self.root)
        self.assertRegex(self.root, r"--ink-rgb:\s*30,\s*25,\s*20;")
        self.assertRegex(self.root, r"--accent-rgb:\s*201,\s*121,\s*83;")

    def test_tertiary_text_meets_contrast(self):
        faint = re.search(r"--ink-faint:\s*(#[0-9a-fA-F]{6});", self.root).group(1)
        for surface in ("#f7f3ec", "#efe7db", "#fbf8f3", "#efe5d6"):
            self.assertGreaterEqual(_contrast(faint, surface), 4.5, surface)

    def test_no_heavy_weights_or_glass_effects(self):
        self.assertNotRegex(self.css, r"font-weight:\s*(650|700|800)\b")
        self.assertNotRegex(self.css, r"backdrop-filter:\s*blur")
        self.assertNotIn("backdrop-filter:blur", _read("js/ui.js"))

    def test_text_colors_do_not_use_translucent_ink(self):
        # Readable text goes through --ink-soft / --ink-faint so contrast is controlled.
        self.assertNotRegex(self.css, r"\n\s+color: rgba\(var\(--ink-rgb\), 0\.[3-5]\d*\);")


class FrontendBuildFlowTests(unittest.TestCase):
    """Guards for the live build progress, form lock and result platforms (#167)."""

    BUILD_KEYS = (
        "build.title",
        "build.failedTitle",
        "build.retry",
        "build.busy",
        "build.buttonBusy",
        "build.platformFailed",
        "build.step.queued",
        "build.step.icon",
        "build.step.shell",
        "build.step.platforms",
        "build.step.publish",
    )

    def setUp(self):
        self.html = _read("index.html")
        self.js = _read("js/app.v5.js")
        self.css = _read("css/style.css")

    def test_progress_panel_lists_every_step_and_platform(self):
        for step in ("queued", "fetching_icon", "writing_shell", "building_platforms", "uploading_cdn"):
            self.assertIn(f'data-step="{step}"', self.html)
        for platform in ("android", "ios", "windows", "macos", "linux"):
            self.assertIn(f'data-platform="{platform}"', self.html)

    def test_live_region_is_separate_from_ticking_timer(self):
        self.assertIn('id="build-progress-live"', self.html)
        self.assertNotRegex(self.html, r'id="build-progress"[^>]*aria-live')

    def test_inline_error_has_retry(self):
        self.assertIn('id="build-error"', self.html)
        self.assertIn('id="build-retry-btn"', self.html)
        self.assertIn("buildRetryBtn.addEventListener('click', handleGenerateClick)", self.js)

    def test_progress_no_longer_written_into_button_text(self):
        self.assertNotIn("stageLabel(", self.js)
        self.assertNotIn("config.generateBtnEmoji", self.js)

    def test_concurrent_builds_are_blocked(self):
        self.assertIn("if (buildInFlight) throw new Error(t('build.busy'))", self.js)
        regen = self.js[self.js.index("if (target.dataset.regenerate)"):]
        self.assertLess(regen.index("buildInFlight"), regen.index("applyHistoryItemToForm"))

    def test_result_platforms_reflect_platform_errors(self):
        self.assertIn('id="result-platforms"', self.html)
        self.assertIn("renderResultPlatforms(data && data.platform_errors)", self.js)
        for cls in (".platform-tag.is-ready", ".platform-tag.is-error"):
            self.assertIn(cls, self.css)

    def test_progress_styles_exist(self):
        for cls in (".build-progress", ".build-steps", ".build-platforms", ".build-error", ".is-locked"):
            self.assertIn(cls, self.css)

    def test_build_strings_exist_in_every_language(self):
        strings = _read("js/i18n.strings.js")
        start = strings.index("'build.title'")
        block = strings[strings.rfind("(function", 0, start):]
        for lang in LANGS:
            self.assertIn(f"R('{lang}',", block, lang)
        for key in self.BUILD_KEYS:
            self.assertEqual(block.count(f"'{key}'"), len(LANGS), key)


class HomeHistoryMarketRedesignTests(unittest.TestCase):
    """Regression guards for the homepage/history/market redesign (#171)."""

    REDESIGN_KEYS = (
        "hero.pointFree",
        "hero.pointPlatforms",
        "hero.pointSize",
        "hero.stagePhone",
        "hero.stageDesktop",
        "hero.stageCaption",
        "hero.previewIdle",
        "hero.previewLoading",
        "hero.previewUnavailable",
        "hero.openSite",
        "hero.previewAlt",
        "history.searchPlaceholder",
        "history.sortVisits",
        "history.delete",
        "history.confirmDelete",
        "history.makePublic",
        "history.noMatches",
        "market.noMatches",
        "market.loadMore",
    )

    def setUp(self):
        self.html = _read("index.html")
        self.js = _read("js/app.v5.js")
        self.css = _read("css/style.css")
        self.strings = _read("js/i18n.strings.js")
        self.server = _read("server/main.py")

    def test_home_uses_live_device_preview(self):
        for marker in (
            'id="hero-stage"',
            'data-stage-tab="phone"',
            'data-stage-tab="desktop"',
            'id="stage-app-icon"',
            'id="stage-app-img"',
            'id="stage-app-name"',
            'id="stage-app-host"',
        ):
            self.assertIn(marker, self.html)
        self.assertIn("function renderStagePreview(force)", self.js)
        self.assertIn("google.com/s2/favicons", self.js)
        self.assertIn("PREVIEW_DEFAULT", self.js)

    def test_home_preview_uses_mshots_with_retry(self):
        for marker in (
            'id="stage-preview-img"',
            'id="stage-preview-placeholder"',
            'id="stage-preview-status"',
            'id="stage-preview-link"',
            'id="stage-app-open"',
        ):
            self.assertIn(marker, self.html)
        self.assertIn("s.wordpress.com/mshots/v1/", self.js)
        self.assertIn("PREVIEW_RETRIES", self.js)
        self.assertIn("naturalWidth === 400", self.js)
        self.assertIn("hero.previewUnavailable", self.js)
        self.assertIn("mShots", _read("privacy.html"))

    def test_home_drops_the_old_prose_and_platform_pills(self):
        for marker in ('class="badge"', 'class="hero-platforms"', "hero-platform-list"):
            self.assertNotIn(marker, self.html)
        self.assertIn('class="hero-points"', self.html)
        self.assertIn('class="hero-stats"', self.html)

    def test_history_has_search_sort_and_overflow_menu(self):
        for marker in (
            'id="history-search"',
            'id="history-sort"',
            'id="history-more-btn"',
            'id="history-more-panel"',
        ):
            self.assertIn(marker, self.html)
        self.assertIn("function visibleHistoryItems()", self.js)
        self.assertIn("data-row-menu", self.js)
        self.assertIn("historyQuery", self.js)

    def test_single_history_delete_uses_existing_endpoint(self):
        self.assertIn("data-delete=", self.js)
        self.assertIn("method: 'DELETE'", self.js)
        self.assertIn("/api/history/${encodeURIComponent(appId)}", self.js)
        self.assertIn('@app.delete("/api/history/{app_id}")', self.server)
        self.assertIn("history.confirmDelete", self.strings)

    def test_history_select_all_respects_active_filter(self):
        self.assertIn("const visible = visibleHistoryItems();", self.js)
        self.assertIn("visible.every((entry) => historySelected.has(entry.app_id || ''))", self.js)

    def test_market_has_load_more_pagination(self):
        self.assertIn('id="market-load-more"', self.html)
        self.assertIn("marketHasMore", self.js)
        self.assertIn("params.set('offset'", self.js)
        self.assertIn("data.has_more", self.js)

    def test_market_api_reports_pagination(self):
        self.assertIn("MARKET_PAGE_MAX = 60", self.server)
        for marker in (
            '"offset": page_offset',
            '"limit": page_limit',
            '"has_more": page_offset + len(page) < total',
        ):
            self.assertIn(marker, self.server)

    def test_redesign_strings_exist_in_every_language(self):
        blocks = {lang: "" for lang in LANGS}
        for match in re.finditer(r"R\('(\w+)',\s*\{(.*?)\}\);", self.strings, re.S):
            if match.group(1) in blocks:
                blocks[match.group(1)] += match.group(2)
        for lang in LANGS:
            for key in self.REDESIGN_KEYS:
                self.assertIn(f"'{key}'", blocks[lang], f"{key} missing for {lang}")

    def test_new_components_have_styles(self):
        for cls in (
            ".hero-stage",
            ".stage-device",
            ".app-row",
            ".row-menu",
            ".market-card-head",
            ".section-panel",
        ):
            self.assertIn(cls, self.css)


if __name__ == "__main__":
    unittest.main()
