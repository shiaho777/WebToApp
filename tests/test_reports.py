"""Abuse reports + admin takedown (#240): public report endpoint, admin
review queue, and takedown that unpublishes and resolves open reports.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from server import main
from server.community_store import CommunityStore
from server.history_store import HistoryStore


def _real_icon_png() -> bytes:
    import io
    from PIL import Image
    image = Image.new("RGBA", (4, 4))
    px = image.load()
    px[0, 0] = (255, 0, 0, 255)
    px[1, 0] = (0, 255, 0, 255)
    px[0, 1] = (0, 0, 255, 255)
    px[1, 1] = (255, 255, 0, 255)
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


class ReportAndTakedownTests(unittest.TestCase):
    FP = "report-test-fp"

    def setUp(self):
        self.client = TestClient(main.app)
        self._tmp = tempfile.TemporaryDirectory()
        self.apps_dir = Path(self._tmp.name)
        self._orig = (main.APPS_DIR, main.history_store, main.community_store)
        main.APPS_DIR = self.apps_dir
        main.history_store = HistoryStore(self.apps_dir / "_history.sqlite3")
        main.community_store = CommunityStore(self.apps_dir / "_community.sqlite3")
        main.report_rate_limiter._buckets.clear()
        self._make_app("badapp01")

    def tearDown(self):
        main.APPS_DIR, main.history_store, main.community_store = self._orig
        self._tmp.cleanup()

    def _make_app(self, app_id):
        (self.apps_dir / app_id).mkdir(parents=True, exist_ok=True)
        recipe = {
            "id": app_id, "name": "Bad App", "url": f"https://{app_id}.test",
            "visibility": "public", "tags": ["tools"], "edit_token": "tok",
        }
        (self.apps_dir / app_id / "recipe.json").write_text(json.dumps(recipe))
        (self.apps_dir / app_id / "icon.png").write_bytes(_real_icon_png())
        main.history_store.record_build(self.FP, recipe, f"/a/{app_id}", None)

    def _cookies(self):
        return {"webtoapp_device_fingerprint": self.FP}

    def test_report_requires_reason_and_existing_app(self):
        self.assertEqual(
            self.client.post("/api/apps/badapp01/report", json={"reason": ""}).status_code, 422)
        self.assertEqual(
            self.client.post("/api/apps/missing1/report", json={"reason": "phishing"}).status_code, 404)

    def test_report_is_stored_and_listed_for_admin(self):
        resp = self.client.post("/api/apps/badapp01/report",
                                json={"reason": "phishing page"}, cookies=self._cookies())
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["reported"])
        # Admin queue requires the token.
        self.assertEqual(self.client.get("/api/admin/reports").status_code, 403)
        with mock.patch.object(main.config, "admin_token", return_value="admintok"):
            ok = self.client.get("/api/admin/reports", headers={"X-Admin-Token": "admintok"})
        self.assertEqual(ok.status_code, 200)
        reports = ok.json()["reports"]
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0]["app_id"], "badapp01")
        self.assertEqual(reports[0]["reason"], "phishing page")
        self.assertEqual(reports[0]["status"], "open")

    def test_report_rate_limited(self):
        codes = [
            self.client.post("/api/apps/badapp01/report", json={"reason": "spam"}).status_code
            for _ in range(main.report_rate_limiter.max_requests + 1)
        ]
        self.assertEqual(codes[-1], 429)
        self.assertTrue(all(c == 200 for c in codes[:-1]))

    def test_takedown_unpublishes_and_resolves_reports(self):
        self.client.post("/api/apps/badapp01/report", json={"reason": "malware"}, cookies=self._cookies())
        # Without token -> 403, app stays public.
        self.assertEqual(self.client.post("/api/admin/apps/badapp01/takedown").status_code, 403)
        self.assertEqual(main.history_store.get_app_visibility("badapp01")["visibility"], "public")
        with mock.patch.object(main.config, "admin_token", return_value="admintok"):
            resp = self.client.post("/api/admin/apps/badapp01/takedown",
                                    headers={"X-Admin-Token": "admintok"})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["taken_down"])
        self.assertEqual(resp.json()["resolved_reports"], 1)
        self.assertEqual(main.history_store.get_app_visibility("badapp01")["visibility"], "private")
        stored = json.loads((self.apps_dir / "badapp01" / "recipe.json").read_text())
        self.assertEqual(stored["visibility"], "private")
        # Market no longer lists it; open queue is empty.
        ids = [i["app_id"] for i in self.client.get("/api/market").json()["items"]]
        self.assertNotIn("badapp01", ids)
        with mock.patch.object(main.config, "admin_token", return_value="admintok"):
            queue = self.client.get("/api/admin/reports", headers={"X-Admin-Token": "admintok"}).json()
        self.assertEqual(queue["reports"], [])

    def test_takedown_missing_app(self):
        with mock.patch.object(main.config, "admin_token", return_value="admintok"):
            resp = self.client.post("/api/admin/apps/missing1/takedown",
                                    headers={"X-Admin-Token": "admintok"})
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()