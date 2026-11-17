import base64
import hashlib
import struct
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from server.engine import apk_v2_signer as apk_signer
from server.engine import mobileconfig_signer as mobile_signer


def _make_apk(path, include_directory=True):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        if include_directory:
            archive.writestr("assets/", b"")
        archive.writestr("classes.dex", b"dex-data")
        archive.writestr("assets/value.txt", b"value")


def test_mobile_can_sign_covers_configuration_and_openssl(monkeypatch):
    which = Mock(side_effect=AssertionError("which must be short-circuited"))
    monkeypatch.setattr(mobile_signer.config, "ios_signing_available", lambda: False)
    monkeypatch.setattr(mobile_signer.shutil, "which", which)
    assert mobile_signer.can_sign() is False
    which.assert_not_called()

    monkeypatch.setattr(mobile_signer.config, "ios_signing_available", lambda: True)
    which.side_effect = None
    which.return_value = None
    assert mobile_signer.can_sign() is False
    which.return_value = "/usr/bin/openssl"
    assert mobile_signer.can_sign() is True


@pytest.mark.parametrize("chain", [None, "chain.pem"])
def test_mobile_sign_success_with_optional_chain(monkeypatch, chain):
    monkeypatch.setattr(mobile_signer.config, "ios_cert_file", lambda: "cert.pem")
    monkeypatch.setattr(mobile_signer.config, "ios_key_file", lambda: "key.pem")
    monkeypatch.setattr(mobile_signer.config, "ios_chain_file", lambda: chain)
    monkeypatch.setattr(mobile_signer.shutil, "which", lambda name: "/mock/openssl")
    commands = []

    def fake_run(cmd, capture_output, timeout=None):
        assert capture_output is True
        commands.append(cmd)
        in_path = Path(cmd[cmd.index("-in") + 1])
        out_path = Path(cmd[cmd.index("-out") + 1])
        assert in_path.read_bytes() == b"<plist/>"
        out_path.write_bytes(b"signed-der")
        return SimpleNamespace(returncode=0, stderr=b"")

    monkeypatch.setattr(mobile_signer.subprocess, "run", fake_run)
    assert mobile_signer.sign(b"<plist/>") == b"signed-der"
    cmd = commands[0]
    assert cmd[:3] == ["/mock/openssl", "cms", "-sign"]
    assert ("-certfile" in cmd) is bool(chain)
    if chain:
        assert cmd[cmd.index("-certfile") + 1] == chain


@pytest.mark.parametrize(
    "cert,key,openssl",
    [
        (None, "key.pem", "/mock/openssl"),
        ("cert.pem", None, "/mock/openssl"),
        ("cert.pem", "key.pem", None),
    ],
)
def test_mobile_sign_reports_missing_prerequisites(monkeypatch, cert, key, openssl):
    monkeypatch.setattr(mobile_signer.config, "ios_cert_file", lambda: cert)
    monkeypatch.setattr(mobile_signer.config, "ios_key_file", lambda: key)
    monkeypatch.setattr(mobile_signer.config, "ios_chain_file", lambda: None)
    monkeypatch.setattr(mobile_signer.shutil, "which", lambda name: openssl)
    run = Mock(side_effect=AssertionError("subprocess must not run"))
    monkeypatch.setattr(mobile_signer.subprocess, "run", run)

    with pytest.raises(mobile_signer.SigningUnavailable, match="openssl/cert/key missing"):
        mobile_signer.sign(b"xml")
    run.assert_not_called()


def test_mobile_sign_wraps_openssl_failure(monkeypatch):
    monkeypatch.setattr(mobile_signer.config, "ios_cert_file", lambda: "cert.pem")
    monkeypatch.setattr(mobile_signer.config, "ios_key_file", lambda: "key.pem")
    monkeypatch.setattr(mobile_signer.config, "ios_chain_file", lambda: None)
    monkeypatch.setattr(mobile_signer.shutil, "which", lambda name: "/mock/openssl")
    monkeypatch.setattr(
        mobile_signer.subprocess,
        "run",
        Mock(return_value=SimpleNamespace(returncode=9, stderr=b"bad certificate\xff\n")),
    )

    with pytest.raises(mobile_signer.SigningUnavailable, match=r"exit=9.*bad certificate"):
        mobile_signer.sign(b"xml")


