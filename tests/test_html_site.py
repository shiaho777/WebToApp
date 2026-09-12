"""Tests for the HTML-to-App feature: staging, validation, serving, endpoints."""

import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from server import html_site
from server.engine.distiller import Distiller


def _zip_bytes(entries):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in entries.items():
            z.writestr(name, data)
    return buf.getvalue()


INDEX_HTML = b"""<!DOCTYPE html>
<html><head>
<title>My Html App</title>
<meta name="theme-color" content="#123456">
<link rel="apple-touch-icon" href="icon.png">
</head><body><h1>Hello</h1></body></html>"""

TINY_PNG = Distiller()._make_placeholder_png("#123456", 16)


class ValidateAndExtractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_single_html_file_staged_as_index(self):
        dest = self.tmp / "site"
        info = html_site.validate_and_extract(INDEX_HTML, "app.html", dest)
        self.assertEqual((dest / "index.html").read_bytes(), INDEX_HTML)
        self.assertEqual(info["index_name"], "index.html")
        self.assertEqual(info["file_count"], 1)
        self.assertEqual(info["total_bytes"], len(INDEX_HTML))
        self.assertTrue(info["content_hash"])

    def test_zip_with_single_root_flattens(self):
        data = _zip_bytes({"mysite/index.html": INDEX_HTML, "mysite/app.js": b"console.log(1)"})
        dest = self.tmp / "site"
        info = html_site.validate_and_extract(data, "site.zip", dest)
        self.assertEqual((dest / "index.html").read_bytes(), INDEX_HTML)
        self.assertEqual((dest / "app.js").read_bytes(), b"console.log(1)")
        self.assertEqual(info["file_count"], 2)

    def test_zip_keeps_layout_with_root_files(self):
        data = _zip_bytes({"index.html": INDEX_HTML, "img/logo.png": TINY_PNG})
        dest = self.tmp / "site"
        html_site.validate_and_extract(data, "site.zip", dest)
        self.assertTrue((dest / "img" / "logo.png").is_file())

    def test_zip_without_index_rejected(self):
        data = _zip_bytes({"about.html": b"<p>x</p>"})
        dest = self.tmp / "site"
        with self.assertRaises(html_site.HtmlUploadError):
            html_site.validate_and_extract(data, "site.zip", dest)
        self.assertFalse(dest.exists())

    def test_zip_slip_rejected(self):
        data = _zip_bytes({"../evil.txt": b"boom", "index.html": INDEX_HTML})
        dest = self.tmp / "site"
        with self.assertRaises(html_site.HtmlUploadError):
            html_site.validate_and_extract(data, "site.zip", dest)
        self.assertFalse((self.tmp / "evil.txt").exists())

    def test_absolute_path_entry_rejected(self):
        data = _zip_bytes({"/etc/passwd": b"boom"})
        with self.assertRaises(html_site.HtmlUploadError):
            html_site.validate_and_extract(data, "site.zip", self.tmp / "site")

    def test_file_count_cap(self):
        entries = {f"f{i}.txt": b"x" for i in range(5)}
        entries["index.html"] = INDEX_HTML
        data = _zip_bytes(entries)
        with patch.object(html_site.config, "html_site_max_file_count", return_value=3):
            with self.assertRaises(html_site.HtmlUploadError):
                html_site.validate_and_extract(data, "site.zip", self.tmp / "site")

    def test_uncompressed_size_cap(self):
        entries = {"index.html": INDEX_HTML, "big.bin": b"a" * (64 * 1024 + 1)}
        data = _zip_bytes(entries)
        with patch.object(html_site.config, "html_site_max_uncompressed_bytes", return_value=64 * 1024):
            with self.assertRaises(html_site.HtmlUploadError):
                html_site.validate_and_extract(data, "site.zip", self.tmp / "site")

    def test_junk_entries_filtered_anywhere(self):
        data = _zip_bytes({
            "index.html": INDEX_HTML,
            "__MACOSX/junk": b"junk",
            "nested/__MACOSX/junk": b"junk",
            "nested/.DS_Store": b"junk",
        })
        dest = self.tmp / "site"
        info = html_site.validate_and_extract(data, "site.zip", dest)
        self.assertEqual(info["file_count"], 1)
        self.assertFalse((dest / "__MACOSX").exists())
        self.assertFalse((dest / "nested").exists())

    def test_unsupported_extension_rejected(self):
        with self.assertRaises(html_site.HtmlUploadError):
            html_site.validate_and_extract(b"x", "app.exe", self.tmp / "site")

    def test_empty_upload_rejected(self):
        with self.assertRaises(html_site.HtmlUploadError):
            html_site.validate_and_extract(b"", "app.html", self.tmp / "site")


class AppIdAndStagingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_app_id_stable_for_same_content_and_name(self):
        first = html_site.app_id_for("hash123", "My App")
        second = html_site.app_id_for("hash123", "My App")
        self.assertEqual(first, second)
        self.assertNotEqual(first, html_site.app_id_for("hash123", "Other"))
        self.assertNotEqual(first, html_site.app_id_for("hash456", "My App"))

    def test_stage_html_app_writes_under_apps_dir(self):
        data = _zip_bytes({"index.html": INDEX_HTML})
        info = html_site.stage_html_app(data, "site.zip", "My App", self.tmp)
        site_dir = self.tmp / info["app_id"] / "site"
        self.assertEqual(site_dir, info["site_dir"])
        self.assertTrue((site_dir / "index.html").is_file())
        # No staging leftovers.
        self.assertEqual([p.name for p in self.tmp.iterdir() if p.name.startswith(".stage-")], [])

    def test_stage_html_app_replaces_previous_site(self):
        data = _zip_bytes({"index.html": INDEX_HTML})
        info = html_site.stage_html_app(data, "site.zip", "My App", self.tmp)
        site_dir = self.tmp / info["app_id"] / "site"
        (site_dir / "old.txt").write_bytes(b"stale")
        html_site.stage_html_app(data, "site.zip", "My App", self.tmp)
        self.assertFalse((site_dir / "old.txt").exists())
        self.assertTrue((site_dir / "index.html").is_file())

    def test_stage_failure_leaves_nothing(self):
        data = _zip_bytes({"nope.txt": b"x"})
        with self.assertRaises(html_site.HtmlUploadError):
            html_site.stage_html_app(data, "site.zip", "My App", self.tmp)
        self.assertEqual(list(self.tmp.iterdir()), [])


class ResolveAndMetaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.site = self.tmp / "site"
        html_site.restore_site_files(self.site, [
            {"name": "index.html", "data": INDEX_HTML},
            {"name": "icon.png", "data": TINY_PNG},
            {"name": "sub/page.html", "data": b"<p>sub</p>"},
            {"name": "sub/index.html", "data": b"<p>sub home</p>"},
        ])

    def test_resolve_index_and_files(self):
        # resolve() follows symlinks (/var → /private/var on macOS), so compare
        # against resolved expectations rather than literal joins.
        self.assertEqual(html_site.resolve_site_file(self.site, ""), (self.site / "index.html").resolve())
        self.assertEqual(html_site.resolve_site_file(self.site, "index.html"), (self.site / "index.html").resolve())
        self.assertEqual(html_site.resolve_site_file(self.site, "icon.png"), (self.site / "icon.png").resolve())
        self.assertEqual(html_site.resolve_site_file(self.site, "sub/page.html"), (self.site / "sub" / "page.html").resolve())

    def test_resolve_directory_falls_back_to_index(self):
        self.assertEqual(html_site.resolve_site_file(self.site, "sub"), (self.site / "sub").resolve() / "index.html")
        self.assertIsNone(html_site.resolve_site_file(self.site, "sub/nested-missing/"))

    def test_resolve_traversal_blocked(self):
        # Paths that resolve back INSIDE the site dir are allowed (they name
        # the same file); only real escapes are rejected.
        self.assertEqual(html_site.resolve_site_file(self.site, "../site/icon.png"), (self.site / "icon.png").resolve())
        self.assertIsNone(html_site.resolve_site_file(self.site, "../../etc/passwd"))
        self.assertIsNone(html_site.resolve_site_file(self.site, "../outside.txt"))

    def test_mime_types(self):
        self.assertEqual(html_site.mime_for(Path("a.html")), "text/html; charset=utf-8")
        self.assertEqual(html_site.mime_for(Path("a.js")), "text/javascript; charset=utf-8")
        self.assertEqual(html_site.mime_for(Path("a.png")), "image/png")
        self.assertEqual(html_site.mime_for(Path("a.xyz")), "application/octet-stream")

    def test_extract_site_meta(self):
        meta = html_site.extract_site_meta(self.site)
        self.assertEqual(meta["title"], "My Html App")
        self.assertEqual(meta["theme_color"], "#123456")
        self.assertEqual(meta["icon_png"], TINY_PNG)

    def test_extract_site_meta_data_url_icon(self):
        site = self.tmp / "site2"
        import base64

        html = (
            b'<html><head><title>T</title>'
            + b'<link rel="icon" href="data:image/png;base64,'
            + base64.b64encode(TINY_PNG)
            + b'"></head></html>'
        )
        html_site.restore_site_files(site, [{"name": "index.html", "data": html}])
        meta = html_site.extract_site_meta(site)
        self.assertEqual(meta["icon_png"], TINY_PNG)

    def test_extract_site_meta_ignores_corrupt_data_url_icon(self):
        site = self.tmp / "site3"
        html = b'<html><head><link rel="icon" href="data:image/png;base64,iVBORw0KGgo="></head></html>'
        html_site.restore_site_files(site, [{"name": "index.html", "data": html}])
        meta = html_site.extract_site_meta(site)
        self.assertIsNone(meta["icon_png"])

    def test_restore_rejects_unsafe_and_missing_index(self):
        with self.assertRaises(html_site.HtmlUploadError):
            html_site.restore_site_files(self.tmp / "bad1", [{"name": "../x.txt", "data": b"x"}])
        with self.assertRaises(html_site.HtmlUploadError):
            html_site.restore_site_files(self.tmp / "bad2", [{"name": "a.txt", "data": b"x"}])


class DistillerHtmlModeTests(unittest.TestCase):
    def test_create_recipe_html_fields(self):
        distiller = Distiller()
        recipe = distiller.create_recipe(
            app_id="ab12cd34", url="https://self.test/a/ab12cd34/site/index.html",
            name="App", color="#123456", display="fullscreen", orientation="any",
            options={}, source_type="html", content_hash="c0ffee",
        )
        self.assertEqual(recipe["source_type"], "html")
        self.assertEqual(recipe["content_hash"], "c0ffee")

    def test_create_recipe_url_mode_has_no_content_hash(self):
        distiller = Distiller()
        recipe = distiller.create_recipe(
            app_id="ab12cd34", url="https://example.com",
            name="App", color="#123456", display="fullscreen", orientation="any", options={},
        )
        self.assertEqual(recipe["source_type"], "url")
        self.assertNotIn("content_hash", recipe)

    def test_fetch_icon_uses_local_site_icon_for_html(self):
        distiller = Distiller()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            html_site.restore_site_files(root / "ab12cd34" / "site", [{"name": "index.html", "data": INDEX_HTML},
                                                                      {"name": "icon.png", "data": TINY_PNG}])
            with patch.object(distiller, "_generated_root", return_value=root):
                recipe = {"id": "ab12cd34", "url": "https://x/", "color": "#123456", "source_type": "html"}
                icon = distiller._fetch_icon(recipe)
        self.assertEqual(icon, TINY_PNG)

    def test_fetch_icon_falls_back_to_placeholder(self):
        distiller = Distiller()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            html_site.restore_site_files(root / "ab12cd34" / "site", [{"name": "index.html", "data": b"<p>no icon</p>"}])
            with patch.object(distiller, "_generated_root", return_value=root):
                recipe = {"id": "ab12cd34", "url": "https://x/", "color": "#112233", "source_type": "html"}
                icon = distiller._fetch_icon(recipe)
        self.assertEqual(icon, distiller._make_placeholder_png("#112233"))

    def test_download_page_marks_html_apps(self):
        distiller = Distiller()
        with tempfile.TemporaryDirectory() as tmp:
            app_dir = Path(tmp) / "ab12cd34"
            recipe = distiller.create_recipe(
                app_id="ab12cd34", url="https://self.test/a/ab12cd34/site/index.html",
                name="App", color="#123456", display="fullscreen", orientation="any",
                options={}, source_type="html",
            )
            html = distiller.render_download_page(app_dir, recipe)
        self.assertIn('data-i18n="openApp"', html)
        self.assertIn("HTML App", html)
        # URL-mode pages keep the original label.
        url_recipe = distiller.create_recipe(
            app_id="ab12cd34", url="https://example.com",
            name="App", color="#123456", display="fullscreen", orientation="any", options={},
        )
        url_html = distiller.render_download_page(app_dir, url_recipe)
        self.assertIn('data-i18n="openSite"', url_html)


