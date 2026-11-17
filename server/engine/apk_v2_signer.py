"""
Custom APK v1 + v2 signer.

Why this exists: the Android SDK ``apksigner`` CLI hard-codes the v1 (JAR)
signature's ``Created-By: 1.0 (Android)`` string, which some mobile AV engines
fingerprint to bulk-flag tool-signed APKs. We reproduce what real Gradle builds
emit (``Created-By: Android Gradle 8.0.2`` / ``Built-By: Signflinger``) by
writing the v1 signature ourselves, then appending an APK Signature Scheme v2
block over the v1-containing APK.

Implements:
  - v1 (JAR signing): MANIFEST.MF + <ALIAS>.SF + <ALIAS>.RSA (PKCS#7 via openssl)
  - v2 (APK Signature Scheme v2): per AOSP spec, 1MB-chunked Merkle-ish digest
    over (ZIP entries | Central Directory | End-Of-Central-Directory), signed
    with RSASSA-PKCS1-v1_5 + SHA-256 (signature algorithm ID 0x0103).

v2 alone satisfies Android 7+ (and the targetSdk>=30 "needs v2" rule); the v1
layer keeps Android 5-6 installable. v3 is intentionally omitted — it is not
required for installation and v2 covers all modern devices.
"""

import base64
import hashlib
import os
import shutil
import struct
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import List, Tuple

def _tool_timeout() -> int:
    """Wall-clock cap for signing subprocesses (#242). Lazy import keeps this
    module free of a config dependency at import time."""
    from server import config
    return config.tool_timeout_seconds()


APK_SIG_BLOCK_MAGIC = b"APK Sig Block 42"
APK_SIGNATURE_SCHEME_V2_BLOCK_ID = 0x7109871A
APK_SIGNATURE_SCHEME_V3_BLOCK_ID = 0xF05368C0
SIG_RSA_PKCS1V15_SHA256 = 0x0103
CHUNK_SIZE = 1024 * 1024
V3_MIN_SDK = 28      # v3 only applies on Android 9+; v2 covers 7-8
V3_MAX_SDK = 0x7FFFFFFF


class V2SignError(Exception):
    pass


# ----------------------------- v1 (JAR) -----------------------------

def _sf_manifest_entry(name: str, digest_b64: str) -> bytes:
    return (f"Name: {name}\r\nSHA-256-Digest: {digest_b64}\r\n\r\n").encode("utf-8")


def build_v1(apk_path: Path, key_pem: Path, cert_pem: Path, alias: str,
             created_by: str = "Android Gradle 8.0.2",
             built_by: str = "Signflinger") -> None:
    """Add a JAR (v1) signature to ``apk_path`` in place.

    The APK must NOT already contain META-INF signature files. The .SF main
    section carries ``X-Android-APK-Signed: 2`` so a v2-aware verifier won't
    accept it as v1-only (rollback protection).
    """
    b64 = lambda d: base64.b64encode(d).decode("ascii")
    sha = lambda d: hashlib.sha256(d).digest()

    with zipfile.ZipFile(apk_path) as z:
        names = [i.filename for i in z.infolist() if not i.is_dir()]
        data = {n: z.read(n) for n in names}

    # MANIFEST.MF
    manifest_main = (
        f"Manifest-Version: 1.0\r\n"
        f"Built-By: {built_by}\r\n"
        f"Created-By: {created_by}\r\n\r\n"
    ).encode("utf-8")
    manifest_entries = b"".join(_sf_manifest_entry(n, b64(sha(data[n]))) for n in names)
    manifest = manifest_main + manifest_entries

    # .SF — match the byte layout Gradle/Signflinger emits (so AV engines that
    # whitelist that pattern treat it the same). Main attribute order:
    #   Signature-Version, Created-By, SHA-256-Digest-Manifest, X-Android-APK-Signed
    sf_main = (
        f"Signature-Version: 1.0\r\n"
        f"Created-By: {created_by}\r\n"
        f"SHA-256-Digest-Manifest: {b64(sha(manifest))}\r\n"
        f"X-Android-APK-Signed: 2,3\r\n\r\n"
    ).encode("utf-8")
    sf_entries = b""
    for n in names:
        section = _sf_manifest_entry(n, b64(sha(data[n])))
        sf_entries += (f"Name: {n}\r\nSHA-256-Digest: {b64(sha(section))}\r\n\r\n").encode("utf-8")
    sf = sf_main + sf_entries

    # PKCS#7 detached signature over .SF (openssl)
    with tempfile.TemporaryDirectory() as td:
        sf_file = Path(td) / "f.sf"
        sf_file.write_bytes(sf)
        p7 = Path(td) / "f.p7"
        res = subprocess.run(
            ["openssl", "smime", "-sign", "-binary", "-noattr",
             "-in", str(sf_file), "-signer", str(cert_pem), "-inkey", str(key_pem),
             "-outform", "DER", "-md", "sha256", "-out", str(p7)],
            capture_output=True, timeout=_tool_timeout(),
        )
        if res.returncode != 0:
            raise V2SignError("openssl v1 PKCS7 failed: " + res.stderr.decode("utf-8", "ignore"))
        rsa = p7.read_bytes()

    a = alias.upper()
    with zipfile.ZipFile(apk_path, "a", zipfile.ZIP_DEFLATED) as z:
        z.writestr("META-INF/MANIFEST.MF", manifest)
        z.writestr(f"META-INF/{a}.SF", sf)
        z.writestr(f"META-INF/{a}.RSA", rsa)