def test_mobile_sign_or_passthrough_all_paths(monkeypatch, capsys):
    sign = Mock(side_effect=AssertionError("sign must not be called"))
    monkeypatch.setattr(mobile_signer, "can_sign", lambda: False)
    monkeypatch.setattr(mobile_signer, "sign", sign)
    assert mobile_signer.sign_or_passthrough(b"xml") == (b"xml", False)
    sign.assert_not_called()

    monkeypatch.setattr(mobile_signer, "can_sign", lambda: True)
    monkeypatch.setattr(mobile_signer, "sign", lambda value: b"signed:" + value)
    assert mobile_signer.sign_or_passthrough(b"xml") == (b"signed:xml", True)

    def fail(_value):
        raise mobile_signer.SigningUnavailable("broken")

    monkeypatch.setattr(mobile_signer, "sign", fail)
    assert mobile_signer.sign_or_passthrough(b"xml") == (b"xml", False)
    assert "[Signer] broken — falling back to unsigned" in capsys.readouterr().out


def test_v1_manifest_entry_and_successful_build(monkeypatch, tmp_path):
    assert apk_signer._sf_manifest_entry("a.txt", "abc") == (
        b"Name: a.txt\r\nSHA-256-Digest: abc\r\n\r\n"
    )
    apk = tmp_path / "app.apk"
    _make_apk(apk, include_directory=True)
    commands = []

    def fake_run(cmd, capture_output, timeout=None):
        assert capture_output is True
        commands.append(cmd)
        sf_path = Path(cmd[cmd.index("-in") + 1])
        assert b"X-Android-APK-Signed: 2,3\r\n" in sf_path.read_bytes()
        Path(cmd[cmd.index("-out") + 1]).write_bytes(b"pkcs7")
        return SimpleNamespace(returncode=0, stderr=b"")

    monkeypatch.setattr(apk_signer.subprocess, "run", fake_run)
    apk_signer.build_v1(apk, Path("key.pem"), Path("cert.pem"), "release")

    with zipfile.ZipFile(apk) as archive:
        names = archive.namelist()
        manifest = archive.read("META-INF/MANIFEST.MF")
        sf = archive.read("META-INF/RELEASE.SF")
        assert archive.read("META-INF/RELEASE.RSA") == b"pkcs7"

    assert "assets/" in names
    assert b"Built-By: Signflinger\r\n" in manifest
    assert b"Created-By: Android Gradle 8.0.2\r\n" in manifest
    assert b"Name: assets/\r\n" not in manifest
    for name, data in (("classes.dex", b"dex-data"), ("assets/value.txt", b"value")):
        digest = base64.b64encode(hashlib.sha256(data).digest())
        assert b"Name: " + name.encode() + b"\r\nSHA-256-Digest: " + digest in manifest
        section = apk_signer._sf_manifest_entry(name, digest.decode("ascii"))
        section_digest = base64.b64encode(hashlib.sha256(section).digest())
        assert b"Name: " + name.encode() + b"\r\nSHA-256-Digest: " + section_digest in sf
    assert commands[0][:4] == ["openssl", "smime", "-sign", "-binary"]


def test_v1_build_wraps_openssl_failure(monkeypatch, tmp_path):
    apk = tmp_path / "app.apk"
    _make_apk(apk, include_directory=False)
    monkeypatch.setattr(
        apk_signer.subprocess,
        "run",
        Mock(return_value=SimpleNamespace(returncode=2, stderr=b"failure\xff")),
    )

    with pytest.raises(apk_signer.V2SignError, match="openssl v1 PKCS7 failed: failure"):
        apk_signer.build_v1(apk, Path("key.pem"), Path("cert.pem"), "alias", "Creator", "Builder")


