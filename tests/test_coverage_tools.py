import json
import runpy
import struct
import sys
import zipfile
from pathlib import Path

import pytest

from server.tools import backfill_r2, check_android_apk_alignment


def _set_tools_root(tmp_path, monkeypatch, *, create_generated=True):
    root = tmp_path / "project"
    if create_generated:
        (root / "generated").mkdir(parents=True)
    fake_file = root / "server" / "tools" / "backfill_r2.py"
    monkeypatch.setattr(backfill_r2, "__file__", str(fake_file))
    return root, root / "generated"


def _tool_app(apps_root: Path, app_id: str, recipe=None) -> Path:
    app = apps_root / app_id
    app.mkdir(parents=True, exist_ok=True)
    (app / "recipe.json").write_text(json.dumps(recipe if recipe is not None else {}))
    return app


def _tool_download(app: Path, name="android.apk", data=b"apk") -> Path:
    downloads = app / "downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    path = downloads / name
    path.write_bytes(data)
    return path


def test_tool_backfill_iter_app_dirs_filters_and_sorts(tmp_path):
    apps = tmp_path / "generated"
    _tool_app(apps, "b-app")
    _tool_app(apps, "a-app")

    assert [path.name for path in backfill_r2._iter_app_dirs(apps, [])] == ["a-app", "b-app"]
    assert [path.name for path in backfill_r2._iter_app_dirs(apps, ["", "b-app"])] == ["b-app"]


def test_tool_backfill_recipe_load_and_save(tmp_path):
    path = tmp_path / "recipe.json"
    path.write_text(json.dumps({"id": "app"}))
    assert backfill_r2._load_recipe(path) == {"id": "app"}

    path.write_text("invalid")
    assert backfill_r2._load_recipe(path) == {}

    backfill_r2._save_recipe(path, {"name": "Café"})
    assert json.loads(path.read_text()) == {"name": "Café"}
    assert "Café" in path.read_text()


def test_tool_backfill_main_requires_r2(monkeypatch, capsys):
    monkeypatch.setattr(backfill_r2.config, "r2_configured", lambda: False)
    assert backfill_r2.main([]) == 2
    assert "R2 not configured" in capsys.readouterr().out


def test_tool_backfill_main_handles_missing_generated(tmp_path, monkeypatch, capsys):
    root, apps = _set_tools_root(tmp_path, monkeypatch, create_generated=False)
    monkeypatch.setattr(backfill_r2.config, "r2_configured", lambda: True)

    assert backfill_r2.main([]) == 0
    assert not apps.exists()
    assert f"No generated/ directory at {root / 'generated'}" in capsys.readouterr().out


def test_tool_backfill_main_dry_run_covers_all_local_skips(tmp_path, monkeypatch, capsys):
    _root, apps = _set_tools_root(tmp_path, monkeypatch)

    existing = _tool_app(apps, "existing", {"downloads_cdn": {"android.apk": "https://old/apk"}})
    _tool_download(existing)

    _tool_app(apps, "no-downloads")

    empty = _tool_app(apps, "empty")
    (empty / "downloads" / "nested").mkdir(parents=True)

    planned = _tool_app(apps, "planned")
    _tool_download(planned, "android.apk")
    _tool_download(planned, "ios.mobileconfig")
    (planned / "downloads" / "nested").mkdir()

    monkeypatch.setattr(backfill_r2.config, "r2_configured", lambda: True)
    monkeypatch.setattr(
        backfill_r2.r2_storage,
        "upload_app_downloads",
        lambda *_args: pytest.fail("dry run must not upload"),
    )

    assert backfill_r2.main(["--dry-run"]) == 0
    output = capsys.readouterr().out
    assert "[skip ] existing: already has 1 CDN URLs" in output
    assert "[skip ] no-downloads: no downloads/ dir" in output
    assert "[skip ] empty: downloads/ empty" in output
    assert "[plan ] planned: would upload 2 files" in output
    assert "apps scanned=4, uploaded=0, skipped=3, dry-run" in output


def test_tool_backfill_main_force_filter_upload_outcomes_and_merge(tmp_path, monkeypatch, capsys):
    _root, apps = _set_tools_root(tmp_path, monkeypatch)

    error = _tool_app(apps, "error")
    (error / "recipe.json").write_text("not-json")
    _tool_download(error)

    no_urls = _tool_app(apps, "no-urls")
    _tool_download(no_urls)

    success = _tool_app(
        apps,
        "success",
        {"downloads_cdn": {"ios.mobileconfig": "https://old/ios"}},
    )
    success_recipe = success / "recipe.json"
    _tool_download(success)

    filtered = _tool_app(apps, "filtered")
    _tool_download(filtered)

    def upload(app_id, _downloads):
        if app_id == "error":
            raise RuntimeError("R2 offline")
        if app_id == "no-urls":
            return {}
        return {"android.apk": "https://cdn.test/success/android.apk"}

    monkeypatch.setattr(backfill_r2.config, "r2_configured", lambda: True)
    monkeypatch.setattr(backfill_r2.r2_storage, "upload_app_downloads", upload)

    result = backfill_r2.main(
        ["--force", "--app", "error", "--app", "no-urls", "--app", "success"]
    )

    assert result == 0
    assert json.loads(success_recipe.read_text())["downloads_cdn"] == {
        "ios.mobileconfig": "https://old/ios",
        "android.apk": "https://cdn.test/success/android.apk",
    }
    output = capsys.readouterr().out
    assert "[error] error: upload failed: R2 offline" in output
    assert "[skip ] no-urls: nothing uploaded" in output
    assert "[ok   ] success: uploaded 1 files" in output
    assert "apps scanned=3, uploaded=1, skipped=1" in output
    assert "dry-run" not in output


