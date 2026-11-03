"""Regression guards for the selective gzip middleware (issue #161)."""

import unittest

from starlette.applications import Starlette
from starlette.responses import Response, StreamingResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from server import main
from server.compression import TextCompressionMiddleware, accepts_gzip, is_compressible

TEXT = ("body { color: #1e1914; }\n" * 400).encode()
BINARY = bytes(range(256)) * 40


def _text(request):
    return Response(TEXT, media_type="text/css", headers={"ETag": '"abc"'})


def _tiny(request):
    return Response(b"ok", media_type="text/plain")


def _binary(request):
    return Response(BINARY, media_type="application/vnd.android.package-archive")


def _encoded(request):
    return Response(TEXT, media_type="text/css", headers={"Content-Encoding": "br"})


def _missing(request):
    return Response(TEXT, status_code=404, media_type="text/html")


def _stream(request):
    async def chunks():
        for _ in range(3):
            yield TEXT[:2048]

    return StreamingResponse(chunks(), media_type="application/javascript")


def _client(**options):
    app = Starlette(routes=[
        Route("/text", _text),
        Route("/tiny", _tiny),
        Route("/binary", _binary),
        Route("/encoded", _encoded),
        Route("/missing", _missing),
        Route("/stream", _stream),
    ])
    app.add_middleware(TextCompressionMiddleware, **options)
    return TestClient(app)


class AcceptsGzipTests(unittest.TestCase):
    def test_parses_accept_encoding(self):
        cases = {
            "gzip": True,
            "br, gzip;q=0.5": True,
            "GZIP": True,
            "*": True,
            "gzip;q=0": False,
            "gzip; q=0.0": False,
            "gzip;q=nope": False,
            "identity": False,
            "br": False,
            "": False,
            None: False,
        }
        for header, expected in cases.items():
            with self.subTest(header=header):
                self.assertIs(accepts_gzip(header), expected)


class IsCompressibleTests(unittest.TestCase):
    def test_only_text_like_types(self):
        for media_type in ("text/html; charset=utf-8", "text/css", "application/javascript",
                           "application/json", "application/manifest+json", "image/svg+xml"):
            with self.subTest(media_type=media_type):
                self.assertTrue(is_compressible(media_type))
        for media_type in ("image/png", "image/jpeg", "application/zip", "application/octet-stream",
                           "application/vnd.android.package-archive", "", None):
            with self.subTest(media_type=media_type):
                self.assertFalse(is_compressible(media_type))


class MiddlewareTests(unittest.TestCase):
    def setUp(self):
        self.client = _client()

    def test_compresses_large_text(self):
        r = self.client.get("/text", headers={"Accept-Encoding": "gzip"})
        self.assertEqual(r.headers["content-encoding"], "gzip")
        self.assertIn("Accept-Encoding", r.headers["vary"])
        self.assertLess(int(r.headers["content-length"]), len(TEXT))
        self.assertEqual(r.content, TEXT)

    def test_weakens_etag_of_compressed_body(self):
        r = self.client.get("/text", headers={"Accept-Encoding": "gzip"})
        self.assertEqual(r.headers["etag"], 'W/"abc"')

    def test_plain_when_client_declines_gzip(self):
        for header in ("identity", "gzip;q=0"):
            with self.subTest(header=header):
                r = self.client.get("/text", headers={"Accept-Encoding": header})
                self.assertNotIn("content-encoding", r.headers)
                self.assertIn("Accept-Encoding", r.headers["vary"])
                self.assertEqual(r.headers["etag"], '"abc"')
                self.assertEqual(r.content, TEXT)

    def test_skips_small_bodies(self):
        r = self.client.get("/tiny", headers={"Accept-Encoding": "gzip"})
        self.assertNotIn("content-encoding", r.headers)
        self.assertEqual(r.content, b"ok")

    def test_skips_binary_downloads(self):
        r = self.client.get("/binary", headers={"Accept-Encoding": "gzip"})
        self.assertNotIn("content-encoding", r.headers)
        self.assertNotIn("vary", r.headers)
        self.assertEqual(r.headers["content-length"], str(len(BINARY)))

    def test_skips_range_requests(self):
        r = self.client.get("/text", headers={"Accept-Encoding": "gzip", "Range": "bytes=0-99"})
        self.assertNotIn("content-encoding", r.headers)

    def test_skips_head_requests(self):
        r = self.client.head("/text", headers={"Accept-Encoding": "gzip"})
        self.assertNotIn("content-encoding", r.headers)

    def test_keeps_existing_encoding(self):
        r = self.client.get("/encoded", headers={"Accept-Encoding": "gzip"})
        self.assertEqual(r.headers["content-encoding"], "br")

    def test_skips_non_200(self):
        r = self.client.get("/missing", headers={"Accept-Encoding": "gzip"})
        self.assertEqual(r.status_code, 404)
        self.assertNotIn("content-encoding", r.headers)

    def test_compresses_streamed_text(self):
        r = self.client.get("/stream", headers={"Accept-Encoding": "gzip"})
        self.assertEqual(r.headers["content-encoding"], "gzip")
        self.assertEqual(r.content, TEXT[:2048] * 3)

    def test_streams_plain_once_over_maximum(self):
        client = _client(maximum_size=4096)
        r = client.get("/stream", headers={"Accept-Encoding": "gzip"})
        self.assertNotIn("content-encoding", r.headers)
        self.assertEqual(r.content, TEXT[:2048] * 3)


class AppWiringTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)

    def test_static_text_assets_are_compressed(self):
        for path in ("/css/style.css", "/js/i18n.strings.js", "/"):
            with self.subTest(path=path):
                r = self.client.get(path, headers={"Accept-Encoding": "gzip"})
                self.assertEqual(r.status_code, 200)
                self.assertEqual(r.headers["content-encoding"], "gzip")
                self.assertTrue(r.headers["etag"].startswith("W/"))

    def test_conditional_request_still_returns_304(self):
        first = self.client.get("/css/style.css", headers={"Accept-Encoding": "gzip"})
        again = self.client.get("/css/style.css", headers={
            "Accept-Encoding": "gzip",
            "If-None-Match": first.headers["etag"],
        })
        self.assertEqual(again.status_code, 304)

    def test_images_are_untouched(self):
        r = self.client.get("/assets/site-logo.jpg", headers={"Accept-Encoding": "gzip"})
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("content-encoding", r.headers)

    def test_round_trip_matches_source(self):
        r = self.client.get("/css/style.css", headers={"Accept-Encoding": "gzip"})
        with open(main.ROOT / "css" / "style.css", "rb") as handle:
            self.assertEqual(r.content, handle.read())


if __name__ == "__main__":
    unittest.main()