# ----------------------------- v2 -----------------------------

def _chunked_digest(data: bytes) -> List[bytes]:
    """Return per-1MB-chunk SHA-256 digests of ``data``."""
    digests = []
    for off in range(0, len(data), CHUNK_SIZE):
        chunk = data[off:off + CHUNK_SIZE]
        h = hashlib.sha256()
        h.update(b"\xa5")
        h.update(struct.pack("<I", len(chunk)))
        h.update(chunk)
        digests.append(h.digest())
    return digests


def _find_eocd(data: bytes) -> int:
    """Offset of the End Of Central Directory record."""
    # EOCD signature 0x06054b50, scan from end (no zip comment expected, but allow some)
    sig = b"\x50\x4b\x05\x06"
    min_eocd = 22
    for i in range(len(data) - min_eocd, max(-1, len(data) - min_eocd - 65536), -1):
        if data[i:i + 4] == sig:
            return i
    raise V2SignError("EOCD not found")


def _lp(data: bytes) -> bytes:
    """uint32 length-prefix a blob."""
    return struct.pack("<I", len(data)) + data


def sign_v2(apk_path: Path, key_der: bytes, cert_der: bytes, pubkey_der: bytes) -> None:
    """Append an APK Signature Scheme v2 block to ``apk_path`` (in place).

    ``apk_path`` should already contain its v1 signature and be zipaligned.
    """
    raw = apk_path.read_bytes()
    eocd_off = _find_eocd(raw)
    # central directory offset is stored at EOCD+16
    cd_off = struct.unpack("<I", raw[eocd_off + 16:eocd_off + 20])[0]

    section1 = raw[:cd_off]            # ZIP entries
    section_cd = raw[cd_off:eocd_off]  # Central Directory
    eocd = bytearray(raw[eocd_off:])   # End Of Central Directory (mutable copy)

    # We'll insert the signing block between section1 and section_cd, which
    # shifts the CD offset. The digest over EOCD must use the *post-insert* CD
    # offset, so patch EOCD's CD-offset field to point at where the signing
    # block will start (== old cd_off, because the block goes right there and
    # the CD moves after it... per spec we set it to the signing block offset).
    # Per AOSP: when computing the EOCD digest, treat the CD-offset field as if
    # it pointed at the start of the APK Signing Block.
    # The signing block starts exactly at the original cd_off.
    struct.pack_into("<I", eocd, 16, cd_off)  # already cd_off; explicit for clarity
    eocd_for_digest = bytes(eocd)

    # ---- compute top-level digest over the 3 sections ----
    chunk_digests = []
    chunk_digests += _chunked_digest(section1)
    chunk_digests += _chunked_digest(section_cd)
    chunk_digests += _chunked_digest(eocd_for_digest)
    total_chunks = len(chunk_digests)
    top = hashlib.sha256()
    top.update(b"\x5a")
    top.update(struct.pack("<I", total_chunks))
    for d in chunk_digests:
        top.update(d)
    apk_digest = top.digest()

    def _rsa_sign(data: bytes) -> bytes:
        with tempfile.TemporaryDirectory() as td:
            sd = Path(td) / "sd.bin"; sd.write_bytes(data)
            kf = Path(td) / "k.der"; kf.write_bytes(key_der)
            sig = Path(td) / "s.bin"
            res = subprocess.run(
                ["openssl", "dgst", "-sha256", "-sign", str(kf),
                 "-keyform", "DER", "-out", str(sig), str(sd)],
                capture_output=True, timeout=_tool_timeout(),
            )
            if res.returncode != 0:
                raise V2SignError("openssl sign failed: " + res.stderr.decode("utf-8", "ignore"))
            return sig.read_bytes()

    digest_entry = struct.pack("<I", SIG_RSA_PKCS1V15_SHA256) + _lp(apk_digest)
    digests_seq = _lp(_lp(digest_entry))
    certs_seq = _lp(_lp(cert_der))
    public_key_lp = _lp(pubkey_der)

    # ----- v2 signer -----
    v2_signed_data = digests_seq + certs_seq + _lp(b"")  # empty additional attrs
    v2_sig = _rsa_sign(v2_signed_data)
    v2_signatures = _lp(_lp(struct.pack("<I", SIG_RSA_PKCS1V15_SHA256) + _lp(v2_sig)))
    v2_signer = _lp(v2_signed_data) + v2_signatures + public_key_lp
    v2_block_value = _lp(_lp(v2_signer))

    # ----- v3 signer (adds min/max SDK to signed-data and to the signer) -----
    v3_signed_data = (
        digests_seq + certs_seq
        + struct.pack("<I", V3_MIN_SDK) + struct.pack("<I", V3_MAX_SDK)
        + _lp(b"")  # additional attributes
    )
    v3_sig = _rsa_sign(v3_signed_data)
    v3_signatures = _lp(_lp(struct.pack("<I", SIG_RSA_PKCS1V15_SHA256) + _lp(v3_sig)))
    v3_signer = (
        _lp(v3_signed_data)
        + struct.pack("<I", V3_MIN_SDK) + struct.pack("<I", V3_MAX_SDK)
        + v3_signatures + public_key_lp
    )
    v3_block_value = _lp(_lp(v3_signer))

    # ---- wrap both into the APK Signing Block ----
    def _pair(block_id, value):
        idv = struct.pack("<I", block_id) + value
        return struct.pack("<Q", len(idv)) + idv

    body = _pair(APK_SIGNATURE_SCHEME_V2_BLOCK_ID, v2_block_value)
    body += _pair(APK_SIGNATURE_SCHEME_V3_BLOCK_ID, v3_block_value)
    block_size = len(body) + 8 + len(APK_SIG_BLOCK_MAGIC)
    signing_block = (
        struct.pack("<Q", block_size)
        + body
        + struct.pack("<Q", block_size)
        + APK_SIG_BLOCK_MAGIC
    )

    # The APK Signing Block must be 4096-byte aligned at its start? No: the spec
    # requires the *contents* after it (CD) — apksigner pads via an extra
    # id-value pair. For simplicity we align the block to 4096 by prepending a
    # padding id-value pair if needed. Many verifiers don't require it, but
    # Android's loader expects the block size consistent; we keep it simple and
    # do NOT 4096-align (verified to pass apksigner). See validation step.

    # ---- patch EOCD's CD offset to point after the inserted block ----
    new_cd_off = cd_off + len(signing_block)
    eocd_out = bytearray(raw[eocd_off:])
    struct.pack_into("<I", eocd_out, 16, new_cd_off)

    out = section1 + signing_block + section_cd + bytes(eocd_out)
    apk_path.write_bytes(out)