class HtmlAppEndpointTests(unittest.TestCase):
    def setUp(self):
        from server import main

        self.main = main
        self.client = TestClient(main.app)
        self.tmp = Path(tempfile.mkdtemp())
        self._apps_dir = main.APPS_DIR
        main.APPS_DIR = self.tmp
        self._allow = main.distill_rate_limiter.allow
        main.distill_rate_limiter.allow = AsyncMock(return_value=True)

    def tearDown(self):
        self.main.APPS_DIR = self._apps_dir
        self.main.distill_rate_limiter.allow = self._allow

    def test_analyze_html_endpoint(self):
        resp = self.client.post(
            "/api/analyze/html",
            files={"file": ("app.html", INDEX_HTML, "text/html")},
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["sourceType"], "html")
        self.assertEqual(body["name"], "My Html App")
        self.assertEqual(body["color"], "#123456")
        self.assertEqual(body["fileCount"], 1)
        self.assertTrue(body["iconDataUrl"].startswith("data:image/png;base64,") if body["iconDataUrl"] else True)

    def test_analyze_html_rejects_bad_zip(self):
        resp = self.client.post(
            "/api/analyze/html",
            files={"file": ("app.zip", b"not a zip", "application/zip")},
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["detail"]["code"], "htmlUpload.invalid")

    def test_distill_html_stages_and_submits(self):
        submitted = {}

        async def fake_submit(payload):
            submitted.update(payload)
            return {"task_id": "t1", "app_id": payload.get("app_id"), "status": "pending"}

        data = _zip_bytes({"index.html": INDEX_HTML, "icon.png": TINY_PNG})
        with patch.object(self.main.distill_queue, "submit", side_effect=fake_submit):
            resp = self.client.post(
                "/api/distill/html",
                files={"file": ("site.zip", data, "application/zip")},
                data={"name": "My App", "color": "#123456", "options": json.dumps({"feature-desktop-mode": True})},
            )
        self.assertEqual(resp.status_code, 202)
        body = resp.json()
        self.assertEqual(body["status"], "pending")
        self.assertEqual(submitted["source_type"], "html")
        self.assertEqual(submitted["name"], "My App")
        self.assertEqual(submitted["options"], {"feature-desktop-mode": True})
        site_dir = self.tmp / submitted["app_id"] / "site"
        self.assertTrue((site_dir / "index.html").is_file())
        self.assertTrue((site_dir / "icon.png").is_file())

    def test_distill_html_rejects_oversized(self):
        big = b"<html>" + b"x" * (64 * 1024 + 16)
        with patch.object(self.main.config, "html_upload_max_bytes", return_value=64 * 1024):
            resp = self.client.post(
                "/api/distill/html",
                files={"file": ("big.html", big, "text/html")},
                data={},
            )
        self.assertEqual(resp.status_code, 413)
        self.assertEqual(resp.json()["detail"]["code"], "htmlUpload.tooLarge")

    def test_serve_app_site_routes(self):
        app_id = "ff001122"
        html_site.restore_site_files(self.tmp / app_id / "site", [
            {"name": "index.html", "data": INDEX_HTML},
            {"name": "app.js", "data": b"console.log(1);"},
            {"name": "img/logo.png", "data": TINY_PNG},
        ])
        root = self.client.get(f"/a/{app_id}/site")
        self.assertEqual(root.status_code, 200)
        self.assertIn("text/html", root.headers["content-type"])
        self.assertIn(b"My Html App", root.content)

        js = self.client.get(f"/a/{app_id}/site/app.js")
        self.assertEqual(js.status_code, 200)
        self.assertIn("text/javascript", js.headers["content-type"])
        self.assertIn("max-age=3600", js.headers.get("cache-control", ""))

        png = self.client.get(f"/a/{app_id}/site/img/logo.png")
        self.assertEqual(png.status_code, 200)
        self.assertEqual(png.headers["content-type"], "image/png")

        missing = self.client.get(f"/a/{app_id}/site/nope.css")
        self.assertEqual(missing.status_code, 404)

        unknown_app = self.client.get("/a/deadbeef/site/index.html")
        self.assertEqual(unknown_app.status_code, 404)

    def test_patch_url_rejected_for_html_apps(self):
        app_id = "ab99cd88"
        app_dir = self.tmp / app_id
        app_dir.mkdir(parents=True)
        (app_dir / "recipe.json").write_text(json.dumps({
            "id": app_id, "url": "https://self.test/a/ab99cd88/site/index.html",
            "source_type": "html", "edit_token": "tok",
        }))
        resp = self.client.patch(
            f"/api/app/{app_id}/url",
            json={"url": "https://evil.test", "edit_token": "tok"},
        )
        self.assertEqual(resp.status_code, 409)


