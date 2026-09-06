import ipaddress
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Optional

from fastapi.testclient import TestClient

from server import main


class MainHelpersTests(unittest.TestCase):
    def make_request(self, *, client_host: str, headers: Optional[dict] = None, scheme: str = "https", netloc: str = "service.test"):
        return SimpleNamespace(
            headers=headers or {},
            client=SimpleNamespace(host=client_host),
            url=SimpleNamespace(scheme=scheme, netloc=netloc),
        )

    def test_client_ip_ignores_forwarded_headers_from_untrusted_clients(self):
        original = main.TRUSTED_PROXY_NETWORKS
        main.TRUSTED_PROXY_NETWORKS = (ipaddress.ip_network("127.0.0.1/32"),)
        try:
            request = self.make_request(
                client_host="198.51.100.9",
                headers={"x-forwarded-for": "203.0.113.5", "x-real-ip": "203.0.113.6"},
            )
            self.assertEqual(main._client_ip(request), "198.51.100.9")
        finally:
            main.TRUSTED_PROXY_NETWORKS = original

    def test_client_ip_accepts_forwarded_headers_from_trusted_proxy(self):
        original = main.TRUSTED_PROXY_NETWORKS
        main.TRUSTED_PROXY_NETWORKS = (ipaddress.ip_network("127.0.0.1/32"),)
        try:
            request = self.make_request(
                client_host="127.0.0.1",
                headers={"x-forwarded-for": "203.0.113.5", "x-real-ip": "203.0.113.6"},
            )
            self.assertEqual(main._client_ip(request), "203.0.113.5")
        finally:
            main.TRUSTED_PROXY_NETWORKS = original

    def test_resolve_base_url_ignores_forwarded_host_without_trusted_proxy(self):
        original = main.TRUSTED_PROXY_NETWORKS
        main.TRUSTED_PROXY_NETWORKS = (ipaddress.ip_network("127.0.0.1/32"),)
        try:
            request = self.make_request(
                client_host="198.51.100.9",
                headers={"x-forwarded-proto": "http", "x-forwarded-host": "evil.test", "host": "service.test"},
                scheme="https",
                netloc="service.test",
            )
            self.assertEqual(main._resolve_base_url(request), "https://service.test")
        finally:
            main.TRUSTED_PROXY_NETWORKS = original

    def test_load_recipe_evicts_least_recently_used_entries(self):
        original_apps_dir = main.APPS_DIR
        original_cache_size = main.RECIPE_CACHE_SIZE
        with tempfile.TemporaryDirectory() as tmpdir:
            apps_dir = Path(tmpdir)
            for app_id in ("a1", "b2", "c3"):
                path = apps_dir / app_id
                path.mkdir(parents=True)
                (path / "recipe.json").write_text(json.dumps({"id": app_id}))
            main.APPS_DIR = apps_dir
            main.RECIPE_CACHE_SIZE = 2
            with main._recipe_cache_lock:
                main._recipe_cache.clear()
            try:
                main._load_recipe("a1")
                main._load_recipe("b2")
                main._load_recipe("a1")
                main._load_recipe("c3")
                with main._recipe_cache_lock:
                    self.assertEqual(list(main._recipe_cache.keys()), ["a1", "c3"])
            finally:
                main.APPS_DIR = original_apps_dir
                main.RECIPE_CACHE_SIZE = original_cache_size
                with main._recipe_cache_lock:
                    main._recipe_cache.clear()


class EntryCacheHeaderTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)

    def test_root_html_must_revalidate(self):
        # Stale entry HTML + fresh ?v= assets inside it = users stranded on
        # old UI talking to a new API (all-zero stats). no-cache forces a
        # cheap 304 revalidation instead of heuristic caching.
        for path in ("/", "/index.html"):
            resp = self.client.get(path)
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.headers.get("cache-control"), "no-cache")

    def test_versioned_assets_stay_long_cached(self):
        resp = self.client.get("/css/style.css")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("max-age=86400", resp.headers.get("cache-control", ""))
