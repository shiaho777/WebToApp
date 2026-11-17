"""Resource-exhaustion defenses (#242): identity-independent throughput
budgets, zero-signal fast reclaim, disk watermark, HTML content dedup.
"""

import io
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from server import config, html_site, main
from server.community_store import CommunityStore
from server.history_store import HistoryStore


def _zip_bytes(entries):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in entries.items():
            z.writestr(name, data)
    return buf.getvalue()


class BuildBudgetTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)
        self._tmp = tempfile.TemporaryDirectory()
        self.apps_dir = Path(self._tmp.name)
        self._orig = (main.APPS_DIR, main.history_store)
        main.APPS_DIR = self.apps_dir
        main.history_store = HistoryStore(self.apps_dir / "_history.sqlite3")
        main.distill_rate_limiter._buckets.clear()
        main.global_build_budget._buckets.clear()
        main.ip_daily_build_limiter._buckets.clear()
        main.url_daily_build_limiter._buckets.clear()
        # Unique fingerprint per test so the real-data daily quota (counted
        # against the shared production history store) can't leak across tests.
        self._fp = f"budget-test-{os.urandom(6).hex()}"

    def tearDown(self):
        main.APPS_DIR, main.history_store = self._orig
        self._tmp.cleanup()

    def _post(self, url="https://example.com", name="App"):
        return self.client.post(
            "/api/distill", json={"url": url, "name": name},
            cookies={"webtoapp_device_fingerprint": self._fp},
        )

    def test_global_hourly_budget_rejects_with_retry_after(self):
        with mock.patch.object(main.global_build_budget, "max_requests", 2):
            self.assertEqual(self._post(name="A").status_code, 202)
            self.assertEqual(self._post(url="https://other.test", name="B").status_code, 202)
            resp = self._post(url="https://third.test", name="C")
        self.assertEqual(resp.status_code, 429)
        self.assertEqual(resp.headers.get("retry-after"), "300")

    def test_per_ip_daily_cap(self):
        with mock.patch.object(main.ip_daily_build_limiter, "max_requests", 1):
            self.assertEqual(self._post(name="A").status_code, 202)
            resp = self._post(url="https://other.test", name="B")
        self.assertEqual(resp.status_code, 429)
        self.assertEqual(resp.headers.get("retry-after"), "3600")

    def test_per_target_daily_cap_blocks_name_variations(self):
        with mock.patch.object(main.url_daily_build_limiter, "max_requests", 1):
            self.assertEqual(self._post(name="A").status_code, 202)
            # Same target, different name (the副本-farming pattern) -> blocked.
            resp = self._post(name="B")
        self.assertEqual(resp.status_code, 429)

    def test_target_key_normalization(self):
        a = main._normalize_target_key("https://WWW.Example.com/path/?utm=1")
        b = main._normalize_target_key("https://example.com/path")
        self.assertEqual(a, b)


class ZeroSignalReclaimTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.apps = Path(self._tmp.name)
        self.store = HistoryStore(self.apps / "_history.sqlite3")

    def tearDown(self):
        self._tmp.cleanup()

    def _app(self, app_id, visibility="private", created="2026-11-01T00:00:00Z"):
        recipe = {"id": app_id, "name": app_id, "url": f"https://{app_id}.test",
                  "visibility": visibility, "tags": ["tools"]}
        self.store.record_build("fp", recipe, f"/a/{app_id}", None)
        with self.store._lock:
            self.store._conn.execute(
                "UPDATE apps SET created_at = ? WHERE app_id = ?", (created, app_id))

    def test_zero_signal_private_app_is_listed(self):
        self._app("junk0001")
        items = self.store.list_zero_signal_apps("2026-11-10T00:00:00Z")
        self.assertEqual([i["app_id"] for i in items], ["junk0001"])

    def test_visited_app_is_not_zero_signal(self):
        self._app("real0001")
        self.store.record_visit("real0001", "landing")
        self.assertEqual(self.store.list_zero_signal_apps("2026-11-10T00:00:00Z"), [])

    def test_downloaded_app_is_not_zero_signal(self):
        self._app("dl000001")
        self.store.record_visit("dl000001", "download:android")
        self.assertEqual(self.store.list_zero_signal_apps("2026-11-10T00:00:00Z"), [])

    def test_public_app_is_never_fast_reclaimed(self):
        self._app("pub00001", visibility="public")
        self.assertEqual(self.store.list_zero_signal_apps("2026-11-10T00:00:00Z"), [])

    def test_recent_app_is_not_reclaimed(self):
        self._app("new00001", created="2026-11-16T00:00:00Z")
        self.assertEqual(self.store.list_zero_signal_apps("2026-11-10T00:00:00Z"), [])


class DiskWatermarkTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)
        self._tmp = tempfile.TemporaryDirectory()
        self.apps_dir = Path(self._tmp.name)
        self._orig = main.APPS_DIR
        main.APPS_DIR = self.apps_dir
        main._invalidate_disk_usage_cache()

    def tearDown(self):
        main.APPS_DIR = self._orig
        main._invalidate_disk_usage_cache()
        self._tmp.cleanup()

    def test_html_upload_paused_over_budget(self):
        (self.apps_dir / "big.bin").write_bytes(b"x" * (2 * 1024 * 1024))
        with mock.patch.object(config, "generated_disk_budget_mb", return_value=1):
            resp = self.client.post(
                "/api/distill/html",
                files={"file": ("app.html", b"<html><title>t</title></html>", "text/html")},
                data={},
            )
        self.assertEqual(resp.status_code, 503)
        self.assertEqual(resp.headers.get("retry-after"), "600")

    def test_url_builds_unaffected_by_disk_budget(self):
        (self.apps_dir / "big.bin").write_bytes(b"x" * (2 * 1024 * 1024))
        main.distill_rate_limiter._buckets.clear()
        main.global_build_budget._buckets.clear()
        main.ip_daily_build_limiter._buckets.clear()
        main.url_daily_build_limiter._buckets.clear()
        fp = f"disk-test-{os.urandom(6).hex()}"
        with mock.patch.object(config, "generated_disk_budget_mb", return_value=1):
            resp = self.client.post(
                "/api/distill", json={"url": "https://example.com"},
                cookies={"webtoapp_device_fingerprint": fp},
            )
        self.assertEqual(resp.status_code, 202)


class ContentDedupTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.apps = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_same_content_different_name_shares_inodes(self):
        bundle = _zip_bytes({"index.html": b"<html><title>same</title></html>",
                             "app.js": b"console.log(1);"})
        first = html_site.stage_html_app(bundle, "site.zip", "Name One", self.apps)
        second = html_site.stage_html_app(bundle, "site.zip", "Name Two", self.apps)
        self.assertNotEqual(first["app_id"], second["app_id"])
        f1 = first["site_dir"] / "index.html"
        f2 = second["site_dir"] / "index.html"
        self.assertEqual(f1.read_bytes(), f2.read_bytes())
        self.assertEqual(f1.stat().st_ino, f2.stat().st_ino)  # one inode, two apps

    def test_different_content_stays_separate(self):
        a = html_site.stage_html_app(
            _zip_bytes({"index.html": b"<html>a</html>"}), "s.zip", "A", self.apps)
        b = html_site.stage_html_app(
            _zip_bytes({"index.html": b"<html>b</html>"}), "s.zip", "B", self.apps)
        self.assertNotEqual(
            (a["site_dir"] / "index.html").stat().st_ino,
            (b["site_dir"] / "index.html").stat().st_ino)

    def test_same_content_same_name_reuses_app_id(self):
        # HTML app_id = hash(content:name): identical re-upload is the same
        # app (rebuild), while changed content mints a new id by design.
        bundle = _zip_bytes({"index.html": b"<html>v1</html>"})
        first = html_site.stage_html_app(bundle, "s.zip", "App", self.apps)
        again = html_site.stage_html_app(bundle, "s.zip", "App", self.apps)
        self.assertEqual(first["app_id"], again["app_id"])
        changed = html_site.stage_html_app(
            _zip_bytes({"index.html": b"<html>v2</html>"}), "s.zip", "App", self.apps)
        self.assertNotEqual(first["app_id"], changed["app_id"])
        self.assertEqual((changed["site_dir"] / "index.html").read_bytes(), b"<html>v2</html>")


if __name__ == "__main__":
    unittest.main()