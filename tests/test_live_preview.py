"""Regression guards for the live WebView-style preview (#175)."""

import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from server import main


class LivePreviewHtmlTests(unittest.TestCase):
    def test_injects_base_and_removes_frame_blockers(self):
        markup = (
            '<html><head>'
            '<meta http-equiv="Content-Security-Policy" content="frame-ancestors none">'
            '<base href="/old/">'
            '<meta http-equiv="refresh" content="0;url=/next">'
            '</head><body><a href="/page">Page</a></body></html>'
        )
        out = main._prepare_live_preview_html(markup, "https://example.com/a?b=1&c=2")
        self.assertIn('<base href="https://example.com/a?b=1&amp;c=2">', out)
        self.assertNotIn("frame-ancestors", out)
        self.assertNotIn("http-equiv=\"refresh\"", out)
        self.assertEqual(out.count("<base"), 1)
        self.assertIn("window.open", out)

    def test_injects_base_when_page_has_no_head(self):
        out = main._prepare_live_preview_html("<p>hello</p>", "https://example.com/")
        self.assertTrue(out.startswith('<base href="https://example.com/">'))
        self.assertIn("<p>hello</p>", out)


class LivePreviewEndpointTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)
        main._LIVE_PREVIEW_CACHE.clear()

    def test_returns_sandboxed_html(self):
        prepared = "<html><head></head><body>ok</body></html>"
        with patch.object(main, "_live_preview_html", new=AsyncMock(return_value=(prepared, "https://example.com/"))):
            resp = self.client.get(
                "/api/live-preview",
                params={"url": "https://example.com/"},
                headers={"sec-fetch-dest": "empty"},
            )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.text, prepared)
        self.assertIn("sandbox", resp.headers["content-security-policy"])
        self.assertIn("allow-scripts", resp.headers["content-security-policy"])
        self.assertEqual(resp.headers["x-robots-tag"], "noindex, nofollow")
        self.assertEqual(resp.headers["referrer-policy"], "no-referrer")

    def test_rejects_top_level_document(self):
        resp = self.client.get(
            "/api/live-preview",
            params={"url": "https://example.com/"},
            headers={"sec-fetch-dest": "document"},
        )
        self.assertEqual(resp.status_code, 403)

    def test_rejects_private_target(self):
        resp = self.client.get(
            "/api/live-preview",
            params={"url": "http://127.0.0.1/"},
            headers={"sec-fetch-dest": "empty"},
        )
        self.assertEqual(resp.status_code, 400)

    def test_rejects_non_html_response(self):
        with patch.object(
            main,
            "_live_preview_html",
            new=AsyncMock(side_effect=main.HTTPException(status_code=415, detail="not html")),
        ):
            resp = self.client.get(
                "/api/live-preview",
                params={"url": "https://example.com/file.pdf"},
                headers={"sec-fetch-dest": "empty"},
            )
        self.assertEqual(resp.status_code, 415)


if __name__ == "__main__":
    unittest.main()
