import unittest
from unittest.mock import patch

from server.engine.distiller import Distiller, _MACOS_HELPER_NAME, _MACOS_TEMPLATE_DIR, _safe_fs_name


class DistillerIconCandidateTests(unittest.TestCase):
    def test_collect_icon_candidates_reads_links_and_manifest(self):
        page_html = b"""
        <html>
          <head>
            <link href="/apple-touch-icon.png" sizes="180x180" rel="apple-touch-icon">
            <link href="/favicon.png" sizes="64x64" rel="shortcut icon">
            <link href="/site.webmanifest" rel="manifest">
            <meta content="/tile.png" name="msapplication-TileImage">
          </head>
        </html>
        """
        manifest = b'{"icons":[{"src":"/manifest-icon.png","sizes":"512x512"}]}'
        distiller = Distiller()

        def fake_fetch(url, timeout=8, use_cache=False):
            if url == "https://example.com":
                return page_html
            if url == "https://example.com/site.webmanifest":
                return manifest
            return None

        with patch.object(distiller, "_fetch_url_bytes", side_effect=fake_fetch):
            candidates = distiller._collect_icon_candidates("https://example.com")
        self.assertIn("https://example.com/apple-touch-icon.png", candidates)
        self.assertIn("https://example.com/favicon.png", candidates)
        self.assertIn("https://example.com/manifest-icon.png", candidates)
        self.assertIn("https://example.com/tile.png", candidates)


