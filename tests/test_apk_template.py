"""Guards for the embedded WebView Activity source in apk_builder.

The Java template ships as a string (ACTIVITY_JAVA) and is compiled on the
build host, far away from CI — so these tests assert the load-bearing pieces
of the source stay intact rather than executing anything.
"""

import re
import struct

import pytest

from server.engine.apk_builder import ACTIVITY_JAVA, MANIFEST_XML, ApkBuilder


def test_activity_java_braces_balanced():
    # Catches truncated / badly merged template edits before they reach the
    # build host and fail there with a cryptic javac error.
    assert ACTIVITY_JAVA.count("{") == ACTIVITY_JAVA.count("}")


def test_file_chooser_is_wired_end_to_end():
    # Issue #16: <input type="file"> did nothing because AppChromeClient never
    # overrode onShowFileChooser (WebView has no default picker).
    assert "@Override public boolean onShowFileChooser(" in ACTIVITY_JAVA
    assert "startActivityForResult(intent, REQ_FILE_CHOOSER)" in ACTIVITY_JAVA
    assert "protected void onActivityResult" in ACTIVITY_JAVA
    assert "if (requestCode != REQ_FILE_CHOOSER) return;" in ACTIVITY_JAVA
    assert "callback.onReceiveValue(parseFileChooserResult(resultCode, data))" in ACTIVITY_JAVA
    assert "private Uri[] parseFileChooserResult(int resultCode, Intent data)" in ACTIVITY_JAVA


def test_file_chooser_callback_always_settled():
    # A callback that is never answered makes WebView silently drop every
    # later <input type="file"> tap, so both the stale-chooser path and the
    # cancel path must deliver null.
    assert ACTIVITY_JAVA.count("pendingFileChoiceCallback.onReceiveValue(null)") == 1
    assert "callback.onReceiveValue(parseFileChooserResult(resultCode, data))" in ACTIVITY_JAVA


def test_file_chooser_imports_present():
    assert "import android.content.ClipData;" in ACTIVITY_JAVA
    assert "import android.webkit.ValueCallback;" in ACTIVITY_JAVA


def test_template_revision_is_bumped_slug():
    # Any change to ACTIVITY_JAVA must come with a new TEMPLATE_REVISION or
    # build hosts keep serving the cached (stale) template APK.
    revision = ApkBuilder.TEMPLATE_REVISION
    parts = revision.split("-")
    assert len(parts) >= 4
    assert all(part.isdigit() for part in parts[:3])  # YYYY-MM-DD prefix
    assert parts[3]  # feature slug


def test_manifest_targets_current_sdk():
    # Issue #32: targetSdk 33 read as stale tool output and got APKs flagged.
    # Android requires targetSdk >= 34 for store updates; keep the generated
    # APK pinned to the current platform level (36).
    assert 'android:targetSdkVersion="36"' in MANIFEST_XML


def test_immersive_mode_handles_edge_to_edge_enforcement():
    # targetSdk 35+ enforces edge-to-edge and ignores the legacy
    # setSystemUiVisibility immersive flags, so API 35+ must go through
    # WindowInsetsController with inset padding on the WebView.
    assert "Build.VERSION_CODES.BAKLAVA" in ACTIVITY_JAVA
    assert "setOnApplyWindowInsetsListener" in ACTIVITY_JAVA
    assert "WindowInsets.CONSUMED" in ACTIVITY_JAVA


# ===== In-page file export bridge (issue #37) =====
#
# window.android.downloadFile does not exist in our APK, and DownloadManager
# cannot fetch blob:/data: URLs, so page-side exports failed silently. The
# template now exposes window.WebToApp.saveFile and resolves blob:/data:
# downloads natively. Like the file-chooser guards above, these assert the
# load-bearing source pieces stay intact (the template compiles far away).


def test_export_bridge_is_registered():
    assert 'addJavascriptInterface(new WebAppBridge(), "WebToApp")' in ACTIVITY_JAVA
    assert "import android.webkit.JavascriptInterface;" in ACTIVITY_JAVA
    assert "@JavascriptInterface public void saveFile(" in ACTIVITY_JAVA
    assert "@JavascriptInterface public void onExportFailed(" in ACTIVITY_JAVA


def test_export_bridge_writes_to_public_downloads():
    # Q+: MediaStore public collection (visible in file managers, no
    # permission needed). Pre-Q: public dir + media scan broadcast.
    assert "MediaStore.Downloads.EXTERNAL_CONTENT_URI" in ACTIVITY_JAVA
    assert "MediaStore.Downloads.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS" in ACTIVITY_JAVA
    assert "getExternalStoragePublicDirectory(" in ACTIVITY_JAVA
    assert "ACTION_MEDIA_SCANNER_SCAN_FILE" in ACTIVITY_JAVA
    assert "import android.provider.MediaStore;" in ACTIVITY_JAVA


def test_blob_and_data_downloads_resolved_natively():
    assert 'lower.startsWith("blob:")' in ACTIVITY_JAVA
    assert 'lower.startsWith("data:")' in ACTIVITY_JAVA
    assert "resolveBlobDownload(url, name, mime)" in ACTIVITY_JAVA
    assert "evaluateJavascript(script, null)" in ACTIVITY_JAVA
    # The fetch snippet must stay double-quote-free so neither the Java nor
    # the Python template layer needs escaping. Compare literal *contents*
    # (delimiters excluded) — the Java "..." delimiters themselves obviously
    # contain quotes.
    block = ACTIVITY_JAVA.split("BLOB_FETCH_PREFIX =", 1)[1].split(
        "private void resolveBlobDownload", 1)[0]
    js = "".join(re.findall(r'"((?:[^"\\]|\\.)*)"', block))
    assert '"' not in js
    assert "fetch(u)" in js and "WebToApp.saveFile" in js


