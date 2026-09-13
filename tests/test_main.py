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

    def _build(self, app_id, visibility, tags, extra=None):
        (self.apps_dir / app_id).mkdir(parents=True, exist_ok=True)
        recipe = {
            "id": app_id, "name": f"App {app_id}", "url": f"https://{app_id}.test",
            "visibility": visibility, "tags": tags, "edit_token": f"tok-{app_id}",
        }
        recipe.update(extra or {})
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

    def test_market_includes_icon_url_when_icon_exists(self):
        self._build("iconapp", "public", ["tools"])
        self._build("noicon", "public", ["tools"])
        (self.apps_dir / "iconapp" / "icon.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        items = {i["app_id"]: i for i in self.client.get("/api/market").json()["items"]}
        self.assertEqual(items["iconapp"]["icon_url"], "/a/iconapp/icon.png")
        self.assertIsNone(items["noicon"]["icon_url"])

    def test_market_exposes_description_when_set(self):
        self._build("descapp", "public", ["tools"],
                    extra={"description": "A tiny RSS reader"})
        self._build("nodesc", "public", ["tools"])
        items = {i["app_id"]: i for i in self.client.get("/api/market").json()["items"]}
        self.assertEqual(items["descapp"]["description"], "A tiny RSS reader")
        self.assertEqual(items["nodesc"]["description"], "")

    def test_history_delete_purges_orphaned_public_app(self):
        self._build("goneapp", "public", ["tools"])
        ids = [i["app_id"] for i in self.client.get("/api/market").json()["items"]]
        self.assertIn("goneapp", ids)
        resp = self.client.delete("/api/history/goneapp", cookies=self._cookies())
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["purged"])
        self.assertFalse((self.apps_dir / "goneapp").exists())
        ids = [i["app_id"] for i in self.client.get("/api/market").json()["items"]]
        self.assertNotIn("goneapp", ids)

    def test_history_delete_keeps_app_owned_by_another_device(self):
        self._build("shared", "public", ["tools"])
        main.history_store.attach_app("other-device-fp", "shared")
        resp = self.client.delete("/api/history/shared", cookies=self._cookies())
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["purged"])
        self.assertTrue((self.apps_dir / "shared").exists())
        ids = [i["app_id"] for i in self.client.get("/api/market").json()["items"]]
        self.assertIn("shared", ids)

    def test_history_bulk_delete_purges_and_reports(self):
        self._build("bulkapp1", "public", ["tools"])
        self._build("bulkapp2", "public", ["tools"])
        resp = self.client.post("/api/history/delete-bulk",
                                json={"app_ids": ["bulkapp1", "bulkapp2", "notmine"]},
                                cookies=self._cookies())
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(sorted(body["removed"]), ["bulkapp1", "bulkapp2"])
        self.assertEqual(sorted(body["purged"]), ["bulkapp1", "bulkapp2"])
        self.assertFalse((self.apps_dir / "bulkapp1").exists())
        self.assertEqual(self.client.get("/api/market").json()["items"], [])

    def test_visibility_toggle_requires_edit_token(self):
        self._build("owned", "private", ["tools"])
        # Wrong token, wrong device -> 403
        resp = self.client.post(
            "/api/history/owned/visibility",
            json={"visibility": "public", "edit_token": "wrong"},
            cookies={"webtoapp_device_fingerprint": "someone-else"},
        )
        self.assertEqual(resp.status_code, 403)
        # Owning device WITHOUT the token -> 403 too: device attachment is
        # self-grantable via /api/history/attach, so it proves nothing.
        resp = self.client.post(
            "/api/history/owned/visibility",
            json={"visibility": "public", "edit_token": ""},
            cookies=self._cookies(),
        )
        self.assertEqual(resp.status_code, 403)
        # Correct token from any device -> 200 and app becomes public
        resp = self.client.post(
            "/api/history/owned/visibility",
            json={"visibility": "public", "edit_token": "tok-owned"},
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

    def test_attach_alone_does_not_grant_visibility(self):
        # The attach endpoint is intentionally open (it only re-links an app
        # into the caller's own history). It must NOT suffice to flip a
        # victim app's public/private state (issue #73).
        self._build("victimapp", "private", ["tools"])
        attacker = {"webtoapp_device_fingerprint": "attacker-fp"}
        resp = self.client.post("/api/history/attach/victimapp", cookies=attacker)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(main.history_store.device_owns_app("attacker-fp", "victimapp"))
        resp = self.client.post(
            "/api/history/victimapp/visibility",
            json={"visibility": "public", "edit_token": ""},
            cookies=attacker,
        )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(self.client.get("/api/market").json()["items"], [])


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


class HistoryImportHardeningTests(unittest.TestCase):
    """POST /api/history/import — rate limit, item cap, app_id allowlist and
    path containment (issue #73)."""

    FP = "import-test-fp"

    def setUp(self):
        self.client = TestClient(main.app)
        self._tmp = tempfile.TemporaryDirectory()
        self.apps_dir = Path(self._tmp.name)
        self.original_apps_dir = main.APPS_DIR
        self.original_store = main.history_store
        main.APPS_DIR = self.apps_dir
        from server.history_store import HistoryStore
        main.history_store = HistoryStore(self.apps_dir / "_history.json")
        main.import_rate_limiter._buckets.clear()

    def tearDown(self):
        main.APPS_DIR = self.original_apps_dir
        main.history_store = self.original_store
        main.import_rate_limiter._buckets.clear()
        self._tmp.cleanup()

    def _cookies(self):
        return {"webtoapp_device_fingerprint": self.FP}

    def test_rejects_traversal_app_id(self):
        resp = self.client.post(
            "/api/history/import",
            json={"items": [{"app_id": "../escape", "recipe": {"url": "https://x.test"}}]},
            cookies=self._cookies(),
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["imported"], 0)
        self.assertEqual(body["skipped"], 1)
        self.assertFalse((self.apps_dir.parent / "escape").exists())

    def test_rejects_non_http_target_url(self):
        resp = self.client.post(
            "/api/history/import",
            json={"items": [{"app_id": "jsurl123", "recipe": {"url": "javascript:alert(1)"}}]},
            cookies=self._cookies(),
        )
        self.assertEqual(resp.json()["skipped"], 1)

    def test_caps_items_per_request(self):
        items = [{"app_id": f"app{i:04d}"} for i in range(main.HISTORY_IMPORT_MAX_ITEMS + 1)]
        resp = self.client.post(
            "/api/history/import", json={"items": items}, cookies=self._cookies()
        )
        self.assertEqual(resp.status_code, 400)

    def test_rate_limits_import_requests(self):
        for _ in range(main.import_rate_limiter.max_requests):
            resp = self.client.post(
                "/api/history/import", json={"items": []}, cookies=self._cookies()
            )
            self.assertEqual(resp.status_code, 200)
        resp = self.client.post(
            "/api/history/import", json={"items": []}, cookies=self._cookies()
        )
        self.assertEqual(resp.status_code, 429)

    def test_valid_import_relinks_without_overwriting_recipe(self):
        app_id = "app12345"
        (self.apps_dir / app_id).mkdir(parents=True)
        (self.apps_dir / app_id / "recipe.json").write_text(json.dumps({
            "id": app_id, "name": "A", "url": "https://a.test", "edit_token": "sekrit",
        }))
        resp = self.client.post(
            "/api/history/import",
            json={"items": [{"app_id": app_id, "recipe": {"url": "https://a.test", "name": "A"}}]},
            cookies=self._cookies(),
        )
        self.assertEqual(resp.json()["imported"], 1)
        stored = json.loads((self.apps_dir / app_id / "recipe.json").read_text())
        self.assertEqual(stored["edit_token"], "sekrit")


class AppIdPathGuardTests(unittest.TestCase):
    """Every route mapping an app_id onto the apps dir rejects malformed ids
    in middleware — traversal and markup characters can never reach the
    filesystem layer (issue #73)."""

    def setUp(self):
        self.client = TestClient(main.app)

    def test_malformed_app_ids_404(self):
        # Avoid literal ".." segments — the HTTP client normalizes them away
        # before the request reaches the app. Encoded/in-band bad ids survive
        # transport and must die in the middleware guard.
        for path in (
            "/a/%2e%2e%2f%2e%2e%2fetc",  # encoded traversal
            "/a/x",                      # below min length
            "/a/abcd1234%22",            # quote char
            "/a/%3Csvg%3E1234",
            "/api/history/attach/%2e%2e",
            "/api/app/%2e%2e/url",
        ):
            resp = self.client.get(path)
            self.assertEqual(resp.status_code, 404, path)

    def test_wellformed_app_id_reaches_route(self):
        # A syntactically valid but nonexistent app id must pass the guard and
        # 404 in the route itself (same status, proves the guard let it through
        # only indirectly — mainly we assert no 5xx).
        resp = self.client.get("/a/abcd1234")
        self.assertIn(resp.status_code, (200, 404))


class QuotaAndAnalyzeLimitTests(unittest.TestCase):
    """Cookie-less builds charge a quota bucket keyed on client IP, and
    /api/analyze is rate-limited (issue #73 follow-ups)."""

    def setUp(self):
        self.client = TestClient(main.app)
        self._tmp = tempfile.TemporaryDirectory()
        self.apps_dir = Path(self._tmp.name)
        self.original_apps_dir = main.APPS_DIR
        self.original_store = main.history_store
        main.APPS_DIR = self.apps_dir
        from server.history_store import HistoryStore
        main.history_store = HistoryStore(self.apps_dir / "_history.json")
        main.analyze_rate_limiter._buckets.clear()
        main.distill_rate_limiter._buckets.clear()

    def tearDown(self):
        main.APPS_DIR = self.original_apps_dir
        main.history_store = self.original_store
        self._tmp.cleanup()

    def test_quota_identity_falls_back_to_ip(self):
        req = SimpleNamespace(
            headers={}, client=SimpleNamespace(host="203.0.113.9"),
            url=SimpleNamespace(scheme="https", netloc="service.test"),
        )
        self.assertEqual(main._quota_identity(req, None), "ip:203.0.113.9")
        self.assertEqual(main._quota_identity(req, "fp1"), "fp1")

    def test_cookieless_build_counts_against_ip_bucket(self):
        # TestClient's peer ("testclient") normalizes to "unknown" — the IP
        # bucket for cookie-less requests is therefore "ip:unknown".
        original_quota = main.config.daily_build_quota_per_device
        main.config.daily_build_quota_per_device = lambda: 1
        try:
            (self.apps_dir / "app00001").mkdir(parents=True)
            main.history_store.record_build(
                "ip:unknown",
                {"id": "app00001", "name": "a", "url": "https://a.test"},
                "/a/app00001", None,
            )
            resp = self.client.post("/api/distill", json={"url": "https://example.com"})
            self.assertEqual(resp.status_code, 429)
        finally:
            main.config.daily_build_quota_per_device = original_quota

    def test_analyze_is_rate_limited(self):
        from unittest.mock import AsyncMock, patch
        with patch.object(main.analyzer, "analyze", new=AsyncMock(return_value={"ok": True})):
            codes = [
                self.client.post("/api/analyze", json={"url": "https://example.com"}).status_code
                for _ in range(main.analyze_rate_limiter.max_requests + 1)
            ]
        self.assertEqual(codes[-1], 429)
        self.assertTrue(all(c == 200 for c in codes[:-1]))


class CommunityEndpointTests(unittest.TestCase):
    """Profiles, creator attribution, comments + ratings endpoints (issue #81)."""

    FP_A = "comm-fp-a"
    FP_B = "comm-fp-b"

    def setUp(self):
        self.client = TestClient(main.app)
        self._tmp = tempfile.TemporaryDirectory()
        self.apps_dir = Path(self._tmp.name)
        self.original_apps_dir = main.APPS_DIR
        self.original_store = main.history_store
        self.original_community = main.community_store
        self.original_avatars = main.AVATARS_DIR
        main.APPS_DIR = self.apps_dir
        from server.history_store import HistoryStore
        from server.community_store import CommunityStore
        main.history_store = HistoryStore(self.apps_dir / "_history.sqlite3")
        main.community_store = CommunityStore(self.apps_dir / "_community.sqlite3")
        main.AVATARS_DIR = self.apps_dir / "_avatars"
        main.AVATARS_DIR.mkdir(exist_ok=True)

    def tearDown(self):
        main.APPS_DIR = self.original_apps_dir
        main.history_store = self.original_store
        main.community_store = self.original_community
        main.AVATARS_DIR = self.original_avatars
        self._tmp.cleanup()

    def _cookies(self, fp):
        return {"webtoapp_device_fingerprint": fp}

    def _make_app(self, app_id, fp, visibility="public", name=None):
        (self.apps_dir / app_id).mkdir(parents=True, exist_ok=True)
        recipe = {
            "id": app_id, "name": name or f"App {app_id}",
            "url": f"https://{app_id}.test",
            "visibility": visibility, "tags": ["tools"],
            "edit_token": f"tok-{app_id}",
        }
        (self.apps_dir / app_id / "recipe.json").write_text(json.dumps(recipe))
        main.history_store.record_build(fp, recipe, f"/a/{app_id}", None)
        # Mirrors the record_build caller in /api/distill: every build
        # attributes a creator, regardless of visibility.
        main.community_store.ensure_user(fp)
        main.community_store.set_creator(app_id, fp)

    # ---------- profiles ----------

    def test_me_requires_fingerprint_and_assigns_sequential_nums(self):
        self.assertEqual(self.client.get("/api/me").status_code, 400)
        a = self.client.get("/api/me", cookies=self._cookies(self.FP_A)).json()
        b = self.client.get("/api/me", cookies=self._cookies(self.FP_B)).json()
        self.assertEqual(a["profile"]["user_num"], 1)
        self.assertEqual(b["profile"]["user_num"], 2)
        # Second visit keeps the number.
        again = self.client.get("/api/me", cookies=self._cookies(self.FP_A)).json()
        self.assertEqual(again["profile"]["user_num"], 1)

    def test_profile_update_validation_and_uniqueness(self):
        resp = self.client.post(
            "/api/me/profile",
            json={"name": "bad name!", "bio_md": ""},
            cookies=self._cookies(self.FP_A),
        )
        self.assertEqual(resp.status_code, 422)
        resp = self.client.post(
            "/api/me/profile",
            json={"name": "Alice", "bio_md": "**hi**"},
            cookies=self._cookies(self.FP_A),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["profile"]["name"], "Alice")
        resp = self.client.post(
            "/api/me/profile",
            json={"name": "ALICE", "bio_md": ""},
            cookies=self._cookies(self.FP_B),
        )
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json()["detail"], "name_taken")

    def test_public_user_profile_and_apps(self):
        self._make_app("pub1aaaa", self.FP_A, "public")
        self._make_app("priv1aaa", self.FP_A, "private")
        self.client.get("/api/me", cookies=self._cookies(self.FP_A))
        resp = self.client.get("/api/users/1")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["profile"]["user_num"], 1)
        ids = [a["app_id"] for a in data["apps"]]
        self.assertEqual(ids, ["pub1aaaa"])  # private app hidden publicly
        self.assertEqual(self.client.get("/api/users/999").status_code, 404)
        self.assertEqual(self.client.get("/api/users/abc").status_code, 404)
        # Own /api/me lists both apps including private.
        mine = self.client.get("/api/me", cookies=self._cookies(self.FP_A)).json()
        self.assertEqual(sorted(a["app_id"] for a in mine["apps"]),
                         ["priv1aaa", "pub1aaaa"])

    def test_avatar_upload_and_serve(self):
        import io
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow not installed")
        buf = io.BytesIO()
        Image.new("RGB", (64, 64), (200, 80, 60)).save(buf, format="PNG")
        resp = self.client.post(
            "/api/me/avatar",
            files={"file": ("a.png", buf.getvalue(), "image/png")},
            cookies=self._cookies(self.FP_A),
        )
        self.assertEqual(resp.status_code, 200)
        url = resp.json()["avatar_url"]
        self.assertTrue(url.startswith("/u/1/avatar.png"))
        served = self.client.get(url.split("?")[0])
        self.assertEqual(served.status_code, 200)
        self.assertEqual(served.headers["content-type"], "image/png")
        # Garbage is rejected.
        bad = self.client.post(
            "/api/me/avatar",
            files={"file": ("a.png", b"not an image", "image/png")},
            cookies=self._cookies(self.FP_A),
        )
        self.assertEqual(bad.status_code, 422)

    # ---------- comments & ratings ----------

    def test_comment_post_get_delete(self):
        self._make_app("capp1", self.FP_A)
        resp = self.client.post(
            "/api/apps/capp1/comments",
            json={"body": "nice <b>app</b>", "rating": 4},
            cookies=self._cookies(self.FP_B),
        )
        self.assertEqual(resp.status_code, 200)
        comment = resp.json()["comment"]
        self.assertEqual(comment["rating"], 4)
        self.assertTrue(comment["mine"])
        community = self.client.get("/api/apps/capp1/community").json()
        self.assertEqual(len(community["comments"]), 1)
        self.assertEqual(community["rating_avg"], 4.0)
        self.assertEqual(community["rating_count"], 1)
        # Wrong fp cannot delete; author can.
        denied = self.client.delete(
            f"/api/comments/{comment['id']}", cookies=self._cookies(self.FP_A))
        self.assertEqual(denied.status_code, 403)
        ok = self.client.delete(
            f"/api/comments/{comment['id']}", cookies=self._cookies(self.FP_B))
        self.assertEqual(ok.status_code, 200)

    def test_comment_admin_delete(self):
        self._make_app("capp2", self.FP_A)
        comment = self.client.post(
            "/api/apps/capp2/comments",
            json={"body": "spam", "rating": None},
            cookies=self._cookies(self.FP_B),
        ).json()["comment"]
        import os
        os.environ["ADMIN_TOKEN"] = "secret-tok"
        try:
            resp = self.client.delete(
                f"/api/comments/{comment['id']}",
                headers={"Authorization": "Bearer secret-tok"},
            )
            self.assertEqual(resp.status_code, 200)
        finally:
            del os.environ["ADMIN_TOKEN"]


    def test_market_sort_rating_avg_then_count(self):
        self._make_app("rlow", self.FP_A)
        self._make_app("rhigh", self.FP_A)
        self._make_app("rtie", self.FP_A)
        self._make_app("rnone", self.FP_A)
        # rhigh: 5.0 avg, 2 votes; rtie: 5.0 avg, 1 vote; rlow: 3.0; rnone: unrated
        # Seed via the store directly — the HTTP path is IP-rate-limited and
        # earlier tests in this class already drained the bucket.
        cs = main.community_store
        cs.add_comment("rhigh", "fp-x", "g", 5)
        cs.add_comment("rhigh", "fp-y", "g", 5)
        cs.add_comment("rtie", "fp-z", "g", 5)
        cs.add_comment("rlow", "fp-w", "ok", 3)
        items = self.client.get("/api/market", params={"sort": "rating"}).json()["items"]
        ids = [i["app_id"] for i in items]
        self.assertLess(ids.index("rhigh"), ids.index("rtie"))
        self.assertLess(ids.index("rtie"), ids.index("rlow"))
        self.assertLess(ids.index("rlow"), ids.index("rnone"))
        # default sort is newest
        default = self.client.get("/api/market").json()
        self.assertEqual(default["sort"], "newest")

    def test_comment_validation_and_missing_fp(self):
        self._make_app("capp3", self.FP_A)
        self.assertEqual(
            self.client.post("/api/apps/capp3/comments", json={"body": "hi"}).status_code, 400)
        for payload, want in [
            ({"body": ""}, 422),
            ({"body": "ok", "rating": 0}, 422),
            ({"body": "ok", "rating": 6}, 422),
        ]:
            resp = self.client.post(
                "/api/apps/capp3/comments", json=payload,
                cookies=self._cookies(self.FP_B))
            self.assertEqual(resp.status_code, want, payload)
        self.assertEqual(
            self.client.get("/api/apps/nonexistent/community").status_code, 404)

    # ---------- market decoration ----------

    def test_market_items_carry_creator_and_rating(self):
        self._make_app("mkt1", self.FP_A)
        self.client.post(
            "/api/me/profile", json={"name": "Maker", "bio_md": ""},
            cookies=self._cookies(self.FP_A))
        self.client.post(
            "/api/apps/mkt1/comments", json={"body": "good", "rating": 5},
            cookies=self._cookies(self.FP_B))
        item = self.client.get("/api/market").json()["items"][0]
        self.assertEqual(item["creator_num"], 1)
        self.assertEqual(item["creator_name"], "Maker")
        self.assertEqual(item["rating_avg"], 5.0)
        self.assertEqual(item["rating_count"], 1)
        # Search by #num and by creator name.
        by_num = self.client.get("/api/market", params={"search": "#1"}).json()["items"]
        self.assertEqual([i["app_id"] for i in by_num], ["mkt1"])
        by_name = self.client.get("/api/market", params={"search": "maker"}).json()["items"]
        self.assertEqual([i["app_id"] for i in by_name], ["mkt1"])

    def test_community_endpoint_reports_creator_and_other_apps(self):
        self._make_app("mine1", self.FP_A)
        self._make_app("mine2", self.FP_A, "public", name="Second App")
        data = self.client.get("/api/apps/mine2/community").json()
        self.assertEqual(data["creator"]["user_num"], 1)
        self.assertEqual([a["app_id"] for a in data["other_apps"]], ["mine1"])


