"""Flat-icon reviews: 48 hours to replace the picture, then leave the market.

Publishing itself is gated on a usable icon (#232); this cure window only
applies to apps already public when their icon fails detection.
"""

import io
import json
import tempfile
import unittest
import unittest.mock
import zipfile
from pathlib import Path

from PIL import Image

from server.engine.distiller import Distiller
from server.history_store import HistoryStore
from server.icon_review import (
    NOTICE_AT,
    enforce_icon_review_deadlines,
    run_icon_review_pass,
    shorten_open_reviews,
)


def _solid_png():
    image = Image.new("RGBA", (8, 8), (124, 58, 237, 255))
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def _real_png():
    image = Image.new("RGBA", (4, 4))
    pixels = image.load()
    pixels[0, 0] = (255, 0, 0, 255)
    pixels[1, 0] = (0, 255, 0, 255)
    pixels[0, 1] = (0, 0, 255, 255)
    pixels[1, 1] = (255, 255, 0, 255)
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


class IconReviewTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.apps = Path(self._tmp.name)
        self.history = HistoryStore(self.apps / "_history.json")

    def tearDown(self):
        self._tmp.cleanup()

    def _public(self, app_id, created_at):
        app_dir = self.apps / app_id
        app_dir.mkdir(parents=True)
        recipe = {
            "id": app_id,
            "name": "Flat",
            "url": f"https://{app_id}.example",
            "visibility": "public",
            "tags": ["tools"],
            "edit_token": "tok",
        }
        (app_dir / "recipe.json").write_text(json.dumps(recipe), encoding="utf-8")
        self.history.record_build("fp", recipe, f"/a/{app_id}", None)
        with self.history._lock:
            self.history._conn.execute(
                "UPDATE apps SET created_at = ? WHERE app_id = ?",
                (created_at, app_id),
            )
        return app_dir

    def test_open_review_keeps_its_first_deadline(self):
        self.assertTrue(self.history.flag_icon_review("abc", flagged_at=NOTICE_AT))
        self.assertFalse(self.history.flag_icon_review("abc", flagged_at="2026-10-18T00:00:00Z"))
        review = self.history.open_icon_reviews()["abc"]
        self.assertEqual(review["deadline_at"], "2026-10-15T16:00:00Z")

    def test_packaged_flat_icon_is_due_with_the_notice(self):
        app_dir = self._public("oldflat1", "2026-09-01T00:00:00Z")
        downloads = app_dir / "downloads"
        downloads.mkdir()
        with zipfile.ZipFile(downloads / "windows.zip", "w") as bundle:
            bundle.writestr("Flat/icon.png", _solid_png())
        summary = run_icon_review_pass(self.history, self.apps, now="2026-10-14T00:00:00Z")
        self.assertEqual(summary["flagged"], ["oldflat1"])
        self.assertEqual(summary["unpublished"], [])
        self.assertEqual(
            self.history.open_icon_reviews()["oldflat1"]["deadline_at"],
            "2026-10-15T16:00:00Z",
        )

    def test_past_deadline_without_a_picture_leaves_the_market(self):
        app_dir = self._public("lateflat", "2026-09-01T00:00:00Z")
        downloads = app_dir / "downloads"
        downloads.mkdir()
        with zipfile.ZipFile(downloads / "windows.zip", "w") as bundle:
            bundle.writestr("Flat/icon.png", _solid_png())
        run_icon_review_pass(self.history, self.apps, now="2026-10-14T00:00:00Z")
        unpublished = enforce_icon_review_deadlines(
            self.history, self.apps, now="2026-10-16T00:00:00Z",
        )
        self.assertEqual(unpublished, ["lateflat"])
        self.assertEqual(self.history.get_app_visibility("lateflat")["visibility"], "private")
        stored = json.loads((app_dir / "recipe.json").read_text(encoding="utf-8"))
        self.assertEqual(stored["visibility"], "private")
        self.assertEqual(stored["edit_token"], "tok")

    def test_a_real_icon_closes_the_review_before_the_deadline(self):
        app_dir = self._public("fixed001", "2026-09-01T00:00:00Z")
        downloads = app_dir / "downloads"
        downloads.mkdir()
        with zipfile.ZipFile(downloads / "windows.zip", "w") as bundle:
            bundle.writestr("Flat/icon.png", _solid_png())
        run_icon_review_pass(self.history, self.apps, now="2026-10-14T00:00:00Z")
        (app_dir / "icon.png").write_bytes(_real_png())
        self.assertEqual(
            enforce_icon_review_deadlines(self.history, self.apps, now="2026-10-14T00:00:00Z"),
            [],
        )
        self.assertEqual(self.history.open_icon_reviews(), {})
        self.assertEqual(self.history.get_app_visibility("fixed001")["visibility"], "public")

    def test_new_flag_defaults_to_48_hours(self):
        self.assertTrue(self.history.flag_icon_review("fresh001", flagged_at="2026-11-16T10:00:00Z"))
        review = self.history.open_icon_reviews()["fresh001"]
        self.assertEqual(review["deadline_at"], "2026-11-18T10:00:00Z")

    def test_legacy_seven_day_reviews_are_capped_to_48h(self):
        # Simulate a review opened under the old 7-day rule.
        self.assertTrue(self.history.flag_icon_review("legacy01", flagged_at="2026-11-16T10:00:00Z"))
        self.history.set_icon_review_deadline("legacy01", "2026-11-23T10:00:00Z")
        changed = shorten_open_reviews(self.history)
        self.assertEqual(changed, 1)
        self.assertEqual(
            self.history.open_icon_reviews()["legacy01"]["deadline_at"],
            "2026-11-18T10:00:00Z",
        )
        # Idempotent: a second pass changes nothing.
        self.assertEqual(shorten_open_reviews(self.history), 0)

    def test_sweep_enforces_the_capped_deadline(self):
        # Created before the notice anchor so the flag time is NOTICE_AT
        # (post-notice apps are flagged at the real current time).
        app_dir = self._public("capped01", "2026-09-01T00:00:00Z")
        downloads = app_dir / "downloads"
        downloads.mkdir()
        with zipfile.ZipFile(downloads / "windows.zip", "w") as bundle:
            bundle.writestr("Flat/icon.png", _solid_png())
        run_icon_review_pass(self.history, self.apps, now="2026-10-14T00:00:00Z")
        # Still inside the 48h window (deadline 2026-10-15T16:00Z): stays public.
        self.assertEqual(
            enforce_icon_review_deadlines(self.history, self.apps, now="2026-10-14T12:00:00Z"),
            [],
        )
        # Past 48h with no replacement: leaves the market.
        self.assertEqual(
            enforce_icon_review_deadlines(self.history, self.apps, now="2026-10-16T00:00:00Z"),
            ["capped01"],
        )

    def test_html_solid_favicon_is_flagged_on_fetch(self):
        distiller = Distiller()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            site = root / "ab12cd34" / "site"
            site.mkdir(parents=True)
            (site / "index.html").write_text(
                '<link rel="icon" href="icon.png">', encoding="utf-8"
            )
            (site / "icon.png").write_bytes(_solid_png())
            with unittest.mock.patch.object(distiller, "_generated_root", return_value=root):
                recipe = {"id": "ab12cd34", "source_type": "html", "url": "https://x/"}
                self.assertIsNone(distiller._fetch_icon(recipe))
        self.assertEqual(recipe["_icon_rejected"], "solid")