def test_chunked_digest_empty_single_and_multiple_chunks():
    assert apk_signer._chunked_digest(b"") == []
    data = b"a" * apk_signer.CHUNK_SIZE + b"b"
    digests = apk_signer._chunked_digest(data)
    assert len(digests) == 2

    def expected(chunk):
        return hashlib.sha256(b"\xa5" + struct.pack("<I", len(chunk)) + chunk).digest()

    assert digests == [expected(data[: apk_signer.CHUNK_SIZE]), expected(b"b")]


def test_find_eocd_scans_backward_and_reports_missing_signature():
    data = b"prefix" + b"PK\x05\x06" + b"\x00" * 18 + b"xyz"
    assert apk_signer._find_eocd(data) == len(b"prefix")
    with pytest.raises(apk_signer.V2SignError, match="EOCD not found"):
        apk_signer._find_eocd(b"x" * 40)


def test_length_prefix_helper():
    assert apk_signer._lp(b"abc") == b"\x03\x00\x00\x00abc"


def test_v2_sign_builds_minimal_v2_v3_block_and_patches_eocd(monkeypatch, tmp_path):
    apk = tmp_path / "app.apk"
    _make_apk(apk, include_directory=False)
    original = apk.read_bytes()
    old_eocd = apk_signer._find_eocd(original)
    old_cd = struct.unpack_from("<I", original, old_eocd + 16)[0]
    signed_inputs = []

    def fake_run(cmd, capture_output, timeout=None):
        assert capture_output is True
        data_path = Path(cmd[-1])
        signed_inputs.append(data_path.read_bytes())
        signature = b"v2-signature" if len(signed_inputs) == 1 else b"v3-signature"
        Path(cmd[cmd.index("-out") + 1]).write_bytes(signature)
        return SimpleNamespace(returncode=0, stderr=b"")

    monkeypatch.setattr(apk_signer.subprocess, "run", fake_run)
    apk_signer.sign_v2(apk, b"private-key", b"certificate", b"public-key")

    result = apk.read_bytes()
    new_eocd = apk_signer._find_eocd(result)
    new_cd = struct.unpack_from("<I", result, new_eocd + 16)[0]
    block = result[old_cd:new_cd]
    leading_size = struct.unpack_from("<Q", block, 0)[0]
    trailing_size = struct.unpack_from("<Q", block, len(block) - 24)[0]

    assert len(signed_inputs) == 2
    assert signed_inputs[0] != signed_inputs[1]
    assert new_cd > old_cd
    assert leading_size == trailing_size == len(block) - 8
    assert block[-16:] == apk_signer.APK_SIG_BLOCK_MAGIC
    assert struct.pack("<I", apk_signer.APK_SIGNATURE_SCHEME_V2_BLOCK_ID) in block
    assert struct.pack("<I", apk_signer.APK_SIGNATURE_SCHEME_V3_BLOCK_ID) in block
    assert result[new_cd:new_eocd] == original[old_cd:old_eocd]
    with zipfile.ZipFile(apk) as archive:
        assert archive.read("classes.dex") == b"dex-data"


def test_v2_sign_wraps_openssl_failure_without_modifying_apk(monkeypatch, tmp_path):
    apk = tmp_path / "app.apk"
    _make_apk(apk, include_directory=False)
    original = apk.read_bytes()
    monkeypatch.setattr(
        apk_signer.subprocess,
        "run",
        Mock(return_value=SimpleNamespace(returncode=4, stderr=b"cannot sign\xff")),
    )

    with pytest.raises(apk_signer.V2SignError, match="openssl sign failed: cannot sign"):
        apk_signer.sign_v2(apk, b"private-key", b"certificate", b"public-key")
    assert apk.read_bytes() == original
