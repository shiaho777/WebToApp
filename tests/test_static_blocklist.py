"""Regression guards for the sensitive-path blocklist (issue #18).

StaticFiles resolves '//server/x' on disk just like '/server/x', so the
blocklist must judge a normalized path — matching the raw string let doubled
slashes evade every prefix rule and serve recipe.json (edit tokens), keystore
password manifests and server source.
"""

import asyncio
import unittest

from server import main


class NormalizeRequestPathTests(unittest.TestCase):
    def test_collapses_duplicate_and_trailing_slashes(self):
        self.assertEqual(main._normalize_request_path("//server//main.py"), "/server/main.py")
        self.assertEqual(main._normalize_request_path("///generated/abc/"), "/generated/abc")
        self.assertEqual(main._normalize_request_path("/Index.HTML"), "/index.html")
        self.assertEqual(main._normalize_request_path(""), "")
        self.assertEqual(main._normalize_request_path(None), "")


class SensitivePathTests(unittest.TestCase):
    def test_prefix_rules_survive_doubled_slashes(self):
        for path in (
            "/server/main.py",
            "//server/main.py",
            "///server/config.py",
            "//certs/app-keys/abc.json",
            "//.git/HEAD",
            "/generated/abc/recipe.json",
            "//generated/_tasks.sqlite3",
        ):
            with self.subTest(path=path):
                assert main._is_sensitive_path(path)

    def test_suffix_rules(self):
        for path in (
            "/webtoapp.env",
            "/deep/nested/backup.bak",
            "/data.sqlite3",
            "/debug.log",
            "//certs/android-template.keystore",
        ):
            with self.subTest(path=path):
                assert main._is_sensitive_path(path)

    def test_allowlist_blocks_unknown_static_paths(self):
        # The catch-all mount is rooted at the whole project dir; anything
        # outside the frontend allowlist must never reach StaticFiles.
        for path in (
            "/.venv/lib/python3.12/site-packages/httpx/__init__.py",
            "//.venv/pyvenv.cfg",
            "/venv/bin/activate",
            "/tests/test_main.py",
            "/.pytest_cache/v/cache/lastfailed",
            "/README.md",
            "/AGENTS.md",
            "/docker-compose.yml",
            "/docs/DEPLOY.md",
            "/.github/workflows/ci.yml",
        ):
            with self.subTest(path=path):
                assert main._is_sensitive_path(path)

    def test_legitimate_paths_still_pass(self):
        for path in (
            "/",
            "/index.html",
            "/css/style.css",
            "/js/app.v5.js",
            "/assets/screenshot-1.png",
            "/a/abc123/manifest.json",  # legit route ending in .json
            "/healthz",
        ):
            with self.subTest(path=path):
                assert not main._is_sensitive_path(path)


class MiddlewareWiringTests(unittest.TestCase):
    """End-to-end through the ASGI app, so a future refactor cannot silently
    unwire the blocklist from the middleware stack."""

    @staticmethod
    def _status_for(path: str) -> int:
        async def call() -> int:
            status = {"code": None}

            async def receive():
                return {"type": "http.request"}

            async def send(message):
                if message["type"] == "http.response.start":
                    status["code"] = message["status"]

            scope = {
                "type": "http",
                "asgi": {"version": "3.0", "spec_version": "2.3"},
                "http_version": "1.1",
                "method": "GET",
                "scheme": "http",
                "path": path,
                "raw_path": path.encode(),
                "query_string": b"",
                "headers": [(b"host", b"testserver")],
                "client": ("127.0.0.1", 12345),
                "server": ("testserver", 80),
            }
            await main.app(scope, receive, send)
            return status["code"] or 0

        return asyncio.run(call())

    def test_doubled_slash_sensitive_path_is_hard_404(self):
        self.assertEqual(self._status_for("//server/main.py"), 404)
        self.assertEqual(self._status_for("//generated/abc/recipe.json"), 404)

    def test_plain_sensitive_path_is_hard_404(self):
        self.assertEqual(self._status_for("/webtoapp.env"), 404)

    def test_homepage_still_serves(self):
        self.assertEqual(self._status_for("/index.html"), 200)

    def test_unknown_project_paths_are_hard_404(self):
        self.assertEqual(self._status_for("/.venv/pyvenv.cfg"), 404)
        self.assertEqual(self._status_for("/tests/test_main.py"), 404)
        self.assertEqual(self._status_for("/README.md"), 404)


if __name__ == "__main__":
    unittest.main()