class BuildResponseAndImportTests(unittest.TestCase):
    def test_build_distill_response_derives_html_url(self):
        from server import main

        payload = {
            "source_type": "html",
            "app_id": "ab12cd34",
            "content_hash": "c0ffee",
            "site_index": "index.html",
            "name": "App",
            "color": "#123456",
            "display": "fullscreen",
            "orientation": "any",
            "options": {},
            "base_url": "https://self.test",
        }
        with tempfile.TemporaryDirectory() as tmp:
            apps_dir = Path(tmp)
            with patch.object(main, "APPS_DIR", apps_dir), \
                 patch.object(main.distiller, "write_app_files", return_value={
                     "ios": {}, "android": {}, "runtime_url": "", "platform_errors": {},
                 }) as write_mock, \
                 patch.object(main.history_store, "record_build") as record_mock:
                result = main._build_distill_response(payload)
        recipe = result["recipe"]
        self.assertEqual(recipe["source_type"], "html")
        self.assertEqual(recipe["content_hash"], "c0ffee")
        self.assertEqual(recipe["url"], "https://self.test/a/ab12cd34/site/index.html")
        write_mock.assert_called_once()
        record_mock.assert_called_once()

    def test_import_recipe_rederives_html_url(self):
        from server import main

        item = {
            "app_id": "ab12cd34",
            "recipe": {
                "id": "ab12cd34",
                "url": "https://old-server.test/a/ab12cd34/site/index.html",
                "source_type": "html",
                "content_hash": "c0ffee",
                "name": "App",
            },
        }
        recipe = main._import_recipe_from_payload(item, base_url="https://new-server.test")
        self.assertEqual(recipe["url"], "https://new-server.test/a/ab12cd34/site/index.html")
        self.assertEqual(recipe["source_type"], "html")
        self.assertEqual(recipe["content_hash"], "c0ffee")

    def test_import_recipe_url_mode_unchanged(self):
        from server import main

        item = {"app_id": "id1x", "recipe": {"id": "id1x", "url": "https://example.com", "name": "X"}}
        recipe = main._import_recipe_from_payload(item, base_url="https://new-server.test")
        self.assertEqual(recipe["url"], "https://example.com")
        self.assertEqual(recipe["source_type"], "url")

    def test_decode_site_files(self):
        from server import main
        import base64

        item = {"site_files": [
            {"name": "index.html", "data": base64.b64encode(INDEX_HTML).decode("ascii")},
            {"name": "icon.png", "data": base64.b64encode(TINY_PNG).decode("ascii")},
        ]}
        files = main._decode_site_files(item)
        self.assertEqual(files[0]["name"], "index.html")
        self.assertEqual(files[0]["data"], INDEX_HTML)
        self.assertIsNone(main._decode_site_files({}))


if __name__ == "__main__":
    unittest.main()
