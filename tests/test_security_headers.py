"""App-level security headers (#238): every response carries anti-framing,
nosniff and referrer policy; HSTS on HTTPS; hosted user content is denied
framing outright. Independent of any CDN edge configuration.
"""

import os
import unittest
from unittest import mock

from fastapi.testclient import TestClient

from server import main


class SecurityHeaderTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)

    def test_homepage_carries_baseline_headers(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers["x-content-type-options"], "nosniff")
        self.assertEqual(resp.headers["referrer-policy"], "strict-origin-when-cross-origin")
        self.assertEqual(resp.headers["x-frame-options"], "SAMEORIGIN")
        self.assertEqual(resp.headers["content-security-policy"], "frame-ancestors 'self'")

    def test_plain_http_has_no_hsts(self):
        resp = self.client.get("/")
        self.assertNotIn("strict-transport-security", resp.headers)

    def test_https_request_gets_hsts(self):
        resp = self.client.get("/", headers={"X-Forwarded-Proto": "https"})
        # TestClient peer is not a trusted proxy, so the header must NOT be
        # honored from an untrusted source.
        self.assertNotIn("strict-transport-security", resp.headers)
        with mock.patch.object(main, "_request_is_from_trusted_proxy", return_value=True):
            resp = self.client.get("/", headers={"X-Forwarded-Proto": "https"})
        self.assertEqual(
            resp.headers["strict-transport-security"],
            "max-age=31536000; includeSubDomains; preload",
        )

    def test_api_responses_also_covered(self):
        resp = self.client.get("/api/stats")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers["x-content-type-options"], "nosniff")
        self.assertIn("frame-ancestors", resp.headers["content-security-policy"])

    def test_hosted_site_content_denies_framing(self):
        # Legacy opt-in so the serving path is reachable; the header policy
        # must still deny framing for user content.
        with mock.patch.dict(os.environ, {"SITE_ALLOW_SAME_ORIGIN": "1"}):
            resp = self.client.get("/a/nonexistent/site/index.html")
        self.assertEqual(resp.status_code, 404)  # app absent, but headers apply
        self.assertEqual(resp.headers["x-frame-options"], "DENY")
        self.assertEqual(resp.headers["content-security-policy"], "frame-ancestors 'none'")

    def test_error_responses_covered(self):
        resp = self.client.get("/a/zzzzzzzz")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.headers["x-content-type-options"], "nosniff")
        self.assertIn("content-security-policy", resp.headers)


if __name__ == "__main__":
    unittest.main()