def test_tool_backfill_module_entrypoint(monkeypatch):
    monkeypatch.setattr(backfill_r2.config, "r2_configured", lambda: False)
    monkeypatch.setattr(sys, "argv", [backfill_r2.__file__])
    with pytest.raises(SystemExit) as exc_info:
        runpy.run_path(backfill_r2.__file__, run_name="__main__")
    assert exc_info.value.code == 2


def _make_apk(path: Path, entries):
    with zipfile.ZipFile(path, "w") as zf:
        for name, compression in entries:
            zf.writestr(name, b"payload", compress_type=compression)


def test_data_offset_reads_local_header_and_rejects_closed_zip(tmp_path):
    archive = tmp_path / "one.zip"
    _make_apk(archive, [("entry.txt", zipfile.ZIP_STORED)])

    with zipfile.ZipFile(archive) as zf:
        info = zf.getinfo("entry.txt")
        expected = info.header_offset + 30 + len(info.filename.encode()) + len(info.extra)
        assert check_android_apk_alignment._data_offset(zf, info) == expected

    with pytest.raises(RuntimeError, match="zip file is closed"):
        check_android_apk_alignment._data_offset(zf, info)


def test_check_apk_reports_missing_entries(tmp_path):
    apk = tmp_path / "empty.apk"
    _make_apk(apk, [])
    assert check_android_apk_alignment.check_apk(apk) == [
        "missing resources.arsc",
        "missing classes.dex",
        "missing AndroidManifest.xml",
    ]


def test_check_apk_reports_compression_and_alignment(tmp_path, monkeypatch):
    apk = tmp_path / "bad.apk"
    _make_apk(
        apk,
        [
            ("resources.arsc", zipfile.ZIP_DEFLATED),
            ("classes.dex", zipfile.ZIP_STORED),
            ("AndroidManifest.xml", zipfile.ZIP_STORED),
        ],
    )
    offsets = {"resources.arsc": 1, "classes.dex": 2, "AndroidManifest.xml": 3}
    monkeypatch.setattr(
        check_android_apk_alignment,
        "_data_offset",
        lambda _zf, info: offsets[info.filename],
    )

    assert check_android_apk_alignment.check_apk(apk) == [
        "resources.arsc is compressed",
        "resources.arsc offset 1 is not 4-byte aligned",
        "classes.dex offset 2 is not 4-byte aligned",
    ]


def test_check_apk_accepts_stored_aligned_entries(tmp_path, monkeypatch):
    apk = tmp_path / "good.apk"
    _make_apk(
        apk,
        [
            ("resources.arsc", zipfile.ZIP_STORED),
            ("classes.dex", zipfile.ZIP_STORED),
            ("AndroidManifest.xml", zipfile.ZIP_STORED),
        ],
    )
    offsets = {"resources.arsc": 4, "classes.dex": 8, "AndroidManifest.xml": 3}
    monkeypatch.setattr(
        check_android_apk_alignment,
        "_data_offset",
        lambda _zf, info: offsets[info.filename],
    )
    assert check_android_apk_alignment.check_apk(apk) == []


def test_alignment_main_prints_issues_and_success(tmp_path, monkeypatch, capsys):
    apk = tmp_path / "app.apk"
    apk.write_bytes(b"unused because check_apk is mocked")

    monkeypatch.setattr(check_android_apk_alignment, "check_apk", lambda _path: ["bad alignment"])
    monkeypatch.setattr(sys, "argv", ["check-alignment", str(apk)])
    assert check_android_apk_alignment.main() == 1
    assert capsys.readouterr().out == "bad alignment\n"

    monkeypatch.setattr(check_android_apk_alignment, "check_apk", lambda _path: [])
    assert check_android_apk_alignment.main() == 0
    assert capsys.readouterr().out == "ok\n"


def test_alignment_module_entrypoint(tmp_path, monkeypatch):
    apk = tmp_path / "empty.apk"
    _make_apk(apk, [])
    monkeypatch.setattr(sys, "argv", [check_android_apk_alignment.__file__, str(apk)])

    with pytest.raises(SystemExit) as exc_info:
        runpy.run_path(check_android_apk_alignment.__file__, run_name="__main__")
    assert exc_info.value.code == 1