class DistillerWriteAppFilesTests(unittest.TestCase):
    def test_write_app_files_parallel_builds_desktop_packages(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        distiller = Distiller()
        recipe = distiller.create_recipe(
            app_id="abcd1234",
            url="https://example.com",
            name="Example",
            color="#123456",
            display="fullscreen",
            orientation="any",
            options={},
        )
        stages = []

        def progress(stage, detail=None):
            stages.append(stage)

        with tempfile.TemporaryDirectory() as tmp:
            app_dir = Path(tmp) / "abcd1234"
            with patch.object(distiller, "_fetch_icon", return_value=distiller._make_placeholder_png("#123456")):
                with patch.object(distiller, "_build_android", return_value={"apk": False, "fallback": True}) as android_mock:
                    with patch.object(distiller, "_build_ios", return_value={"signed": False, "dynamic_url": True}) as ios_mock:
                        meta = distiller.write_app_files(app_dir, recipe, base_url="https://service.test", progress_cb=progress)
            self.assertTrue((app_dir / "downloads" / "windows.zip").exists())
            self.assertTrue((app_dir / "downloads" / "macos.zip").exists())
            self.assertTrue((app_dir / "downloads" / "linux.tar.gz").exists())
            self.assertTrue((app_dir / "recipe.json").exists())
            self.assertEqual(meta["android"]["fallback"], True)
            self.assertEqual(meta["ios"]["dynamic_url"], True)
            self.assertIn("fetching_icon", stages)
            self.assertIn("building_platforms", stages)
            self.assertIn("done", stages)
            android_mock.assert_called_once()
            ios_mock.assert_called_once()


class DistillerMacosLauncherTests(unittest.TestCase):
    def _build(self, name="My App", url="https://example.com"):
        import tempfile
        import zipfile
        from pathlib import Path

        distiller = Distiller()
        recipe = {"id": "abcd1234", "name": name}
        with tempfile.TemporaryDirectory() as tmp:
            distiller._build_macos(Path(tmp), recipe, None, url)
            entries = {}
            modes = {}
            with zipfile.ZipFile(Path(tmp) / "macos.zip") as z:
                for info in z.infolist():
                    entries[info.filename] = z.read(info.filename)
                    modes[info.filename] = (info.external_attr >> 16) & 0o7777
        return entries, modes

    def _launcher(self, entries, name="My App"):
        # Zip entry names are filesystem-sanitized at build time (issue #74).
        return entries[f"{_safe_fs_name(name)}.app/Contents/MacOS/launcher"].decode()

    def test_launcher_tries_webview_then_browser_fallbacks(self):
        import shlex

        entries, modes = self._build(url="https://example.com/x")
        launcher = self._launcher(entries)
        self.assertTrue(launcher.startswith("#!/bin/bash"))
        # Preferred path: native WKWebView helper inside our bundle identity,
        # then the JXA/osascript window, then Chromium app mode, then browser.
        self.assertIn("wta_webview", launcher)
        self.assertIn("/usr/bin/osascript -l JavaScript", launcher)
        self.assertIn(f"export WTA_URL={shlex.quote('https://example.com/x')}", launcher)
        self.assertLess(launcher.index("wta_webview"), launcher.index("osascript"))
        self.assertLess(launcher.index("osascript"), launcher.index("open -na"))
        self.assertIn('open "$WTA_URL"', launcher)
        self.assertGreater(launcher.index('open "$WTA_URL"'), launcher.index("open -na"))
        # The JXA fallback runtime ships inside the bundle and drives a real window.
        app_js = entries["My App.app/Contents/Resources/app.js"].decode()
        self.assertIn("WKWebView", app_js)
        self.assertIn("windowWillClose:", app_js)
        self.assertIn("WTA_URL", app_js)
        # Launcher stays executable through the zip round-trip.
        self.assertEqual(modes["My App.app/Contents/MacOS/launcher"], 0o755)

    def test_launcher_shell_quotes_names_and_urls(self):
        import shlex

        tricky_name = "Bob's \"App\""
        tricky_url = "https://example.com/?q=it's&a=$b"
        entries, _ = self._build(name=tricky_name, url=tricky_url)
        launcher = self._launcher(entries, name=tricky_name)
        # Entry dir is sanitized; env values keep the raw name via shlex.
        self.assertTrue(all(k.startswith(f"{_safe_fs_name(tricky_name)}.app/") for k in entries))
        self.assertIn(f"export WTA_URL={shlex.quote(tricky_url)}", launcher)
        self.assertIn(f"export WTA_NAME={shlex.quote(tricky_name)}", launcher)

    def test_webview_runtime_rejects_http_targets(self):
        entries, _ = self._build(url="http://example.com")
        app_js = entries["My App.app/Contents/Resources/app.js"].decode()
        # ATS blocks plain http inside WKWebView; app.js must bail out (non-zero
        # exit) so the shell launcher falls through to browser app mode.
        self.assertIn("requires an https target", app_js)

    def test_bundle_declares_ats_exception(self):
        entries, _ = self._build(url="http://example.com")
        plist = entries["My App.app/Contents/Info.plist"].decode()
        # http targets open in the standalone window thanks to the bundle-level
        # ATS exception (the compiled helper runs under our bundle identity).
        self.assertIn("NSAppTransportSecurity", plist)
        self.assertIn("NSAllowsArbitraryLoads", plist)

    @unittest.skipUnless(
        (_MACOS_TEMPLATE_DIR / _MACOS_HELPER_NAME).exists(),
        "prebuilt macOS helper not present on this platform",
    )
    def test_helper_binary_is_packed_executable(self):
        entries, modes = self._build()
        key = f"My App.app/Contents/MacOS/{_MACOS_HELPER_NAME}"
        blob = entries[key]
        self.assertEqual(modes[key], 0o755)
        # Universal binaries start with the fat-binary magic 0xCAFEBABE.
        self.assertEqual(blob[:4], b"\xca\xfe\xba\xbe")
        self.assertGreater(len(blob), 4096)


class DistillerDesktopWindowTests(unittest.TestCase):
    def _recipe(self, options):
        return {
            "id": "abcd1234",
            "name": "Example",
            "url": "https://example.com",
            "options": Distiller()._feature_options(options),
        }

    def _build_windows_bat(self, options):
        import tempfile
        import zipfile
        from pathlib import Path

        distiller = Distiller()
        with tempfile.TemporaryDirectory() as tmp:
            distiller._build_windows(Path(tmp), self._recipe(options), None, "https://example.com")
            with zipfile.ZipFile(Path(tmp) / "windows.zip") as z:
                return z.read("Example/Example.bat").decode()

    def _build_linux_desktop(self, options):
        import tarfile
        import tempfile
        from pathlib import Path

        distiller = Distiller()
        with tempfile.TemporaryDirectory() as tmp:
            distiller._build_linux(Path(tmp), self._recipe(options), None, "https://example.com")
            with tarfile.open(Path(tmp) / "linux.tar.gz") as t:
                member = t.extractfile("Example/Example.desktop")
                return member.read().decode()

    def test_default_launchers_have_no_window_flags(self):
        bat = self._build_windows_bat({})
        self.assertIn('--app="%URL%" --new-window & exit', bat)
        self.assertNotIn("--window-size", bat)
        self.assertNotIn("--start-maximized", bat)
        desktop = self._build_linux_desktop({})
        self.assertIn('exec "$b" --app="$URL"; done', desktop)
        self.assertNotIn("--window-size", desktop)
        self.assertNotIn("--start-maximized", desktop)

    def test_custom_size_flows_into_both_shells(self):
        options = {"windows-window-width": 1280, "windows-window-height": 800,
                   "linux-window-width": "1024", "linux-window-height": "768"}
        bat = self._build_windows_bat(options)
        self.assertIn("--window-size=1280,800", bat)
        self.assertNotIn("--window-size=1024,768", bat)
        desktop = self._build_linux_desktop(options)
        self.assertIn("--window-size=1024,768", desktop)
        self.assertNotIn("--window-size=1280,800", desktop)

    def test_maximized_wins_over_size(self):
        options = {"windows-window-width": 640, "windows-window-height": 480,
                   "windows-window-maximized": True}
        bat = self._build_windows_bat(options)
        self.assertIn("--start-maximized", bat)
        self.assertNotIn("--window-size", bat)

    def test_dimensions_clamped_and_garbage_ignored(self):
        distiller = Distiller()
        normalized = distiller._feature_options({
            "windows-window-width": 50,           # clamped to 320
            "windows-window-height": 99999,       # clamped to 7680
            "linux-window-width": "wide",         # garbage -> None
            "linux-window-height": "",
        })
        self.assertEqual(normalized["windows-window-width"], 320)
        self.assertEqual(normalized["windows-window-height"], 7680)
        self.assertIsNone(normalized["linux-window-width"])
        self.assertIsNone(normalized["linux-window-height"])
        self.assertIn("--window-size=320,7680", distiller._desktop_window_flags(normalized, "windows"))
        self.assertEqual(distiller._desktop_window_flags(normalized, "linux"), "")
        # Half a size is no size: no flag rather than a broken one.
        self.assertEqual(
            distiller._desktop_window_flags({"windows-window-width": 1280}, "windows"), ""
        )


class DistillerIconFallbackTests(unittest.TestCase):
    def test_blocked_page_keeps_service_fallbacks_within_limit(self):
        # Simulate a host the server cannot reach (e.g. foreign site behind
        # the GFW): the page fetch returns nothing, so the candidate list
        # falls back to well-known paths plus icon services. The services
        # must survive the candidate-limit truncation or such sites never
        # get an icon at all (issue #71).
        distiller = Distiller()

        def fake_fetch(url, timeout=8, use_cache=False):
            return None

        with patch.object(distiller, "_fetch_url_bytes", side_effect=fake_fetch):
            candidates = distiller._collect_icon_candidates("https://example.com")
        limit = distiller and 14  # matches the new default in config.icon_candidate_limit
        head = candidates[:14]
        self.assertIn("https://favicon.im/example.com", head)
        self.assertIn("https://favicon.yandex.net/favicon/example.com", head)
        self.assertIn("https://icons.duckduckgo.com/ip3/example.com.ico", head)
        self.assertIn("https://www.google.com/s2/favicons?domain=example.com&sz=256", head)

    def test_service_fallbacks_rank_below_page_icons(self):
        # Reachable page with a declared icon: service mirrors must rank
        # below the site's own candidates so we never prefer a third-party
        # proxy over the real thing.
        page_html = b'<link href="/apple-touch-icon.png" sizes="180x180" rel="apple-touch-icon">'
        distiller = Distiller()

        def fake_fetch(url, timeout=8, use_cache=False):
            if url == "https://example.com":
                return page_html
            return None

        with patch.object(distiller, "_fetch_url_bytes", side_effect=fake_fetch):
            candidates = distiller._collect_icon_candidates("https://example.com")
        self.assertEqual(candidates[0], "https://example.com/apple-touch-icon.png")


class DownloadPageHardeningTests(unittest.TestCase):
    """Generated page.html / pwa.html interpolate user-controlled recipe
    fields — every interpolation must be output-encoded (issue #73)."""

    def _page(self, **overrides):
        import tempfile
        from pathlib import Path

        recipe = {
            "id": "abcd1234", "name": "App", "url": "https://example.com",
            "color": "#7c3aed", "display": "fullscreen", "orientation": "any",
            "tags": [],
        }
        recipe.update(overrides)
        with tempfile.TemporaryDirectory() as tmp:
            return Distiller().render_download_page(Path(tmp), recipe)

    def test_recipe_fields_are_escaped(self):
        page = self._page(
            name='<img src=x onerror=alert(1)>',
            url='javascript:alert(document.domain)',
            color='#123"><svg onload=alert(1)>',
            tags=['<script>alert(1)</script>'],
        )
        self.assertIn('&lt;img src=x', page)
        self.assertNotIn('<img src=x onerror', page)
        self.assertNotIn('href="javascript:', page)
        self.assertIn('href="#"', page)
        # Bad color falls back to the default instead of breaking the attr.
        self.assertIn('content="#7c3aed"', page)
        self.assertIn('&lt;script&gt;', page)

    def test_script_breakout_is_neutralized(self):
        page = self._page(name='</script><script>alert(1)</script>')
        self.assertNotIn('</script><script>', page)
        self.assertIn('\\u003c', page)

    def test_csp_hash_pins_inline_script(self):
        import base64
        import hashlib
        import re as _re

        page = self._page()
        m = _re.search(r"script-src 'sha256-([A-Za-z0-9+/=]+)'", page)
        self.assertIsNotNone(m)
        body = _re.search(r"<script>(.*?)</script>", page, _re.S).group(1)
        self.assertEqual(
            base64.b64encode(hashlib.sha256(body.encode("utf-8")).digest()).decode("ascii"),
            m.group(1),
        )

    def test_pwa_shell_escapes_fields(self):
        import tempfile
        from pathlib import Path

        recipe = {
            "id": "abcd1234", "name": 'x</title><img onerror=1>',
            "url": "https://example.com", "color": 'red"><svg onload=1>',
            "display": "standalone", "orientation": "any",
        }
        with tempfile.TemporaryDirectory() as tmp:
            Distiller()._write_pwa_files(Path(tmp), recipe, "javascript:alert(1)")
            pwa = (Path(tmp) / "pwa.html").read_text()
        self.assertIn('&lt;/title&gt;', pwa)
        self.assertNotIn('src="javascript:', pwa)
        self.assertIn('src="#"', pwa)
        self.assertIn('sha256-', pwa)

    def test_pages_detect_browser_language(self):
        # First visit should follow navigator.languages, not hardcode English.
        import tempfile
        from pathlib import Path

        page = self._page()
        self.assertIn("navigator.languages", page)
        self.assertIn('tg.split("-")[0]', page)

        recipe = {
            "id": "abcd1234", "name": "App", "url": "https://example.com",
            "color": "#7c3aed", "display": "standalone", "orientation": "any",
        }
        with tempfile.TemporaryDirectory() as tmp:
            Distiller()._write_pwa_files(Path(tmp), recipe, "https://example.com")
            pwa = (Path(tmp) / "pwa.html").read_text()
        self.assertIn("navigator.languages", pwa)

    def test_page_mounts_community_scripts(self):
        # Download pages load the shared community component: mount point,
        # WTA_APP_ID bootstrap before the script, and 'self' in the CSP so
        # the external scripts run under the hash-pinned policy (issue #81).
        page = self._page()
        self.assertIn('id="community-sec"', page)
        self.assertIn('id="creator-card"', page)
        self.assertIn('id="comment-form"', page)
        self.assertIn("window.WTA_APP_ID", page)
        self.assertIn('/js/community.js', page)
        self.assertIn('/js/mdmini.js', page)
        import re as _re
        script_src = _re.search(r"script-src ([^;]+)", page).group(1)
        self.assertIn("'self'", script_src)
        self.assertIn("sha256-", script_src)
        # WTA_APP_ID must be assigned before community.js executes.
        self.assertLess(page.index("window.WTA_APP_ID"), page.index("/js/community.js"))


class ArtifactSanitizationTests(unittest.TestCase):
    """Recipe name/url land inside .bat/.desktop/install.sh/plist/zip+tar
    entries — every artifact context is encoded (issue #73 follow-up)."""

    def _windows_zip(self, name, url):
        import tempfile
        import zipfile
        from pathlib import Path

        distiller = Distiller()
        recipe = {"id": "abcd1234", "name": name, "options": {}}
        with tempfile.TemporaryDirectory() as tmp:
            distiller._build_windows(Path(tmp), recipe, None, url)
            with zipfile.ZipFile(Path(tmp) / "windows.zip") as z:
                return {i.filename: z.read(i.filename) for i in z.infolist()}

    def test_zip_entries_cannot_traverse(self):
        entries = self._windows_zip("../../evil", "https://x.test")
        for entry in entries:
            first = entry.split("/")[0]
            self.assertNotEqual(first, "..")
            self.assertFalse(entry.startswith("/"))
            self.assertNotIn("\\", entry)

    def test_bat_url_doubles_percent_and_drops_quote(self):
        entries = self._windows_zip("My App", 'https://x.test/?a=%2F&b=1"x')
        bat = entries["My App/My App.bat"].decode()
        self.assertIn('set "URL=https://x.test/?a=%%2F&b=1x"', bat)

    def test_bat_title_neutralizes_metachars(self):
        entries = self._windows_zip('n"& calc.exe', "https://x.test")
        bat = next(v.decode() for k, v in entries.items() if k.endswith(".bat"))
        title = next(line for line in bat.splitlines() if line.startswith("title"))
        self.assertNotIn("&", title)
        self.assertNotIn('"', title)

    def test_linux_artifacts_strip_shell_metas(self):
        import tarfile
        import tempfile
        from pathlib import Path

        distiller = Distiller()
        recipe = {"id": "abcd1234", "name": 'x"$(touch /tmp/pwned)`', "options": {}}
        with tempfile.TemporaryDirectory() as tmp:
            distiller._build_linux(Path(tmp), recipe, None, "https://x.test/")
            with tarfile.open(Path(tmp) / "linux.tar.gz") as t:
                names = t.getnames()
                desktop = t.extractfile(next(n for n in names if n.endswith(".desktop"))).read().decode()
                install = t.extractfile(next(n for n in names if n.endswith("install.sh"))).read().decode()
        self.assertFalse(any("$" in n or "`" in n or '"' in n for n in names))
        self.assertNotIn("$(touch", install)

    def test_desktop_name_cannot_inject_keys(self):
        import tarfile
        import tempfile
        from pathlib import Path

        distiller = Distiller()
        recipe = {"id": "abcd1234", "name": "a\nExec=sh -c evil\nX", "options": {}}
        with tempfile.TemporaryDirectory() as tmp:
            distiller._build_linux(Path(tmp), recipe, None, "https://x.test/")
            with tarfile.open(Path(tmp) / "linux.tar.gz") as t:
                names = t.getnames()
                desktop = t.extractfile(next(n for n in names if n.endswith(".desktop"))).read().decode()
        self.assertEqual(desktop.count("\nExec="), 1)  # only the real Exec line
        self.assertNotIn("\nExec=sh -c evil", desktop)

    def test_mobileconfig_escapes_name_and_sanitizes_id(self):
        import tempfile
        from pathlib import Path

        distiller = Distiller()
        recipe = {
            "id": "ab..cd", "name": 'a</string></dict><key>Injected</key><true/>',
            "url": "https://x.test", "color": "#7c3aed", "orientation": "any",
        }
        with tempfile.TemporaryDirectory() as tmp:
            distiller._build_ios(Path(tmp), recipe, None, base_url=None)
            cfg = (Path(tmp) / "ios.mobileconfig").read_bytes()
        self.assertNotIn(b"</dict><key>Injected</key>", cfg)
        self.assertIn(b"&lt;/dict&gt;", cfg)
        self.assertIn(b"com.webtoapp.abcd.clip", cfg)

    def test_mobileconfig_points_clip_directly_at_target(self):
        """A FullScreen clip that 302s cross-origin (via /launch) gets pushed
        into Safari instead of running standalone — the clip URL must be the
        target itself."""
        import tempfile
        from pathlib import Path

        distiller = Distiller()
        recipe = {"id": "zz123abc", "name": "App", "url": "https://target.test/x", "color": "#000000"}
        with tempfile.TemporaryDirectory() as tmp:
            meta = distiller._build_ios(Path(tmp), recipe, None, base_url="https://ours.test")
            cfg = (Path(tmp) / "ios.mobileconfig").read_bytes()
        self.assertIn(b"<key>URL</key><string>https://target.test/x</string>", cfg)
        self.assertNotIn(b"/launch", cfg)
        self.assertFalse(meta["dynamic_url"])

    def test_android_fallback_escapes_and_sanitizes(self):
        import tempfile
        import zipfile
        from pathlib import Path
        from server.engine.apk_builder import ApkBuilder

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "android.zip"
            ApkBuilder().build_fallback(
                str(out), 'javascript:alert(1)', '../../x<img onerror=1>', None, 'red"><svg>'
            )
            with zipfile.ZipFile(out) as z:
                entries = {i.filename: z.read(i.filename) for i in z.infolist()}
        for entry in entries:
            self.assertNotEqual(entry.split("/")[0], "..")
        index = next(v.decode() for k, v in entries.items() if k.endswith("index.html"))
        self.assertNotIn("javascript:", index)
        self.assertIn('src="about:blank"', index)
        self.assertIn("&lt;img onerror=1&gt;", index)


class AppDescriptionTests(unittest.TestCase):
    """Optional per-app description: sanitized into the recipe, rendered on
    the download page, and exposed on market snapshots (issue #98)."""

    def test_description_sanitized_into_recipe(self):
        recipe = Distiller().create_recipe(
            app_id="desc0001", url="https://example.com", name="App",
            color="#7c3aed", display="fullscreen", orientation="any",
            options={"description": "  hello   world \n next  " + "x" * 200},
        )
        desc = recipe["description"]
        self.assertEqual(desc[:11], "hello world")
        self.assertLessEqual(len(desc), 80)
        self.assertNotIn("\n", desc)

    def test_description_defaults_empty(self):
        recipe = Distiller().create_recipe(
            app_id="desc0002", url="https://example.com", name="App",
            color="#7c3aed", display="fullscreen", orientation="any",
            options={},
        )
        self.assertEqual(recipe["description"], "")

    def test_page_shows_description_when_present(self):
        page = DownloadPageHardeningTests()._page(
            description="A tiny RSS reader")
        self.assertIn('<p class="app-desc">A tiny RSS reader</p>', page)

    def test_page_omits_element_without_description(self):
        page = DownloadPageHardeningTests()._page()
        self.assertNotIn('class="app-desc"', page)

    def test_description_is_escaped(self):
        page = DownloadPageHardeningTests()._page(
            description='<img src=x onerror=alert(1)>')
        self.assertNotIn('<img src=x', page)
        self.assertIn("&lt;img src=x", page)


class DownloadPageLayoutTests(unittest.TestCase):
    """Verbose prose is folded into <details>; key info stays visible."""

    def _page(self):
        return DownloadPageHardeningTests()._page(description="A demo app")

    def test_prose_is_collapsed_not_inline(self):
        page = self._page()
        body = page[page.find("<body>"):]
        self.assertIn('<details class="fold">', body)
        self.assertIn('data-i18n="aboutTitle"', body)
        self.assertIn('ios-fold', body)
        self.assertNotIn('class="desc"', body)
        self.assertNotIn('class="footnote"', body)
        self.assertNotIn('app-sub', body)

    def test_platforms_render_before_ios_fold(self):
        page = self._page()
        body = page[page.find("<body>"):]
        self.assertLess(body.find('class="platforms"'), body.find('ios-fold'))
        self.assertLess(body.find('id="community-sec"'), body.find('class="hero-panel"'))


class IconPipelineTests(unittest.TestCase):
    """Icon normalization accepts every raster format Pillow reads, and ICO
    decodes its largest frame (legacy BMP-encoded entries included)."""

    def _png_dim(self, png):
        return int.from_bytes(png[16:20], "big")

    def test_ico_largest_frame_wins(self):
        import io
        from PIL import Image
        big = Image.new("RGBA", (128, 128), (255, 0, 0, 255))
        buf = io.BytesIO()
        big.save(buf, format="ICO", sizes=[(16, 16), (128, 128)])
        png = Distiller()._normalize_to_png(buf.getvalue())
        self.assertIsNotNone(png)
        self.assertEqual(self._png_dim(png), 128)

    def test_jpeg_accepted(self):
        import io
        from PIL import Image
        buf = io.BytesIO()
        Image.new("RGB", (64, 64), (0, 128, 255)).save(buf, format="JPEG")
        png = Distiller()._normalize_to_png(buf.getvalue())
        self.assertIsNotNone(png)
        self.assertEqual(png[:4], b"\x89PNG")

    def test_svg_rejected(self):
        self.assertIsNone(Distiller()._normalize_to_png(b"<svg xmlns='x'></svg>"))

    def test_icon_miss_uses_short_cache(self):
        from server.engine import cache as cache_mod
        from unittest.mock import patch
        d = Distiller()
        recipe = {"url": "https://nohost.invalid/", "color": "#123456"}
        with patch.object(d, "_collect_icon_candidates", return_value=[]), \
             patch.object(d, "_choose_best_icon", return_value=None), \
             patch.object(cache_mod.icon_cache, "get", return_value=None):
            first = d._fetch_icon(recipe)
            self.assertIsNotNone(first)  # placeholder PNG
            # Second call inside the miss window must not re-sweep.
            with patch.object(d, "_collect_icon_candidates",
                              side_effect=AssertionError("re-swept")):
                second = d._fetch_icon(recipe)
            self.assertIsNotNone(second)


def _png_bytes(size=(40, 30), fmt="PNG", color=(10, 120, 200, 255)):
    import io
    from PIL import Image
    im = Image.new("RGBA", size, color)
    buf = io.BytesIO()
    im.save(buf, fmt)
    return buf.getvalue()


def _data_url(raw: bytes, mime="image/png") -> str:
    import base64
    return f"data:{mime};base64,{base64.b64encode(raw).decode()}"


class DistillerAboutContentTests(unittest.TestCase):
    """Creator-authored about-fold text + images (option _about_text /
    _about_images → persisted recipe.about + about-N.webp files)."""

    def _build(self, options, app_id="about01"):
        import tempfile
        from pathlib import Path

        distiller = Distiller()
        recipe = distiller.create_recipe(
            app_id=app_id,
            url="https://example.com",
            name="About App",
            color="#123456",
            display="browser",
            orientation="any",
            options=options,
        )
        tmp = tempfile.TemporaryDirectory()
        app_dir = Path(tmp.name) / app_id
        with patch.object(distiller, "_fetch_icon", return_value=distiller._make_placeholder_png("#123456")):
            with patch.object(distiller, "_build_android", return_value={"apk": False, "fallback": True}):
                with patch.object(distiller, "_build_ios", return_value={"signed": False, "dynamic_url": True}):
                    distiller.write_app_files(app_dir, recipe, base_url="https://service.test")
        page = (app_dir / "page.html").read_text()
        return distiller, recipe, app_dir, page, tmp

    def test_default_about_empty_for_old_recipes(self):
        _d, recipe, _dir, page, tmp = self._build({})
        self.addCleanup(tmp.cleanup)
        self.assertEqual(recipe["about"], {"text": "", "images": []})
        self.assertNotIn('<p class="about-text"', page)
        self.assertNotIn('class="about-imgs"', page)

    def test_text_escaped_and_paragraphs_split(self):
        _d, recipe, _dir, page, tmp = self._build(
            {"about-text": "Hello <script>x</script> world\n\nSecond para"}
        )
        self.addCleanup(tmp.cleanup)
        self.assertIn('<p class="about-text">Hello &lt;script&gt;x&lt;/script&gt; world</p>', page)
        self.assertIn('<p class="about-text">Second para</p>', page)
        self.assertNotIn("<script>x</script>", page)
        self.assertEqual(recipe["about"]["text"], "Hello <script>x</script> world\n\nSecond para")

    def test_images_normalized_webp_and_referenced(self):
        imgs = [_data_url(_png_bytes((64, 48))), _data_url(_png_bytes((1200, 900)))]
        _d, recipe, app_dir, page, tmp = self._build({"about-images": imgs})
        self.addCleanup(tmp.cleanup)
        self.assertEqual(recipe["about"]["images"], ["about-1.webp", "about-2.webp"])
        for i in (1, 2):
            f = app_dir / f"about-{i}.webp"
            self.assertTrue(f.exists())
            self.assertLessEqual(f.stat().st_size, 800 * 1024)
            self.assertTrue(f.read_bytes().startswith(b"RIFF"))
        self.assertIn("/a/about01/about/about-1.webp", page)
        self.assertIn('class="about-imgs"', page)

    def test_invalid_dropped_and_capped_at_three(self):
        import base64
        imgs = [
            "data:image/png;base64," + base64.b64encode(b"not an image").decode(),
            _data_url(_png_bytes((32, 32))),
            _data_url(_png_bytes((33, 33))),
            _data_url(_png_bytes((34, 34))),
            _data_url(_png_bytes((35, 35))),
        ]
        _d, recipe, app_dir, page, tmp = self._build({"about-images": imgs})
        self.addCleanup(tmp.cleanup)
        self.assertEqual(len(recipe["about"]["images"]), 3)
        self.assertTrue((app_dir / "about-3.webp").exists())
        self.assertFalse((app_dir / "about-4.webp").exists())

    def test_oversized_pixel_image_rejected(self):
        # 9MP image is fine — it gets downscaled, not dropped. Rejection is
        # reserved for decompression-bomb territory (ABOUT_MAX_PIXELS).
        _d, recipe, app_dir, page, tmp = self._build(
            {"about-images": [_data_url(_png_bytes((3000, 3000)))]}
        )
        self.addCleanup(tmp.cleanup)
        self.assertEqual(len(recipe["about"]["images"]), 1)
        with patch.object(Distiller, "ABOUT_MAX_PIXELS", 1_000_000):
            _d, recipe, _dir2, page2, tmp2 = self._build(
                {"about-images": [_data_url(_png_bytes((3000, 3000)))]}, app_id="about02"
            )
            self.addCleanup(tmp2.cleanup)
        self.assertEqual(recipe["about"]["images"], [])
        self.assertNotIn('class="about-imgs"', page2)

    def test_rebuild_keeps_stored_images_when_untouched(self):
        imgs = [_data_url(_png_bytes((64, 48)))]
        distiller, recipe, app_dir, page, tmp = self._build({"about-images": imgs})
        self.addCleanup(tmp.cleanup)
        stored = (app_dir / "about-1.webp").read_bytes()
        # Rebuild with a history recipe: no _about_* keys, about already set.
        recipe2 = dict(recipe)
        recipe2.pop("_about_text", None)
        recipe2.pop("_about_images", None)
        with patch.object(distiller, "_fetch_icon", return_value=distiller._make_placeholder_png("#123456")):
            with patch.object(distiller, "_build_android", return_value={"apk": False, "fallback": True}):
                with patch.object(distiller, "_build_ios", return_value={"signed": False, "dynamic_url": True}):
                    distiller.write_app_files(app_dir, recipe2, base_url="https://service.test")
        self.assertEqual((app_dir / "about-1.webp").read_bytes(), stored)
        self.assertIn("about-1.webp", (app_dir / "page.html").read_text())

    def test_clear_images_with_empty_list(self):
        imgs = [_data_url(_png_bytes((64, 48)))]
        distiller, recipe, app_dir, page, tmp = self._build({"about-images": imgs})
        self.addCleanup(tmp.cleanup)
        recipe2 = dict(recipe)
        recipe2["_about_images"] = []
        with patch.object(distiller, "_fetch_icon", return_value=distiller._make_placeholder_png("#123456")):
            with patch.object(distiller, "_build_android", return_value={"apk": False, "fallback": True}):
                with patch.object(distiller, "_build_ios", return_value={"signed": False, "dynamic_url": True}):
                    distiller.write_app_files(app_dir, recipe2, base_url="https://service.test")
        self.assertFalse((app_dir / "about-1.webp").exists())
        self.assertEqual(recipe2["about"]["images"], [])