def test_download_failures_are_visible():
    # Issue #37's core pain was silent failure: every catch swallowed the
    # error. Failures must now surface via logcat and an on-screen Toast.
    assert "enqueueDownload failed" in ACTIVITY_JAVA
    assert "Toast.makeText(M.this, message, Toast.LENGTH_LONG).show()" in ACTIVITY_JAVA
    assert "import android.widget.Toast;" in ACTIVITY_JAVA
    assert "import android.util.Log;" in ACTIVITY_JAVA


def test_notification_permission_nudged_not_blocking():
    assert '<uses-permission android:name="android.permission.POST_NOTIFICATIONS"/>' in MANIFEST_XML
    assert "REQ_NOTIFY" in ACTIVITY_JAVA
    assert '"android.permission.POST_NOTIFICATIONS"' in ACTIVITY_JAVA


# ===== Forkless per-app patching (issue #34) =====
#
# The per-app APK path must not run apktool; it rewrites ZIP entries of the
# cached template directly. The AXML patcher is exercised against a fixture
# manifest compiled by aapt2 (not the build host) so CI never needs an SDK.

def _u16pool(s: str) -> bytes:
    # One pool entry: u16 length prefix + UTF-16 data + NUL terminator.
    return struct.pack("<H", len(s)) + s.encode("utf-16-le") + b"\x00\x00"


_AXML_FIXTURE = (
    b"\x03\x00\x0c\x00\x8c\x0b\x00\x00"  # RES_XML doc header: type 3, size 3004
    b"\x01\x00\x1c\x00\x84\x04\x00\x00"  # string pool: type 1, header 28
    + struct.pack("<IIIII", 6, 0, 0, 52, 0)  # stringsStart: 28 header + 6*4 offsets
    + struct.pack("<6I", 0, 46, 84, 110, 136, 146)
    + _u16pool("com.webtoapp.template")
    + _u16pool("WebToApp Template")
    + _u16pool("versionCode")
    + _u16pool("versionName")
    + _u16pool("1.0")
    + _u16pool("2.0")
    + b"\x00" * 2  # pool padding to 4-byte boundary
    # START_ELEMENT for <manifest>: type 0x0102, header 16, size 96;
    # attrExt: ns, name, attrStart=20, attrSize=20, attrCount=4, next=0, ...
    + b"\x02\x01\x10\x00\x60\x00\x00\x00"
    + b"\x00\x00\x00\x00\x00\x00\x00\x00"  # line number + comment
    + b"\xff\xff\xff\xff"  # ns = -1
    + b"\x01\x00\x00\x00"  # element name index
    + b"\x14\x00\x14\x00\x04\x00\x00\x00\x00\x00\x00\x00"  # attrExt tail
    # attribute records: ns, name_idx, raw_idx, typed_value, value
    + b"\xff\xff\xff\xff" + struct.pack("<I", 2) + b"\xff\xff\xff\xff"
    + struct.pack("<II", 0x10000008, 1)  # versionCode = 1 (INT_DEC)
    + b"\xff\xff\xff\xff" + struct.pack("<I", 3) + struct.pack("<I", 4)
    + struct.pack("<II", 0x03000008, 4)  # versionName = "1.0" (STRING)
    + b"\xff\xff\xff\xff" + struct.pack("<I", 0) + b"\xff\xff\xff\xff"
    + struct.pack("<II", 0x03000008, 0)  # package = "com.webtoapp.template"
    + b"\xff\xff\xff\xff" + struct.pack("<I", 1) + b"\xff\xff\xff\xff"
    + struct.pack("<II", 0x03000008, 1)  # label = "WebToApp Template"
)


def test_axml_patcher_swaps_pool_strings_and_version_code():
    from server.engine.apk_builder import _AxmlPatcher

    patched = _AxmlPatcher(_AXML_FIXTURE).patch(
        {"com.webtoapp.template": "com.webtoapp.ae877d6c2", "WebToApp Template": "Sdk36Verify"},
        version_code=42,
    )
    strings = _AxmlPatcher(patched)._string_pool(patched)
    assert strings[0] == "com.webtoapp.ae877d6c2"
    assert strings[1] == "Sdk36Verify"
    # untouched entries keep their pool slots
    assert strings[4] == "1.0" and strings[5] == "2.0"


def test_axml_patcher_rejects_utf8_pool():
    from server.engine.apk_builder import _AxmlPatcher

    utf8_flagged = bytearray(_AXML_FIXTURE)
    # Pool header: type(2) headerSize(2) size(4) count(4) styleCount(4) flags(4)
    # → the flags field sits at absolute offset 8+16=24; aapt2 marks UTF-8
    # pools with 1<<8 in that 32-bit little-endian field.
    struct.pack_into("<I", utf8_flagged, 24, struct.unpack_from("<I", utf8_flagged, 24)[0] | 0x100)
    with pytest.raises(ValueError):
        _AxmlPatcher(bytes(utf8_flagged)).patch({"com.webtoapp.template": "com.webtoapp.ae877d6c2"}, version_code=2)