class AboutImageRouteTests(unittest.TestCase):
    """GET /a/{app_id}/about/{name} — serves only server-generated about-N.webp
    files from inside the app's own directory."""

    def setUp(self):
        self.client = TestClient(main.app)
        self._tmp = tempfile.TemporaryDirectory()
        self.apps_dir = Path(self._tmp.name)
        self.original_apps_dir = main.APPS_DIR
        main.APPS_DIR = self.apps_dir
        app_dir = self.apps_dir / "aboutapp"
        app_dir.mkdir(parents=True)
        (app_dir / "recipe.json").write_text(json.dumps({"id": "aboutapp"}))
        (app_dir / "about-1.webp").write_bytes(b"RIFFfake-webp")
        (app_dir / "secret.txt").write_bytes(b"nope")

    def tearDown(self):
        main.APPS_DIR = self.original_apps_dir
        self._tmp.cleanup()

    def test_serves_about_image_with_cache_headers(self):
        resp = self.client.get("/a/aboutapp/about/about-1.webp")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content, b"RIFFfake-webp")
        self.assertEqual(resp.headers["content-type"], "image/webp")
        self.assertIn("max-age=86400", resp.headers.get("cache-control", ""))

    def test_rejects_non_generated_names_and_missing_app(self):
        self.assertEqual(self.client.get("/a/aboutapp/about/evil.png").status_code, 404)
        self.assertEqual(self.client.get("/a/aboutapp/about/secret.txt").status_code, 404)
        self.assertEqual(self.client.get("/a/nosuchid/about/about-1.webp").status_code, 404)
        self.assertEqual(self.client.get("/a/aboutapp/about/about-9.webp").status_code, 404)


class PublicRecipeScrubTests(unittest.TestCase):
    def test_transient_about_keys_never_leak(self):
        safe = main._public_recipe({
            "id": "x", "name": "X",
            "_about_text": "hi", "_about_images": ["data:image/png;base64,AA=="],
            "_custom_icon_data_url": "data:image/png;base64,BB==",
            "edit_token": "secret",
            "about": {"text": "hi", "images": ["about-1.webp"]},
        })
        for k in ("_about_text", "_about_images", "_custom_icon_data_url", "edit_token"):
            self.assertNotIn(k, safe)
        self.assertEqual(safe["about"]["images"], ["about-1.webp"])
