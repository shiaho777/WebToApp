import asyncio
import unittest
from unittest.mock import patch

from server.engine.analyzer import SiteAnalyzer


class AnalyzerParsingTests(unittest.TestCase):
    def test_analyze_html_uses_structured_parser(self):
        html = """
        <html>
          <head>
            <meta content="Structured Description" property="og:description">
            <meta content="Example Suite" property="og:site_name">
            <meta content="#112233" name="theme-color">
            <link href="/favicon-192.png" sizes="192x192" rel="shortcut icon">
            <script src="https://static.example.com/app.js"></script>
            <script src="https://www.googletagmanager.com/gtm.js"></script>
            <script>console.log("inline")</script>
            <style>body { color: red; }</style>
            <title>Example Suite | Portal</title>
          </head>
          <body>
            <div class="cookie-banner">cookie</div>
          </body>
        </html>
        """
        analyzer = SiteAnalyzer()
        with patch.object(analyzer, "_favicon_data_url", return_value=""):
            result = asyncio.run(analyzer._analyze_html("https://example.com/path", html, len(html.encode("utf-8"))))
        self.assertEqual(result["title"], "Example Suite | Portal")
        self.assertEqual(result["siteName"], "Example Suite")
        self.assertEqual(result["description"], "Structured Description")
        self.assertEqual(result["themeColor"], "#112233")
        self.assertEqual(result["favicon"], "https://example.com/favicon-192.png")
        self.assertEqual(result["totalScripts"], 2)
        self.assertEqual(result["trackers"], 1)
        self.assertEqual(result["popups"], 1)


class AuthWallDetectionTests(unittest.TestCase):
    """Sites behind Authelia / Cloudflare Access redirect the server-side fetch
    to a login portal. The analyzer must detect that and report a structured
    auth-protected result instead of analyzing the login page."""

    def _make_response(self, status_code=302, location=None, set_cookie=None):
        import httpx
        headers = {}
        if location is not None:
            headers["location"] = location
        if set_cookie is not None:
            headers["set-cookie"] = set_cookie
        return httpx.Response(status_code, headers=headers, request=httpx.Request("GET", "https://app.example.com"))

    def test_detect_cloudflare_access_redirect(self):
        from server.engine.analyzer import _detect_auth_wall
        resp = self._make_response(location="https://acme.cloudflareaccess.com/cdn-cgi/access/login/abc")
        self.assertEqual(_detect_auth_wall(resp, "https://acme.cloudflareaccess.com/cdn-cgi/access/login/abc"), "cloudflare_access")

    def test_detect_authelia_redirect(self):
        from server.engine.analyzer import _detect_auth_wall
        resp = self._make_response(location="https://auth.example.com/auth/?rd=https%3A%2F%2Fapp.example.com")
        self.assertEqual(_detect_auth_wall(resp, "https://auth.example.com/auth/?rd=https%3A%2F%2Fapp.example.com"), "authelia")

    def test_detect_cloudflare_access_cookie(self):
        from server.engine.analyzer import _detect_auth_wall
        resp = self._make_response(set_cookie="CF_Authorization=eyJabc; Path=/; HttpOnly")
        self.assertEqual(_detect_auth_wall(resp, ""), "cloudflare_access")

    def test_detect_authelia_cookie(self):
        from server.engine.analyzer import _detect_auth_wall
        resp = self._make_response(set_cookie="authelia_session=xyz; Path=/; HttpOnly")
        self.assertEqual(_detect_auth_wall(resp, ""), "authelia")

    def test_no_auth_wall_for_normal_redirect(self):
        from server.engine.analyzer import _detect_auth_wall
        resp = self._make_response(location="https://www.example.com/")
        self.assertEqual(_detect_auth_wall(resp, "https://www.example.com/"), "")

    def test_analyze_returns_auth_protected_result(self):
        """End-to-end: a redirect to an auth portal yields authProtected=True
        with a host-derived name and empty HTML (no login page analyzed)."""
        analyzer = SiteAnalyzer()
        async def fake_fetch(url):
            return ("https://app.example.com", "", 0, b"", "authelia")
        with patch.object(analyzer, "_fetch_page", side_effect=fake_fetch):
            result = asyncio.run(analyzer.analyze("https://app.example.com"))
        self.assertTrue(result["authProtected"])
        self.assertEqual(result["authProvider"], "authelia")
        self.assertEqual(result["suggestedName"], "App")
        self.assertEqual(result["originalSize"], "N/A")
        self.assertEqual(result["ads"], 0)

