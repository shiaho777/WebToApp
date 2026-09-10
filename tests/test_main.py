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


class HistoryBulkDeleteTests(unittest.TestCase):
    """POST /api/history/delete-bulk — one request replaces the per-id DELETE
    fan-out that froze the server (issue #59), and the old /api/history/recover
    endpoint (which attached every app on the server to the caller) is gone."""

    FP = "test-device-fp"

    def setUp(self):
        self.client = TestClient(main.app)
        self._tmp = tempfile.TemporaryDirectory()
        self.apps_dir = Path(self._tmp.name)
        self.original_apps_dir = main.APPS_DIR
        self.original_store = main.history_store
        main.APPS_DIR = self.apps_dir
        main.history_store = __import__("server.history_store", fromlist=["HistoryStore"]).HistoryStore(
            self.apps_dir / "_history.json"
        )

    def tearDown(self):
        main.APPS_DIR = self.original_apps_dir
        main.history_store = self.original_store
        self._tmp.cleanup()

    def _record(self, app_id):
        (self.apps_dir / app_id).mkdir(parents=True, exist_ok=True)
        main.history_store.record_build(self.FP, {"id": app_id, "name": app_id, "url": f"https://{app_id}.test"}, f"/a/{app_id}", None)

    def _cookies(self):
        return {"webtoapp_device_fingerprint": self.FP}

    def test_bulk_delete_removes_only_requested_ids(self):
        for app_id in ("a1", "b2", "c3"):
            self._record(app_id)
        resp = self.client.post(
            "/api/history/delete-bulk",
            json={"app_ids": ["a1", "c3", "missing"]},
            cookies=self._cookies(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["removed"], ["a1", "c3"])
        remaining = [item["app_id"] for item in resp.json()["history"]["items"]]
        self.assertEqual(remaining, ["b2"])

    def test_bulk_delete_requires_device_fingerprint(self):
        resp = self.client.post("/api/history/delete-bulk", json={"app_ids": ["a1"]})
        self.assertEqual(resp.status_code, 400)

    def test_bulk_delete_rejects_oversized_payload(self):
        app_ids = [f"app{i}" for i in range(main.HISTORY_BULK_DELETE_MAX + 1)]
        resp = self.client.post(
            "/api/history/delete-bulk",
            json={"app_ids": app_ids},
            cookies=self._cookies(),
        )
        self.assertEqual(resp.status_code, 400)

    def test_bulk_delete_empty_list_is_a_noop(self):
        resp = self.client.post(
            "/api/history/delete-bulk",
            json={"app_ids": []},
            cookies=self._cookies(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["removed"], [])

    def test_recover_endpoint_is_removed(self):
        # 405 (matches the DELETE /{app_id} route as "recover") proves no POST
        # recover handler exists anymore.
        resp = self.client.post("/api/history/recover", cookies=self._cookies())
        self.assertIn(resp.status_code, (404, 405))


class MarketAndVisibilityTests(unittest.TestCase):
    """Public/private visibility + tags + market listing (issue #61)."""

    FP = "market-test-fp"

    def setUp(self):
        self.client = TestClient(main.app)
        self._tmp = tempfile.TemporaryDirectory()
        self.apps_dir = Path(self._tmp.name)
        self.original_apps_dir = main.APPS_DIR
        self.original_store = main.history_store
        main.APPS_DIR = self.apps_dir
        from server.history_store import HistoryStore
        main.history_store = HistoryStore(self.apps_dir / "_history.json")

    def tearDown(self):
        main.APPS_DIR = self.original_apps_dir
        main.history_store = self.original_store
        self._tmp.cleanup()

    def _build(self, app_id, visibility, tags):
        (self.apps_dir / app_id).mkdir(parents=True, exist_ok=True)
        recipe = {
            "id": app_id, "name": f"App {app_id}", "url": f"https://{app_id}.test",
            "visibility": visibility, "tags": tags, "edit_token": f"tok-{app_id}",
        }
        (self.apps_dir / app_id / "recipe.json").write_text(json.dumps(recipe))
        main.history_store.record_build(self.FP, recipe, f"/a/{app_id}", None)

    def _cookies(self):
        return {"webtoapp_device_fingerprint": self.FP}

    def test_market_lists_only_public_apps(self):
        self._build("pub1", "public", ["tools"])
        self._build("priv1", "private", ["tools"])
        resp = self.client.get("/api/market")
        self.assertEqual(resp.status_code, 200)
        ids = [item["app_id"] for item in resp.json()["items"]]
        self.assertEqual(ids, ["pub1"])

    def test_market_tag_filter_and_sort(self):
        self._build("toolapp", "public", ["tools"])
        self._build("gameapp", "public", ["games"])
        resp = self.client.get("/api/market", params={"tag": "games"})
        ids = [item["app_id"] for item in resp.json()["items"]]
        self.assertEqual(ids, ["gameapp"])
        resp = self.client.get("/api/market", params={"sort": "newest"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["sort"], "newest")

    def test_market_search_matches_name(self):
        self._build("findme", "public", ["tools"])
        self._build("other", "public", ["tools"])
        resp = self.client.get("/api/market", params={"search": "findme"})
        ids = [item["app_id"] for item in resp.json()["items"]]
        self.assertEqual(ids, ["findme"])

    def test_market_never_leaks_edit_token(self):
        self._build("pubtok", "public", ["tools"])
        item = self.client.get("/api/market").json()["items"][0]
        self.assertNotIn("edit_token", item.get("recipe") or {})

    def test_visibility_toggle_requires_ownership(self):
        self._build("owned", "private", ["tools"])
        # Wrong token, wrong device -> 403
        resp = self.client.post(
            "/api/history/owned/visibility",
            json={"visibility": "public", "edit_token": "wrong"},
            cookies={"webtoapp_device_fingerprint": "someone-else"},
        )
        self.assertEqual(resp.status_code, 403)
        # Owner device -> 200 and app becomes public
        resp = self.client.post(
            "/api/history/owned/visibility",
            json={"visibility": "public", "edit_token": ""},
            cookies=self._cookies(),
        )
        self.assertEqual(resp.status_code, 200)
        ids = [i["app_id"] for i in self.client.get("/api/market").json()["items"]]
        self.assertEqual(ids, ["owned"])
        # Back to private -> disappears from market
        resp = self.client.post(
            "/api/history/owned/visibility",
            json={"visibility": "private", "edit_token": "tok-owned"},
            cookies={"webtoapp_device_fingerprint": "someone-else"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.client.get("/api/market").json()["items"], [])
        # recipe.json visibility synced too
        stored = json.loads((self.apps_dir / "owned" / "recipe.json").read_text())
        self.assertEqual(stored["visibility"], "private")

    def test_public_requires_tags(self):
        self._build("notag", "private", [])
        resp = self.client.post(
            "/api/history/notag/visibility",
            json={"visibility": "public", "edit_token": "tok-notag"},
            cookies={"webtoapp_device_fingerprint": "someone-else"},
        )
        self.assertEqual(resp.status_code, 400)


class DownloadPageNoAttachTests(unittest.TestCase):
    """GET /a/<id> must count a visit but never attach the app to the
    visitor's history — market visitors were inheriting other people's
    public apps (issue #67), which also granted false ownership."""

    def setUp(self):
        self.client = TestClient(main.app)
        self._tmp = tempfile.TemporaryDirectory()
        self.apps_dir = Path(self._tmp.name)
        self.original_apps_dir = main.APPS_DIR
        self.original_store = main.history_store
        main.APPS_DIR = self.apps_dir
        from server.history_store import HistoryStore
        main.history_store = HistoryStore(self.apps_dir / "_history.json")

    def tearDown(self):
        main.APPS_DIR = self.original_apps_dir
        main.history_store = self.original_store
        self._tmp.cleanup()

    def test_visit_does_not_attach_to_history(self):
        app_id = "pubapp1"
        app_dir = self.apps_dir / app_id
        app_dir.mkdir(parents=True)
        (app_dir / "recipe.json").write_text(json.dumps({
            "id": app_id, "name": "Foreign App", "url": "https://foreign.test",
            "color": "#7c3aed", "visibility": "public", "tags": ["tools"],
        }))
        cookies = {"webtoapp_device_fingerprint": "visitor-fp"}
        for _ in range(2):
            resp = self.client.get(f"/a/{app_id}", cookies=cookies)
            self.assertEqual(resp.status_code, 200)
        items = main.history_store.list_history("visitor-fp", self.apps_dir)
        self.assertEqual(items, [])
        # Visits are still counted (market stats rely on them).
        self.assertFalse(main.history_store.device_owns_app("visitor-fp", app_id))
