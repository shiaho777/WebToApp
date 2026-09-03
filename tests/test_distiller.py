import unittest
from unittest.mock import patch

from server.engine.distiller import Distiller, _MACOS_HELPER_NAME, _MACOS_TEMPLATE_DIR


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
        return entries[f"{name}.app/Contents/MacOS/launcher"].decode()

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
