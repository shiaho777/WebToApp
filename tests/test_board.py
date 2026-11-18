"""Site feedback board (#248): tagged threads, hourly cap, 500-char limit,
image caps, toggleable likes (no double-like), threaded replies, and cascade
delete that removes replies + image files.
"""

import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient
from PIL import Image

from server import main
from server.community_store import CommunityStore
from server.history_store import HistoryStore


def _png_bytes(color=(200, 120, 80), size=(40, 30)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


class BoardTests(unittest.TestCase):
    FP = "board-test-fp"
    FP2 = "board-test-fp-2"

    def setUp(self):
        self.client = TestClient(main.app)
        self._tmp = tempfile.TemporaryDirectory()
        self.apps_dir = Path(self._tmp.name)
        self._orig = (main.APPS_DIR, main.BOARD_IMG_DIR, main.history_store, main.community_store)
        main.APPS_DIR = self.apps_dir
        main.BOARD_IMG_DIR = self.apps_dir / "_board"
        main.BOARD_IMG_DIR.mkdir(exist_ok=True)
        main.history_store = HistoryStore(self.apps_dir / "_history.sqlite3")
        main.community_store = CommunityStore(self.apps_dir / "_community.sqlite3")
        main.board_hourly_limiter._buckets.clear()
        main.comment_rate_limiter._buckets.clear()

    def tearDown(self):
        main.APPS_DIR, main.BOARD_IMG_DIR, main.history_store, main.community_store = self._orig
        self._tmp.cleanup()

    def _cookies(self, fp=None):
        return {"webtoapp_device_fingerprint": fp or self.FP}

    def _post_topic(self, tag="suggestion", body="A great idea", fp=None, files=None):
        data = {"tag": tag, "body": body}
        return self.client.post("/api/board/topics", data=data,
                                files=files or [], cookies=self._cookies(fp))

    def test_tag_required_and_validated(self):
        self.assertEqual(self._post_topic(tag="").status_code, 422)
        self.assertEqual(self._post_topic(tag="rant").status_code, 422)
        for i, tag in enumerate(("suggestion", "question", "help")):
            self.assertEqual(
                self._post_topic(tag=tag, body=f"about {tag}", fp=f"tag-fp-{i}").status_code, 200)

    def test_body_required_and_500_cap(self):
        self.assertEqual(self._post_topic(body="").status_code, 422)
        self.assertEqual(self._post_topic(body="x" * 500).status_code, 200)
        self.assertEqual(self._post_topic(body="x" * 501).status_code, 422)

    def test_hourly_cap_three_per_identity(self):
        for i in range(3):
            self.assertEqual(self._post_topic(body=f"idea {i}").status_code, 200)
        resp = self._post_topic(body="fourth")
        self.assertEqual(resp.status_code, 429)
        self.assertEqual(resp.headers.get("retry-after"), "600")
        # A different identity has its own budget.
        self.assertEqual(self._post_topic(body="other user", fp=self.FP2).status_code, 200)

    def test_list_filter_and_pagination(self):
        for i in range(5):
            self._post_topic(tag="question", body=f"q{i}", fp=f"fp-{i}")
        self._post_topic(tag="help", body="need help", fp="fp-help")
        listing = self.client.get("/api/board/topics?tag=question&limit=2").json()
        self.assertEqual(listing["total"], 5)
        self.assertEqual(len(listing["items"]), 2)
        self.assertTrue(listing["has_more"])
        self.assertTrue(all(i["tag"] == "question" for i in listing["items"]))
        page2 = self.client.get("/api/board/topics?tag=question&limit=2&offset=2").json()
        self.assertEqual(page2["offset"], 2)
        ids1 = {i["id"] for i in listing["items"]}
        ids2 = {i["id"] for i in page2["items"]}
        self.assertFalse(ids1 & ids2)

    def test_like_toggle_no_double_like(self):
        topic = self._post_topic().json()["topic"]
        url = f"/api/board/topic/{topic['id']}/like"
        first = self.client.post(url, cookies=self._cookies()).json()
        self.assertTrue(first["liked"])
        self.assertEqual(first["like_count"], 1)
        # Liking again unlikes (toggle) — never stacks to 2.
        second = self.client.post(url, cookies=self._cookies()).json()
        self.assertFalse(second["liked"])
        self.assertEqual(second["like_count"], 0)
        # A second user liking brings it to 1, and repeated toggles stay bounded.
        self.client.post(url, cookies=self._cookies(self.FP2))
        third = self.client.post(url, cookies=self._cookies()).json()
        self.assertEqual(third["like_count"], 2)
        self.assertTrue(third["liked"])

    def test_reply_and_cascade_delete(self):
        topic = self._post_topic().json()["topic"]
        tid = topic["id"]
        r1 = self.client.post(f"/api/board/topics/{tid}/replies",
                              data={"body": "reply one"}, cookies=self._cookies(self.FP2)).json()["reply"]
        r2 = self.client.post(f"/api/board/topics/{tid}/replies",
                              data={"body": "reply two"}, cookies=self._cookies()).json()["reply"]
        # like a reply too, to verify likes are cleaned on cascade
        self.client.post(f"/api/board/reply/{r1['id']}/like", cookies=self._cookies())
        detail = self.client.get(f"/api/board/topics/{tid}").json()["topic"]
        self.assertEqual(detail["reply_count"], 2)
        # Deleting the topic must remove BOTH replies.
        resp = self.client.delete(f"/api/board/topics/{tid}", cookies=self._cookies())
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.client.get(f"/api/board/topics/{tid}").status_code, 404)
        # replies gone from storage (cascade), and their likes too
        self.assertEqual(main.community_store.board_reply_by_id(r1["id"]), {})
        self.assertEqual(main.community_store.board_reply_by_id(r2["id"]), {})
        with main.community_store._lock:
            like_rows = main.community_store._conn.execute(
                "SELECT COUNT(*) FROM board_likes WHERE target_id IN (?, ?)",
                (r1["id"], r2["id"])).fetchone()[0]
        self.assertEqual(like_rows, 0)

    def test_delete_reply_only_removes_itself(self):
        topic = self._post_topic().json()["topic"]
        tid = topic["id"]
        r1 = self.client.post(f"/api/board/topics/{tid}/replies",
                              data={"body": "keep"}, cookies=self._cookies(self.FP2)).json()["reply"]
        r2 = self.client.post(f"/api/board/topics/{tid}/replies",
                              data={"body": "drop"}, cookies=self._cookies()).json()["reply"]
        self.client.delete(f"/api/board/replies/{r2['id']}", cookies=self._cookies())
        detail = self.client.get(f"/api/board/topics/{tid}").json()["topic"]
        self.assertEqual(detail["reply_count"], 1)
        self.assertEqual(detail["replies"][0]["id"], r1["id"])

    def test_delete_forbidden_for_non_owner(self):
        topic = self._post_topic().json()["topic"]
        resp = self.client.delete(f"/api/board/topics/{topic['id']}", cookies=self._cookies(self.FP2))
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_delete_any(self):
        topic = self._post_topic().json()["topic"]
        with mock.patch.object(main.config, "admin_token", return_value="admintok"):
            resp = self.client.delete(f"/api/board/topics/{topic['id']}",
                                      headers={"X-Admin-Token": "admintok"})
        self.assertEqual(resp.status_code, 200)

    def test_admin_badge_on_reply(self):
        topic = self._post_topic().json()["topic"]
        with mock.patch.object(main.config, "admin_token", return_value="admintok"):
            reply = self.client.post(f"/api/board/topics/{topic['id']}/replies",
                                     data={"body": "admin here"},
                                     headers={"X-Admin-Token": "admintok"},
                                     cookies=self._cookies()).json()["reply"]
        self.assertTrue(reply["is_admin"])

    def test_image_upload_and_serving_and_cleanup(self):
        files = [("images", ("a.png", _png_bytes(), "image/png")),
                 ("images", ("b.png", _png_bytes((10, 20, 30)), "image/png"))]
        topic = self._post_topic(body="with pics", files=files).json()["topic"]
        self.assertEqual(len(topic["images"]), 2)
        url = topic["images"][0]["url"]
        img_resp = self.client.get(url)
        self.assertEqual(img_resp.status_code, 200)
        self.assertEqual(img_resp.headers["content-type"], "image/webp")
        self.assertIn("immutable", img_resp.headers["cache-control"])
        names = [Path(i["url"]).name for i in topic["images"]]
        for n in names:
            self.assertTrue((main.BOARD_IMG_DIR / n).exists())
        # cascade delete removes the files
        self.client.delete(f"/api/board/topics/{topic['id']}", cookies=self._cookies())
        for n in names:
            self.assertFalse((main.BOARD_IMG_DIR / n).exists())

    def test_image_total_cap_5mb(self):
        # Random noise barely compresses, so each PNG is ~3MB raw (under the
        # per-file 5MB cap) but two together exceed the 5MB total.
        import os as _os
        noise = Image.frombytes("RGB", (1000, 1000), _os.urandom(3_000_000))
        buf = io.BytesIO()
        noise.save(buf, format="PNG")
        big = buf.getvalue()
        self.assertLess(len(big), 5 * 1024 * 1024)
        self.assertGreater(len(big) * 2, 5 * 1024 * 1024)
        files = [("images", ("a.png", big, "image/png")),
                 ("images", ("b.png", big, "image/png"))]
        resp = self._post_topic(body="too big", files=files)
        self.assertEqual(resp.status_code, 413)

    def test_bad_image_rejected(self):
        files = [("images", ("x.png", b"not an image at all", "image/png"))]
        self.assertEqual(self._post_topic(body="bad", files=files).status_code, 422)

    def test_reply_image_cleanup_on_reply_delete(self):
        topic = self._post_topic().json()["topic"]
        files = [("images", ("r.png", _png_bytes(), "image/png"))]
        reply = self.client.post(f"/api/board/topics/{topic['id']}/replies",
                                 data={"body": "pic reply"}, files=files,
                                 cookies=self._cookies()).json()["reply"]
        name = Path(reply["images"][0]["url"]).name
        self.assertTrue((main.BOARD_IMG_DIR / name).exists())
        self.client.delete(f"/api/board/replies/{reply['id']}", cookies=self._cookies())
        self.assertFalse((main.BOARD_IMG_DIR / name).exists())


if __name__ == "__main__":
    unittest.main()