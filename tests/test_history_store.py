import json
import tempfile
import unittest
from pathlib import Path

from server.history_store import HistoryStore


class HistoryStoreSqliteTests(unittest.TestCase):
    def test_record_list_and_migrate_from_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            json_path = root / "_history.json"
            json_path.write_text(
                json.dumps(
                    {
                        "devices": {
                            "dev1": {
                                "app_ids": ["app1"],
                                "created_at": "2026-01-01T00:00:00Z",
                                "updated_at": "2026-01-01T00:00:00Z",
                            }
                        },
                        "apps": {
                            "app1": {
                                "app_id": "app1",
                                "name": "Demo",
                                "target_url": "https://example.com",
                                "public_path": "/a/app1",
                                "runtime_url": "https://example.com",
                                "color": "#111111",
                                "recipe": {"id": "app1", "url": "https://example.com", "name": "Demo"},
                                "created_at": "2026-01-01T00:00:00Z",
                                "updated_at": "2026-01-01T00:00:00Z",
                            }
                        },
                        "visits": {
                            "app1": {
                                "total": 3,
                                "landing": 2,
                                "install": 1,
                                "pwa": 0,
                                "launch": 0,
                                "downloads": {"android": 1},
                                "last_visited_at": "2026-01-02T00:00:00Z",
                            }
                        },
                    }
                )
            )
            store = HistoryStore(json_path)
            items = store.list_history("dev1", root)
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]["name"], "Demo")
            self.assertEqual(items[0]["visit_count"], 3)
            self.assertTrue(store.db_path.exists())
            store.record_build(
                "dev1",
                {"id": "app2", "url": "https://example.org", "name": "Two", "color": "#222222"},
                "/a/app2",
                "https://example.org",
            )
            items = store.list_history("dev1", root)
            self.assertEqual([i["app_id"] for i in items][:2], ["app2", "app1"])
            self.assertEqual(store.stats()["apps"], 2)

    def test_traffic_totals_splits_views_and_downloads(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = HistoryStore(Path(tmp) / "_history.json")
            store.record_visit("app1", "landing")
            store.record_visit("app1", "landing")
            store.record_visit("app1", "download:android")
            store.record_visit("app2", "install")
            store.record_visit("app2", "download:ios")
            store.record_visit("app2", "download:ios")
            totals = store.traffic_totals()
            # Pure page views only; download events counted separately.
            self.assertEqual(totals["views"], 3)
            self.assertEqual(totals["downloads"], 3)


class PublicListingQueryTests(unittest.TestCase):
    """issue #224: one JOIN instead of per-row visits SELECTs, json_each
    download totals, and limit=None for full-set search/sort correctness."""

    def _store_with_apps(self, tmp, count):
        store = HistoryStore(Path(tmp) / "_history.json")
        for index in range(count):
            app_id = f"app{index:04d}"
            store.record_build(
                "dev",
                {"id": app_id, "name": f"App {index}", "url": f"https://{app_id}.test",
                 "visibility": "public", "tags": ["tools"]},
                f"/a/{app_id}",
                None,
            )
        return store

    def test_limit_none_returns_full_public_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store_with_apps(tmp, 65)
            items = store.list_public_apps(sort="newest", limit=None)
            self.assertEqual(len(items), 65)
            # Default limit still pages.
            self.assertEqual(len(store.list_public_apps(sort="newest")), 60)

    def test_offset_pages_without_overlap(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store_with_apps(tmp, 10)
            first = store.list_public_apps(sort="newest", limit=4, offset=0)
            second = store.list_public_apps(sort="newest", limit=4, offset=4)
            self.assertEqual(len(first), 4)
            self.assertEqual(len(second), 4)
            self.assertFalse({i["app_id"] for i in first} & {i["app_id"] for i in second})

    def test_download_totals_summed_in_sql(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store_with_apps(tmp, 2)
            store.record_visit("app0000", "download:android")
            store.record_visit("app0000", "download:ios")
            store.record_visit("app0000", "landing")
            store.record_visit("app0001", "download:android")
            items = {i["app_id"]: i for i in store.list_public_apps(limit=None)}
            self.assertEqual(items["app0000"]["download_count"], 2)
            self.assertEqual(items["app0000"]["visit_count"], 3)
            self.assertEqual(items["app0001"]["download_count"], 1)

    def test_search_matches_beyond_first_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store_with_apps(tmp, 65)
            # The oldest app (index 0) must still be findable — the old
            # endpoint capped the candidate set at the newest 1000/60 rows.
            hits = store.list_public_apps(search="App 0", limit=None)
            self.assertIn("app0000", {i["app_id"] for i in hits})


if __name__ == "__main__":
    unittest.main()
