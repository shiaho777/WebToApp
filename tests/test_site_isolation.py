"""Isolation of uploaded HTML-app content from the API origin (issue #20).

With SITE_PUBLIC_BASE_URL configured, uploaded pages must execute on that
host only: the main origin 301-redirects /a/<id>/site/ requests there, and
generated recipe URLs point at the isolated host. Without it, legacy
main-origin behaviour is preserved.
"""

import os
import unittest
from unittest import mock

from fastapi.testclient import TestClient

from server import config, main

SANDBOX = "https://s.origin.test"
ORIGIN = "origin.test"


class HtmlSitePublicBaseTests(unittest.TestCase):
    def test_configured_base_wins_over_request_origin(self):
        with mock.patch.dict(os.environ, {"SITE_PUBLIC_BASE_URL": SANDBOX}):
            self.assertEqual(main._html_site_public_base("https://other.test"), SANDBOX)

    def test_unconfigured_falls_back_to_request_origin(self):
        with mock.patch.dict(os.environ, {"SITE_PUBLIC_BASE_URL": ""}):
            self.assertEqual(main._html_site_public_base("https://other.test"), "https://other.test")
            self.assertEqual(main._html_site_public_base(""), "")

    def test_config_strips_trailing_slash(self):
        with mock.patch.dict(os.environ, {"SITE_PUBLIC_BASE_URL": SANDBOX + "/"}):
            self.assertEqual(config.site_public_base_url(), SANDBOX)


class ServeAppSiteIsolationTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)

    def test_foreign_host_is_redirected_to_sandbox(self):
        with mock.patch.dict(os.environ, {"SITE_PUBLIC_BASE_URL": SANDBOX}):
            resp = self.client.get(
                "/a/someapp/site/index.html",
                headers={"Host": ORIGIN},
                follow_redirects=False,
            )
        self.assertEqual(resp.status_code, 301)
        self.assertEqual(resp.headers["location"], f"{SANDBOX}/a/someapp/site/index.html")

    def test_redirect_preserves_query_string(self):
        with mock.patch.dict(os.environ, {"SITE_PUBLIC_BASE_URL": SANDBOX}):
            resp = self.client.get(
                "/a/someapp/site/app.js",
                params={"v": "2"},
                headers={"Host": ORIGIN},
                follow_redirects=False,
            )
        self.assertEqual(resp.status_code, 301)
        self.assertEqual(resp.headers["location"], f"{SANDBOX}/a/someapp/site/app.js?v=2")

    def test_sandbox_host_reaches_serving_logic(self):
        # Matching host: no redirect — the request proceeds to the serving
        # logic and fails with 404 for an app that does not exist locally.
        with mock.patch.dict(os.environ, {"SITE_PUBLIC_BASE_URL": SANDBOX}):
            resp = self.client.get(
                "/a/nonexistent/site/index.html",
                headers={"Host": "s.origin.test"},
                follow_redirects=False,
            )
        self.assertEqual(resp.status_code, 404)

    def test_unconfigured_fails_closed(self):
        # #238: without an isolated origin, serving uploaded content is
        # refused outright (503) instead of running same-origin with the API.
        with mock.patch.dict(os.environ, {"SITE_PUBLIC_BASE_URL": "", "SITE_ALLOW_SAME_ORIGIN": ""}):
            resp = self.client.get(
                "/a/nonexistent/site/index.html",
                headers={"Host": ORIGIN},
                follow_redirects=False,
            )
        self.assertEqual(resp.status_code, 503)

    def test_unconfigured_with_explicit_opt_in_serves_legacy(self):
        with mock.patch.dict(os.environ, {"SITE_PUBLIC_BASE_URL": "", "SITE_ALLOW_SAME_ORIGIN": "1"}):
            resp = self.client.get(
                "/a/nonexistent/site/index.html",
                headers={"Host": ORIGIN},
                follow_redirects=False,
            )
        self.assertEqual(resp.status_code, 404)  # reached serving logic

    def test_gateway_key_bypasses_redirect(self):
        env = {"SITE_PUBLIC_BASE_URL": SANDBOX, "SITE_ORIGIN_KEY": "s3cret"}
        with mock.patch.dict(os.environ, env):
            resp = self.client.get(
                "/a/nonexistent/site/index.html",
                headers={"Host": ORIGIN, "X-Site-Origin-Key": "s3cret"},
                follow_redirects=False,
            )
        self.assertEqual(resp.status_code, 404)  # reached serving logic, no redirect

    def test_wrong_gateway_key_still_redirects(self):
        env = {"SITE_PUBLIC_BASE_URL": SANDBOX, "SITE_ORIGIN_KEY": "s3cret"}
        with mock.patch.dict(os.environ, env):
            resp = self.client.get(
                "/a/nonexistent/site/index.html",
                headers={"Host": ORIGIN, "X-Site-Origin-Key": "nope"},
                follow_redirects=False,
            )
            self.assertEqual(resp.status_code, 301)
        # No key configured on the server side: any header must be ignored.
        with mock.patch.dict(os.environ, {"SITE_PUBLIC_BASE_URL": SANDBOX, "SITE_ORIGIN_KEY": ""}):
            resp = self.client.get(
                "/a/nonexistent/site/index.html",
                headers={"Host": ORIGIN, "X-Site-Origin-Key": "s3cret"},
                follow_redirects=False,
            )
        self.assertEqual(resp.status_code, 301)


if __name__ == "__main__":
    unittest.main()
