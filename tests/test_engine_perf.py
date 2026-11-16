"""Engine build-path optimizations (issue #226): icon early-exit, R2 upload
retry/partial results, signing-material cache."""

import threading
import time
from pathlib import Path
from unittest.mock import Mock

import pytest

from server.engine import storage
from server.engine.apk_builder import ApkBuilder
from server.engine.distiller import Distiller


def _png_bytes(dim: int) -> bytes:
    # _png_dimension only reads the IHDR width at bytes 16:20.
    return b"\x89PNG" + b"\x00" * 12 + dim.to_bytes(4, "big") + b"\x00" * 32


def test_icon_sweep_stops_at_perfect_icon(monkeypatch):
    distiller = Distiller()
    perfect = _png_bytes(512)
    slow_started = threading.Event()

    def fake_fetch(url, timeout=None):
        if url == "https://site.test/touch.png":
            return b"perfect-raw"
        slow_started.set()
        time.sleep(2.0)  # a slow third-party service we must NOT wait for
        return b"slow-raw"

    monkeypatch.setattr(distiller, "_fetch_url_bytes", fake_fetch)
    monkeypatch.setattr(distiller, "_normalize_to_png",
                        lambda data: perfect if data == b"perfect-raw" else _png_bytes(96))
    monkeypatch.setattr("server.engine.distiller.is_unusable_icon", lambda png: False)

    started = time.monotonic()
    best, saw_solid = distiller._choose_best_icon(
        ["https://site.test/touch.png", "https://slow.test/icon.png"]
    )
    elapsed = time.monotonic() - started
    assert best == perfect
    assert saw_solid is False
    # Early exit must not wait for the 2s tail (allow generous scheduling slack).
    assert elapsed < 1.5


def test_icon_sweep_keeps_best_when_no_perfect(monkeypatch):
    distiller = Distiller()
    small, medium = _png_bytes(96), _png_bytes(256)
    monkeypatch.setattr(distiller, "_fetch_url_bytes", lambda url, timeout=None: url.encode())
    monkeypatch.setattr(distiller, "_normalize_to_png",
                        lambda data: medium if b"medium" in data else small)
    monkeypatch.setattr("server.engine.distiller.is_unusable_icon", lambda png: False)
    best, _ = distiller._choose_best_icon(["https://a.test/small", "https://b.test/medium"])
    assert best == medium


def test_r2_upload_retries_then_keeps_partial_results(monkeypatch, tmp_path):
    client = storage.R2Storage()
    monkeypatch.setattr(storage.config, "r2_configured", lambda: True)
    monkeypatch.setattr(storage.time, "sleep", lambda *_: None)
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    (downloads / "a.apk").write_bytes(b"a")
    (downloads / "b.zip").write_bytes(b"b")

    calls = []

    def flaky_upload(path, key, content_type=None):
        calls.append(key)
        if path.name == "b.zip" and calls.count(key) == 1:
            raise RuntimeError("transient 503")
        return f"https://cdn/{path.name}"

    monkeypatch.setattr(client, "upload_file", flaky_upload)
    urls = client.upload_app_downloads("app1", downloads)
    assert urls == {"a.apk": "https://cdn/a.apk", "b.zip": "https://cdn/b.zip"}
    assert calls.count("app1/downloads/b.zip") == 2  # retried once


def test_r2_upload_persistent_failure_keeps_siblings(monkeypatch, tmp_path):
    client = storage.R2Storage()
    monkeypatch.setattr(storage.config, "r2_configured", lambda: True)
    monkeypatch.setattr(storage.time, "sleep", lambda *_: None)
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    (downloads / "a.apk").write_bytes(b"a")
    (downloads / "b.zip").write_bytes(b"b")

    def half_broken(path, key, content_type=None):
        if path.name == "b.zip":
            raise RuntimeError("permanent failure")
        return f"https://cdn/{path.name}"

    monkeypatch.setattr(client, "upload_file", half_broken)
    urls = client.upload_app_downloads("app1", downloads)
    # The old serial loop aborted the batch and returned {} — losing a.apk's URL.
    assert urls == {"a.apk": "https://cdn/a.apk"}


def test_signing_material_cache_skips_openssl_on_rebuild(monkeypatch, tmp_path):
    builder = ApkBuilder.__new__(ApkBuilder)  # no SDK probing needed
    keystore = tmp_path / "app.keystore"
    keystore.write_bytes(b"fake-p12")
    runs = []

    def fake_run(cmd, *args, **kwargs):
        runs.append(cmd)
        out_idx = cmd.index("-out") + 1 if "-out" in cmd else None
        if out_idx is not None:
            Path(cmd[out_idx]).write_bytes(b"DER-OR-PEM")
        return Mock(returncode=0, stdout=b"PUBKEY-PEM")

    monkeypatch.setattr("server.engine.apk_builder.subprocess.run", fake_run)
    with builder._signing_material_lock:
        builder._signing_material_cache.clear()

    tmp1 = tmp_path / "t1"
    tmp1.mkdir()
    first = builder._export_signing_material(keystore, "pw", "alias", tmp1)
    openssl_calls = len(runs)
    assert openssl_calls >= 6

    tmp2 = tmp_path / "t2"
    tmp2.mkdir()
    second = builder._export_signing_material(keystore, "pw", "alias", tmp2)
    assert len(runs) == openssl_calls  # zero new subprocesses on the rebuild
    assert second[2:] == first[2:]  # DER bytes identical
    assert second[0].read_bytes() == first[0].read_bytes()
    assert second[0].parent == tmp2  # PEMs re-materialized into the caller's tmp

    # Rotating the keystore invalidates the cache entry.
    keystore.write_bytes(b"rotated-p12-material")
    tmp3 = tmp_path / "t3"
    tmp3.mkdir()
    builder._export_signing_material(keystore, "pw", "alias", tmp3)
    assert len(runs) > openssl_calls