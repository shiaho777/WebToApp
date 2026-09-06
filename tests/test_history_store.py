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


if __name__ == "__main__":
    unittest.main()
