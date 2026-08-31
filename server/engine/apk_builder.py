"""
Android APK Builder.

Primary strategy:
1. Reuse a cached template WebView APK.
2. Patch package name / app name / version / icon / assets URL by rewriting
   the affected ZIP entries in place (AXML string-pool edit for the
   manifest) — no apktool round-trip in the per-app path.
3. Re-align and sign with a per-app keystore (one signing certificate per
   app_id; generated on first build and reused on every later build of the
   same app_id so reinstalls are accepted as updates).

Fallback strategy:
1. Build the minimal WebView shell from source if SDK tools are available.
2. Cache the result as the template APK.
3. If all else fails, emit the legacy ZIP fallback package.
"""

import json
import os
import re
import secrets
import shutil
import struct
import subprocess
import tempfile
import zipfile
import zlib
from pathlib import Path

from server import config
from server.engine import apk_v2_signer


class _AxmlPatcher:
    """Minimal binary (compiled) Android XML editor.

    The template manifest is compiled by our own aapt2 build, so patching per
    app is a bounded edit of two AXML structures instead of an apktool
    decode/re-encode round-trip:

    1. The global UTF-16 string pool: strings are replaced **by content** and
       the pool is re-serialized with the same entry order and count. Element
       chunks reference strings by *index*, not offset, so as long as the
       order is unchanged every other chunk stays valid — only the byte
       offsets after the pool shift, and those are carried by chunk headers
       which we rewrite.
    2. ``android:versionCode`` attribute: the manifest element carries the
       value as a raw little-endian int32 in its attribute payload; rewrite
       it in place (offsets re-derived from the rebuilt stream).
    """

    _RES_XML_TYPE = 0x0003  # RES_XML doc header
    _STRING_POOL_TYPE = 0x0001
    _START_ELEMENT_TYPE = 0x0102
    _UTF8_FLAG = 1 << 8

    def __init__(self, axml: bytes):
        self._axml = axml

    def patch(self, string_swaps: dict, version_code: int) -> bytes:
        strings = self._string_pool(self._axml)
        rebuilt = [
            string_swaps.get(s, s) for s in strings
        ]
        if rebuilt == strings and version_code == 1:
            return self._axml
        data = self._rebuild_pool(self._axml, rebuilt)
        return self._patch_version_code(data, version_code)

    def _rebuild_pool(self, data: bytes, strings: list) -> bytes:
        """Re-serialize the string pool with new contents, same order/count.

        Everything after the pool shifts by the size delta; the pool chunk
        header and the wrapping RES_XML doc header are rewritten accordingly.
        Subsequent chunk contents never carry absolute offsets to the pool
        (references are indices), so a plain shift is safe.
        """
        pos = self._first_chunk_end(data)
        chunk_type, header_size, chunk_size = struct.unpack_from("<HHI", data, pos)
        if chunk_type != self._STRING_POOL_TYPE:
            raise ValueError("AXML: string pool chunk not found")
        string_count, style_count, flags, strings_start, styles_start = struct.unpack_from(
            "<IIIII", data, pos + 8
        )
        if flags & self._UTF8_FLAG:
            raise ValueError("AXML: UTF-8 string pools not supported")
        if style_count or styles_start:
            raise ValueError("AXML: styled strings not supported")

        header = bytearray(data[pos:pos + header_size])
        body = bytearray()
        offsets = []
        for s in strings:
            encoded = s.encode("utf-16-le")
            offsets.append(len(body))
            u16len = len(s)
            if u16len >= 0x8000:
                body += struct.pack("<HH", (u16len >> 16) | 0x8000, u16len & 0xFFFF)
            else:
                body += struct.pack("<H", u16len)
            body += encoded
            body += b"\x00\x00"  # NUL terminator
        # 4-byte align the strings block
        while len(body) % 4:
            body += b"\x00"

        strings_start_new = header_size + string_count * 4
        struct.pack_into("<I", header, 20, strings_start_new)  # stringsStart @ +20
        new_pool = bytes(header) + struct.pack(f"<{string_count}I", *offsets) + bytes(body)

        out = bytearray(data[:pos] + new_pool + data[pos + chunk_size:])
        # Fix sizes: pool chunk header (offset 4) and the outer doc header (offset 4).
        struct.pack_into("<I", out, pos + 4, len(new_pool))
        doc_type, _hs, doc_size = struct.unpack_from("<HHI", out, 0)
        if doc_type == self._RES_XML_TYPE:
            struct.pack_into("<I", out, 4, doc_size + (len(new_pool) - chunk_size))
        return bytes(out)

    def _patch_version_code(self, data: bytes, version_code: int) -> bytes:
        """Rewrite the manifest element's android:versionCode int attribute.

        Walks the AXML chunk stream to find the first START_ELEMENT (the
        ``<manifest>`` element) and patches the attribute whose name resolves
        to ``versionCode`` in the string pool.
        """
        data = bytearray(data)
        strings = self._string_pool(data)
        idx = strings.index("versionCode") if "versionCode" in strings else -1
        if idx < 0:
            return data
        pos = self._first_chunk_end(data)  # skip the document header chunk
        while pos + 8 <= len(data):
            chunk_type, _header_size, chunk_size = struct.unpack_from("<HHI", data, pos)
            if chunk_type != self._START_ELEMENT_TYPE:
                pos += chunk_size
                continue
            # START_ELEMENT: 16-byte header (type/size/line/comment), then the
            # 20-byte attrExt block (ns, name, attrStart, attrSize, attrCount),
            # then attribute records. attrStart is relative to attrExt.
            attr_count = struct.unpack_from("<H", data, pos + 28)[0]
            attr_start_rel = struct.unpack_from("<H", data, pos + 24)[0]
            attr_base = pos + 16 + attr_start_rel
            for i in range(attr_count):
                base = attr_base + i * 20
                _ns, name_idx, _raw_idx, typed_value, _value = struct.unpack_from("<IIIII", data, base)
                if name_idx == idx and (typed_value >> 24) == 0x10:  # INT_DEC
                    struct.pack_into("<I", data, base + 16, version_code & 0xFFFFFFFF)
                    return data
            break
        return data

    def _first_chunk_end(self, data: bytes) -> int:
        # The outer chunk is the XML document header (type 0x0003) spanning
        # the whole file; the real chunk stream (string pool, elements) starts
        # right after its 8-byte header.
        if len(data) < 8:
            return len(data)
        chunk_type, _hs, _size = struct.unpack_from("<HHI", data, 0)
        if chunk_type != self._RES_XML_TYPE:
            return 0
        return 8

    def _string_pool(self, data: bytes) -> list:
        """Parse the global UTF-16 string pool (type 0x0001) into Python strs."""
        pos = self._first_chunk_end(data)
        if pos + 8 > len(data):
            return []
        chunk_type, _hs, size = struct.unpack_from("<HHI", data, pos)
        if chunk_type != 0x0001:
            return []
        (string_count, _style_count, _flags, strings_start, _styles_start) = struct.unpack_from(
            "<IIIII", data, pos + 8
        )
        base = pos + strings_start
        offsets = struct.unpack_from(f"<{string_count}I", data, pos + 28)
        out = []
        for off in offsets:
            start = base + off
            if start + 2 > len(data):
                break
            (u16len,) = struct.unpack_from("<H", data, start)
            if u16len & 0x8000:  # high bit = length spans two units
                u16len = ((u16len & 0x7FFF) << 16) | struct.unpack_from("<H", data, start + 2)[0]
                text_start = start + 4
            else:
                text_start = start + 2
            raw = data[text_start:text_start + u16len * 2]
            out.append(raw.decode("utf-16-le", errors="replace"))
        return out


ACTIVITY_JAVA = r"""
package w;
import android.Manifest;
import android.app.Activity;
import android.app.DownloadManager;
import android.content.ClipData;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.view.View;
import android.view.WindowInsets;
import android.view.WindowInsetsController;
import android.webkit.CookieManager;
import android.webkit.DownloadListener;
import android.webkit.GeolocationPermissions;
import android.webkit.PermissionRequest;
import android.webkit.URLUtil;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;
import org.json.JSONArray;
import org.json.JSONObject;
public class M extends Activity {
    private static final int REQ_WRITE_STORAGE = 2001;
    private static final int REQ_LOCATION = 2002;
    private static final int REQ_MEDIA = 2003;
    private static final int REQ_FILE_CHOOSER = 2004;
    private static final String DESKTOP_USER_AGENT =
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        + "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36";

    // Core ad/tracker network blocklist. Stored as a HashSet for O(1) lookups.
    // Subdomain matching is handled in isAdHost() — adding "doubleclick.net"
    // automatically blocks "securepubads.g.doubleclick.net" etc.
    private static final Set<String> AD_HOSTS = new HashSet<>(Arrays.asList(
        "doubleclick.net",
        "googlesyndication.com",
        "adservice.google.com",
        "amazon-adsystem.com",
        "ads.yahoo.com",
        "googletagmanager.com",
        "googletagservices.com",
        "adnxs.com",
        "adsystem.amazon.com",
        "pagead2.googlesyndication.com",
        "tpc.googlesyndication.com",
        "securepubads.g.doubleclick.net",
        "pubads.g.doubleclick.net",
        "ads.rubiconproject.com",
        "pixel.rubiconproject.com",
        "ib.adnxs.com",
        "cdn.taboola.com",
        "trc.taboola.com",
        "cdn.outbrain.com",
        "widgets.outbrain.com",
        "popads.net",
        "popcash.net",
        "juicyads.com",
        "exoclick.com",
        "trafficjunky.net",
        "adsterra.com",
        "hilltopads.net",
        "propellerads.com",
        "adcash.com",
        "revcontent.com",
        "mgid.com",
        "trafficfactory.biz"
    ));

    private WebView webView;
    private AppConfig config;
    private PendingDownload pendingDownload;
    private GeolocationPermissions.Callback pendingGeolocationCallback;
    private String pendingGeolocationOrigin;
    private PermissionRequest pendingPermissionRequest;
    private ValueCallback<Uri[]> pendingFileChoiceCallback;

    /**
     * Returns true if the given host matches any blocked ad/tracker domain.
     * Checks direct match first (O(1)), then walks up the subdomain chain so
     * that e.g. "sub.doubleclick.net" is caught by the "doubleclick.net" entry.
     * Also checks any extra hosts supplied at runtime via webtoapp_config.json.
     */
    private boolean isAdHost(String host) {
        if (host == null || host.isEmpty()) return false;
        String lower = host.toLowerCase(Locale.US);
        if (AD_HOSTS.contains(lower)) return true;
        int dot = lower.indexOf('.');
        while (dot != -1) {
            String parent = lower.substring(dot + 1);
            if (AD_HOSTS.contains(parent)) return true;
            dot = lower.indexOf('.', dot + 1);
        }
        // Check server-supplied extra hosts from webtoapp_config.json
        if (config != null && config.extraAdHosts.contains(lower)) return true;
        return false;
    }

    /** Returns an empty 200 response to silently swallow a blocked request.
     *  The page never sees a network error — the request just yields nothing. */
    private WebResourceResponse emptyResponse() {
        return new WebResourceResponse(
            "text/plain", "utf-8",
            new ByteArrayInputStream(new byte[0])
        );
    }

    @Override protected void onCreate(Bundle b) {
        super.onCreate(b);
        getWindow().requestFeature(android.view.Window.FEATURE_NO_TITLE);
        config = loadConfig();
        webView = new WebView(this);
        applyImmersiveMode();
        webView.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                return handleNavigation(request != null && request.getUrl() != null ? request.getUrl().toString() : null);
            }
            @Override public boolean shouldOverrideUrlLoading(WebView view, String url) {
                return handleNavigation(url);
            }
            // ── Ad blocker (modern API 21+) ───────────────────────────────
            // Intercepts every sub-resource request. Ad network hosts get an
            // empty 200 back; everything else passes through untouched.
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                if (request != null && request.getUrl() != null) {
                    if (isAdHost(request.getUrl().getHost())) {
                        return emptyResponse();
                    }
                    // Desktop mode: force a desktop-size layout viewport.
                    // A site's <meta name="viewport" content="width=device-width">
                    // pins the layout viewport to the phone width, so responsive
                    // pages render the mobile layout even when the user agent is
                    // desktop. Chrome's "request desktop site" uses a ~980px
                    // viewport, but WebView has no public API for that, so for the
                    // main-frame document we strip the viewport meta from the HTML
                    // before it is parsed. Without the meta the layout viewport
                    // falls back to the wide desktop viewport.
                    if (config != null && config.desktopMode
                            && request.isForMainFrame()
                            && "GET".equalsIgnoreCase(request.getMethod())
                            && ("http".equals(request.getUrl().getScheme())
                                || "https".equals(request.getUrl().getScheme()))) {
                        try {
                            WebResourceResponse desktop = desktopHtml(request.getUrl().toString());
                            if (desktop != null) return desktop;
                        } catch (Throwable ignored) {}
                    }
                }
                return super.shouldInterceptRequest(view, request);
            }
            // ── Ad blocker (legacy pre-API 21) ────────────────────────────
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, String url) {
                if (url != null) {
                    try {
                        if (isAdHost(Uri.parse(url).getHost())) {
                            return emptyResponse();
                        }
                    } catch (Throwable ignored) {}
                }
                return super.shouldInterceptRequest(view, url);
            }
            // ─────────────────────────────────────────────────────────────
        });
        webView.setWebChromeClient(new AppChromeClient());
        webView.setDownloadListener(new AppDownloadListener());
        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setAllowContentAccess(true);
        s.setAllowFileAccess(false);
        s.setJavaScriptCanOpenWindowsAutomatically(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setGeolocationEnabled(true);
        s.setLoadWithOverviewMode(true);
        s.setUseWideViewPort(true);
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.LOLLIPOP) {
            s.setMixedContentMode(WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE);
        }
        String ua = s.getUserAgentString();
        if (ua != null && !ua.isEmpty()) {
            s.setUserAgentString(config.desktopMode ? DESKTOP_USER_AGENT : sanitizeUserAgent(ua));
        }
        try {
            CookieManager cm = CookieManager.getInstance();
            cm.setAcceptCookie(true);
            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.LOLLIPOP) {
                cm.setAcceptThirdPartyCookies(webView, true);
            }
        } catch (Throwable ignored) {}
        try {
            String launchUrl = config.url != null && !config.url.isEmpty() ? config.url : "about:blank";
            webView.loadUrl(launchUrl);
        } catch (Exception e) { webView.loadUrl("about:blank"); }
        setContentView(webView);
        applyImmersiveMode();
    }

    private String sanitizeUserAgent(String ua) {
        return ua.replace("; wv", "").replace(" Version/4.0", "");
    }

    /**
     * Desktop mode helper. Fetches the main-frame document over the desktop
     * user agent and returns it with any viewport meta tag removed, so the
     * layout viewport falls back to the wide (~980px) desktop viewport.
     * Response headers (Set-Cookie, Cache-Control, ...) are passed through so
     * sessions and caching behave like a normal request. Returns null on any
     * failure so the caller falls back to the default WebView request.
     */
    private WebResourceResponse desktopHtml(String url) {
        java.net.HttpURLConnection conn = null;
        try {
            conn = (java.net.HttpURLConnection) new java.net.URL(url).openConnection();
            conn.setInstanceFollowRedirects(true);
            conn.setConnectTimeout(15000);
            conn.setReadTimeout(15000);
            conn.setRequestProperty("User-Agent", DESKTOP_USER_AGENT);
            String cookies = CookieManager.getInstance().getCookie(url);
            if (cookies != null && !cookies.isEmpty()) {
                conn.setRequestProperty("Cookie", cookies);
            }
            int code = conn.getResponseCode();
            if (code < 200 || code >= 300) return null;
            java.io.InputStream in = conn.getInputStream();
            java.io.ByteArrayOutputStream buf = new java.io.ByteArrayOutputStream();
            byte[] chunk = new byte[16384];
            int n;
            while ((n = in.read(chunk)) != -1) buf.write(chunk, 0, n);
            in.close();
            String contentType = conn.getContentType();
            String charset = "utf-8";
            if (contentType != null) {
                java.util.regex.Matcher cm = java.util.regex.Pattern
                    .compile("charset=([^;\\s]+)", java.util.regex.Pattern.CASE_INSENSITIVE)
                    .matcher(contentType);
                if (cm.find()) charset = cm.group(1).replace("\"", "").trim();
            }
            String html = new String(buf.toByteArray(), charset);
            html = html.replaceAll(
                "(?is)<meta\\b[^>]*\\bname\\s*=\\s*[\"']?viewport[\"']?[^>]*>", "");
            java.util.Map<String, String> headers = new java.util.HashMap<>();
            for (java.util.Map.Entry<String, java.util.List<String>> e : conn.getHeaderFields().entrySet()) {
                if (e.getKey() != null && e.getValue() != null && !e.getValue().isEmpty()) {
                    headers.put(e.getKey(), e.getValue().get(0));
                }
            }
            return new WebResourceResponse("text/html", charset, code, "OK", headers,
                new ByteArrayInputStream(html.getBytes(charset)));
        } catch (Throwable e) {
            return null;
        } finally {
            if (conn != null) conn.disconnect();
        }
    }

    private AppConfig loadConfig() {
        AppConfig loaded = new AppConfig();
        try {
            InputStream input = getAssets().open("webtoapp_config.json");
            byte[] data = input.readAllBytes();
            input.close();
            JSONObject json = new JSONObject(new String(data, StandardCharsets.UTF_8));
            loaded.url = json.optString("url", "about:blank").trim();
            loaded.immersiveFullscreen = json.optBoolean("immersive_fullscreen", false);
            loaded.desktopMode = json.optBoolean("desktop_mode", false);
            // Load any extra ad hosts supplied by the server at build time
            JSONArray extraHosts = json.optJSONArray("extra_ad_hosts");
            if (extraHosts != null) {
                for (int i = 0; i < extraHosts.length(); i++) {
                    String h = extraHosts.optString(i, "").trim().toLowerCase(Locale.US);
                    if (!h.isEmpty()) loaded.extraAdHosts.add(h);
                }
            }
        } catch (Throwable ignored) {}
        return loaded;
    }

    private void applyImmersiveMode() {
        if (config == null || !config.immersiveFullscreen) return;
        android.view.Window window = getWindow();
        // Draw behind the system bars so content fills the whole screen with no
        // black letterbox where the status/navigation bars used to be.
        // API 35+ (targetSdk 35+) enforces edge-to-edge and IGNORES the legacy
        // setSystemUiVisibility flags, so those paths below are only for < 35.
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            window.setDecorFitsSystemWindows(false);
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.BAKLAVA) {
            // targetSdk 35+: hide the bars entirely via WindowInsetsController and
            // pad the WebView by the transient-bar insets so content is never
            // drawn underneath the bars when the user swipes to reveal them.
            WindowInsetsController controller = window.getInsetsController();
            if (controller != null) {
                controller.hide(WindowInsets.Type.statusBars() | WindowInsets.Type.navigationBars());
                controller.setSystemBarsBehavior(WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE);
            }
            webView.setOnApplyWindowInsetsListener(new View.OnApplyWindowInsetsListener() {
                @Override public android.view.WindowInsets onApplyWindowInsets(View v, android.view.WindowInsets insets) {
                    android.graphics.Insets bars = insets.getInsets(
                        WindowInsets.Type.statusBars() | WindowInsets.Type.navigationBars()
                        | WindowInsets.Type.displayCutout());
                    v.setPadding(bars.left, bars.top, bars.right, bars.bottom);
                    return WindowInsets.CONSUMED;
                }
            });
        } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            WindowInsetsController controller = window.getInsetsController();
            if (controller != null) {
                controller.hide(WindowInsets.Type.statusBars() | WindowInsets.Type.navigationBars());
                controller.setSystemBarsBehavior(WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE);
            }
        } else {
            View decor = window.getDecorView();
            decor.setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                    | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                    | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                    | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                    | View.SYSTEM_UI_FLAG_FULLSCREEN
                    | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
            );
        }
        // Extend into the display cutout (notch) area too, and make the bars
        // transparent so nothing shows through during the transient swipe.
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            window.getAttributes().layoutInDisplayCutoutMode =
                android.view.WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES;
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            window.setStatusBarColor(android.graphics.Color.TRANSPARENT);
            window.setNavigationBarColor(android.graphics.Color.TRANSPARENT);
        }
    }

    private boolean handleNavigation(String url) {
        if (url == null) return false;
        String trimmed = url.trim();
        if (trimmed.isEmpty()) return false;
        String lower = trimmed.toLowerCase(Locale.US);
        if (
            lower.startsWith("http://") ||
            lower.startsWith("https://") ||
            lower.startsWith("about:") ||
            lower.startsWith("javascript:") ||
            lower.startsWith("data:") ||
            lower.startsWith("blob:")
        ) {
            return false;
        }
        if (lower.startsWith("intent://")) {
            return openIntentUri(trimmed);
        }
        return openExternal(trimmed);
    }

    private boolean openIntentUri(String url) {
        try {
            Intent intent = Intent.parseUri(url, Intent.URI_INTENT_SCHEME);
            String fallback = intent.getStringExtra("browser_fallback_url");
            intent.removeExtra("browser_fallback_url");
            intent.addCategory(Intent.CATEGORY_BROWSABLE);
            intent.setComponent(null);
            intent.setSelector(null);
            try {
                startActivity(intent);
                return true;
            } catch (Throwable ignored) {
                if (fallback != null && (fallback.startsWith("http://") || fallback.startsWith("https://"))) {
                    webView.loadUrl(fallback);
                    return true;
                }
            }
        } catch (Throwable ignored) {}
        return true;
    }

    private boolean openExternal(String url) {
        try {
            Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
            intent.addCategory(Intent.CATEGORY_BROWSABLE);
            intent.setComponent(null);
            intent.setSelector(null);
            startActivity(intent);
        } catch (Throwable ignored) {}
        return true;
    }

    private final class AppChromeClient extends WebChromeClient {
        @Override public void onGeolocationPermissionsShowPrompt(String origin, GeolocationPermissions.Callback callback) {
            handleGeolocationPermission(origin, callback);
        }

        @Override public void onPermissionRequest(final PermissionRequest request) {
            runOnUiThread(new Runnable() {
                @Override public void run() {
                    handleMediaPermission(request);
                }
            });
        }

        @Override public void onPermissionRequestCanceled(PermissionRequest request) {
            if (pendingPermissionRequest == request) {
                pendingPermissionRequest = null;
            }
        }

        // ── Popup blocker ─────────────────────────────────────────────────
        // Ad networks call window.open() without any user interaction to spawn
        // popup ads. We allow only windows that originated from a genuine user
        // gesture (e.g. a real link tap). Everything else is silently dropped.
        @Override
        public boolean onCreateWindow(WebView view, boolean isDialog,
                                      boolean isUserGesture, android.os.Message resultMsg) {
            return !isUserGesture;
        }
        // ─────────────────────────────────────────────────────────────────

        // ── File chooser (<input type="file">) ────────────────────────────
        // WebView ships no default file picker: without this override every
        // tap on an <input type="file"> silently does nothing. We hand the
        // request to the system picker via startActivityForResult and deliver
        // the result back in onActivityResult.
        @Override public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback,
                                                   FileChooserParams params) {
            // Settle any chooser still pending (e.g. the user backed out of a
            // previous one without cancelling cleanly). Leaving it hanging
            // makes WebView drop all future file-input taps.
            if (pendingFileChoiceCallback != null) {
                pendingFileChoiceCallback.onReceiveValue(null);
            }
            pendingFileChoiceCallback = callback;
            try {
                Intent intent = params.createIntent();
                if (params.getMode() == FileChooserParams.MODE_OPEN_MULTIPLE) {
                    intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true);
                }
                startActivityForResult(intent, REQ_FILE_CHOOSER);
                return true;
            } catch (Throwable ignored) {
                pendingFileChoiceCallback = null;
                return false;
            }
        }
        // ─────────────────────────────────────────────────────────────────
    }

    private final class AppDownloadListener implements DownloadListener {
        @Override public void onDownloadStart(String url, String userAgent, String contentDisposition, String mimeType, long contentLength) {
            PendingDownload download = new PendingDownload();
            download.url = url;
            download.userAgent = userAgent;
            download.contentDisposition = contentDisposition;
            download.mimeType = mimeType;
            download.fileName = URLUtil.guessFileName(url, contentDisposition, mimeType);
            if (needsLegacyWritePermission()) {
                pendingDownload = download;
                requestPermissions(new String[]{Manifest.permission.WRITE_EXTERNAL_STORAGE}, REQ_WRITE_STORAGE);
                return;
            }
            enqueueDownload(download);
        }
    }

    private void enqueueDownload(PendingDownload download) {
        if (download == null || download.url == null || download.url.trim().isEmpty()) return;
        try {
            DownloadManager manager = (DownloadManager) getSystemService(DOWNLOAD_SERVICE);
            if (manager == null) return;
            DownloadManager.Request request = new DownloadManager.Request(Uri.parse(download.url));
            request.setTitle(download.fileName);
            request.setDescription(download.url);
            request.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
            request.setMimeType(download.mimeType);
            request.setAllowedOverMetered(true);
            request.setAllowedOverRoaming(true);
            String cookies = CookieManager.getInstance().getCookie(download.url);
            if (cookies != null && !cookies.isEmpty()) {
                request.addRequestHeader("Cookie", cookies);
            }
            if (download.userAgent != null && !download.userAgent.isEmpty()) {
                request.addRequestHeader("User-Agent", download.userAgent);
            }
            request.setDestinationInExternalPublicDir(
                Environment.DIRECTORY_DOWNLOADS,
                buildDownloadRelativePath(download.fileName)
            );
            manager.enqueue(request);
        } catch (Throwable ignored) {}
    }

    private String buildDownloadRelativePath(String fileName) {
        return sanitizeFileSegment(fileName);
    }

    private String sanitizeFileSegment(String value) {
        String cleaned = String.valueOf(value == null ? "" : value).replaceAll("[\\\\/:*?\"<>|]+", "_").trim();
        return cleaned.isEmpty() ? "download.bin" : cleaned;
    }

    private boolean needsLegacyWritePermission() {
        return Build.VERSION.SDK_INT >= Build.VERSION_CODES.M
            && Build.VERSION.SDK_INT < Build.VERSION_CODES.Q
            && checkSelfPermission(Manifest.permission.WRITE_EXTERNAL_STORAGE) != PackageManager.PERMISSION_GRANTED;
    }

    private void handleGeolocationPermission(String origin, GeolocationPermissions.Callback callback) {
        if (hasAnyPermission(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION)) {
            callback.invoke(origin, true, false);
            return;
        }
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.M) {
            callback.invoke(origin, true, false);
            return;
        }
        pendingGeolocationOrigin = origin;
        pendingGeolocationCallback = callback;
        requestPermissions(
            new String[]{Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION},
            REQ_LOCATION
        );
    }

    private void handleMediaPermission(PermissionRequest request) {
        if (request == null) return;
        ArrayList<String> missingPermissions = new ArrayList<String>();
        for (String resource : request.getResources()) {
            if (PermissionRequest.RESOURCE_VIDEO_CAPTURE.equals(resource) && !hasPermission(Manifest.permission.CAMERA)) {
                missingPermissions.add(Manifest.permission.CAMERA);
            }
            if (PermissionRequest.RESOURCE_AUDIO_CAPTURE.equals(resource) && !hasPermission(Manifest.permission.RECORD_AUDIO)) {
                missingPermissions.add(Manifest.permission.RECORD_AUDIO);
            }
        }
        if (missingPermissions.isEmpty() || Build.VERSION.SDK_INT < Build.VERSION_CODES.M) {
            request.grant(request.getResources());
            return;
        }
        pendingPermissionRequest = request;
        requestPermissions(missingPermissions.toArray(new String[0]), REQ_MEDIA);
    }

    private boolean hasPermission(String permission) {
        return Build.VERSION.SDK_INT < Build.VERSION_CODES.M
            || checkSelfPermission(permission) == PackageManager.PERMISSION_GRANTED;
    }

    private boolean hasAnyPermission(String first, String second) {
        return hasPermission(first) || hasPermission(second);
    }

    private boolean allGranted(int[] grantResults) {
        if (grantResults == null || grantResults.length == 0) return false;
        for (int result : grantResults) {
            if (result != PackageManager.PERMISSION_GRANTED) return false;
        }
        return true;
    }

    @Override protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != REQ_FILE_CHOOSER) return;
        ValueCallback<Uri[]> callback = pendingFileChoiceCallback;
        pendingFileChoiceCallback = null;
        if (callback == null) return;  // activity recreated meanwhile: WebView's callback is gone
        // Deliver even when the user cancelled (null result) — leaving the
        // callback hanging makes WebView ignore all later file-input taps.
        callback.onReceiveValue(parseFileChooserResult(resultCode, data));
    }

    /**
     * Converts the system picker result into the Uri[] the WebView expects.
     * FileChooserParams.parseResult() only handles single selection, so
     * multi-select results are read from ClipData here.
     */
    private Uri[] parseFileChooserResult(int resultCode, Intent data) {
        if (resultCode != RESULT_OK || data == null) return null;
        ClipData clip = data.getClipData();
        if (clip != null) {
            ArrayList<Uri> uris = new ArrayList<Uri>();
            for (int i = 0; i < clip.getItemCount(); i++) {
                Uri uri = clip.getItemAt(i).getUri();
                if (uri != null) uris.add(uri);
            }
            return uris.isEmpty() ? null : uris.toArray(new Uri[0]);
        }
        Uri single = data.getData();
        return single != null ? new Uri[]{single} : null;
    }

    @Override public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == REQ_WRITE_STORAGE) {
            PendingDownload download = pendingDownload;
            pendingDownload = null;
            if (allGranted(grantResults)) {
                enqueueDownload(download);
            }
            return;
        }
        if (requestCode == REQ_LOCATION) {
            GeolocationPermissions.Callback callback = pendingGeolocationCallback;
            String origin = pendingGeolocationOrigin;
            pendingGeolocationCallback = null;
            pendingGeolocationOrigin = null;
            if (callback != null) {
                callback.invoke(origin, allGranted(grantResults), false);
            }
            return;
        }
        if (requestCode == REQ_MEDIA) {
            PermissionRequest request = pendingPermissionRequest;
            pendingPermissionRequest = null;
            if (request != null) {
                if (allGranted(grantResults)) request.grant(request.getResources());
                else request.deny();
            }
        }
    }

    @Override public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) applyImmersiveMode();
    }

    @Override public void onBackPressed() {
        if (webView != null && webView.canGoBack()) webView.goBack();
        else super.onBackPressed();
    }

    @Override protected void onDestroy() {
        pendingDownload = null;
        pendingGeolocationCallback = null;
        pendingGeolocationOrigin = null;
        pendingPermissionRequest = null;
        pendingFileChoiceCallback = null;
        if (webView != null) {
            webView.destroy();
            webView = null;
        }
        super.onDestroy();
    }

    private static final class PendingDownload {
        String url;
        String userAgent;
        String contentDisposition;
        String mimeType;
        String fileName;
    }

    private static final class AppConfig {
        String url = "about:blank";
        boolean immersiveFullscreen = false;
        boolean desktopMode = false;
        // Extra ad hosts injected at build time via webtoapp_config.json.
        // Allows blocking site-specific ad domains without rebuilding the APK template.
        Set<String> extraAdHosts = new HashSet<>();
    }
}
"""

MANIFEST_XML = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="{pkg}" android:versionCode="{version_code}" android:versionName="{version_name}">
    <uses-sdk android:minSdkVersion="21" android:targetSdkVersion="36"/>
    <uses-permission android:name="android.permission.INTERNET"/>
    <uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION"/>
    <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>
    <uses-permission android:name="android.permission.CAMERA"/>
    <uses-permission android:name="android.permission.RECORD_AUDIO"/>
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" android:maxSdkVersion="28"/>
    <application android:label="{name}" android:icon="@mipmap/ic_launcher"
        android:usesCleartextTraffic="true">
        <activity android:name="w.M" android:exported="true"
            android:theme="@android:style/Theme.NoTitleBar">
            <intent-filter>
                <action android:name="android.intent.action.MAIN"/>
                <category android:name="android.intent.category.LAUNCHER"/>
            </intent-filter>
        </activity>
    </application>
</manifest>
"""


class ApkBuilder:
    TEMPLATE_PACKAGE = "com.webtoapp.template"
    TEMPLATE_APP_NAME = "WebToApp Template"
    TEMPLATE_VERSION_CODE = 1
    TEMPLATE_VERSION_NAME = "1.0"
    TEMPLATE_REVISION = "2026-08-31-targetsdk36-1"
    # Keystore used only to sign the throwaway base *template* APK. The template
    # is always re-signed per-app afterwards, so this key never reaches users.
    TEMPLATE_KEY_ALIAS = "webtoapp"
    TEMPLATE_APK_NAME = "android-template.apk"

    def __init__(self):
        self.sdk = self._find_sdk()
        self.root = Path(__file__).resolve().parents[2]
        self.certs_dir = self.root / "certs"
        self.template_dir = self.root / "server" / "engine" / "_android_template"
        self.android_tools_dir = self.root / "server" / "engine" / "_android_tools"
        # Per-app signing keystores live here, one keystore per app_id. Kept
        # private (never publicly served) and out of version control.
        self.app_keys_dir = Path(config.android_keystore_dir())
        self.template_dir.mkdir(parents=True, exist_ok=True)
        self.android_tools_dir.mkdir(parents=True, exist_ok=True)
        self.certs_dir.mkdir(parents=True, exist_ok=True)
        self.app_keys_dir.mkdir(parents=True, exist_ok=True)

    def _find_sdk(self):
        for p in [
            os.environ.get("ANDROID_HOME"),
            os.environ.get("ANDROID_SDK_ROOT"),
            os.path.expanduser("~/Library/Android/sdk"),
            os.path.expanduser("~/Android/Sdk"),
        ]:
            if p and os.path.isdir(p):
                return p
        return None

    def _find_tool(self, name):
        tools = self._find_tools(name)
        return tools[0] if tools else None

    def _find_tools(self, name):
        results = []
        if self.sdk:
            bt = Path(self.sdk) / "build-tools"
            if bt.exists():
                for v in sorted(bt.iterdir(), reverse=True):
                    f = v / name
                    if f.exists():
                        results.append(str(f))
        path_tool = shutil.which(name)
        if path_tool and path_tool not in results:
            results.append(path_tool)
        return results

    def _find_jar(self):
        if not self.sdk:
            return None
        p = Path(self.sdk) / "platforms"
        if p.exists():
            for v in sorted(p.iterdir(), reverse=True):
                j = v / "android.jar"
                if j.exists():
                    return str(j)
        return None

    def _find_apktool(self):
        tool = shutil.which("apktool")
        if tool:
            return tool
        jar = self._apktool_jar()
        if jar and shutil.which("java"):
            return f"java -jar {self._shell_quote(str(jar))}"
        return None

    def _apktool_jar(self):
        jar = self.android_tools_dir / "apktool.jar"
        return jar if jar.exists() else None

    def _apksigner_jar(self):
        jar = self.android_tools_dir / "apksigner.jar"
        return jar if jar.exists() else None

    @property
    def can_build_apk(self):
        return self._can_patch_apk() and (self._template_apk_path().exists() or self._can_build_template())

    def _can_patch_apk(self):
        # The forkless patcher needs no apktool — just openssl (via
        # _export_signing_material) and our own v1/v2 signer. keytool/java are
        # only required to *mint* keystores; an existing per-app keystore is
        # used as-is. They stay in the list so hosts without a JDK don't get
        # silently switched to the PWA fallback on first build.
        return all([
            shutil.which("openssl"),
            shutil.which("keytool"),
            shutil.which("java"),
        ])

    def _can_build_template(self):
        return all([
            self.sdk,
            self._find_tool("aapt2"),
            self._find_tool("d8"),
            shutil.which("javac"),
            self._find_jar(),
            self._find_tool("apksigner"),
        ])

    def build_apk(self, output, url, name, pkg, icon_png=None, version_code=1, version_name="1.0", feature_options=None, app_id=None):
        if not self.can_build_apk:
            return False
        try:
            template_apk = self._ensure_template_apk(icon_png)
            if not template_apk or not template_apk.exists():
                return False
            self._patch_template_apk(
                template_apk=template_apk,
                output=Path(output),
                url=url,
                name=name,
                pkg=pkg,
                icon_png=icon_png,
                version_code=version_code,
                version_name=version_name,
                feature_options=feature_options or {},
                app_id=app_id or pkg,
            )
            if not self._validate_built_apk(Path(output)):
                raise RuntimeError("built APK failed alignment validation")
            return True
        except Exception as e:
            print(f"[ApkBuilder] template build failed: {e}")
            return False

    def _ensure_template_apk(self, icon_png=None):
        template_apk = self._template_apk_path()
        revision_file = self.template_dir / "template.revision"
        current_revision = revision_file.read_text().strip() if revision_file.exists() else ""
        if template_apk.exists() and current_revision == self.TEMPLATE_REVISION:
            return template_apk
        if template_apk.exists():
            template_apk.unlink()
        built = self._build_base_template(template_apk, icon_png)
        if built and built.exists():
            revision_file.write_text(self.TEMPLATE_REVISION)
        return built if built and built.exists() else None

    def _template_apk_path(self):
        return self.template_dir / self.TEMPLATE_APK_NAME

    def _seed_template_from_existing_generated(self, template_apk: Path):
        generated_dir = self.root / "generated"
        if not generated_dir.exists():
            return None
        for candidate in generated_dir.glob("*/downloads/android.apk"):
            if candidate.is_file():
                shutil.copy(candidate, template_apk)
                return template_apk
        return None

    def _build_base_template(self, template_apk: Path, icon_png=None):
        aapt2_candidates = self._find_tools("aapt2")
        d8 = self._find_tool("d8")
        javac = shutil.which("javac")
        jar = self._find_jar()
        apksigner = self._find_tool("apksigner")
        if not all([aapt2_candidates, d8, javac, jar, apksigner]):
            return None

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            src = tmp / "src" / "w"
            src.mkdir(parents=True)
            (src / "M.java").write_text(ACTIVITY_JAVA)

            manifest = tmp / "AndroidManifest.xml"
            manifest.write_text(
                MANIFEST_XML.format(
                    pkg=self.TEMPLATE_PACKAGE,
                    name=self.TEMPLATE_APP_NAME,
                    version_code=self.TEMPLATE_VERSION_CODE,
                    version_name=self.TEMPLATE_VERSION_NAME,
                )
            )

            mipmap = tmp / "res" / "mipmap"
            mipmap.mkdir(parents=True)
            if icon_png:
                (mipmap / "ic_launcher.png").write_bytes(icon_png)
            else:
                (mipmap / "ic_launcher.png").write_bytes(self._blank_png())

            compiled = tmp / "compiled"
            compiled.mkdir()
            apk_unsigned = tmp / "app-unsigned.apk"
            aapt2 = self._run_aapt2_with_fallback(aapt2_candidates, compiled, tmp, manifest, jar, apk_unsigned)
            if not aapt2:
                print("[ApkBuilder] All aapt2 versions failed")
                return None

            classes = tmp / "classes"
            classes.mkdir()
            subprocess.run(
                # -proc:none skips the annotation-processor classpath scan,
                # which is pure startup overhead for a processor-less build.
                [javac, "-proc:none", "-source", "1.8", "-target", "1.8", "-bootclasspath", jar, "-d", str(classes), str(src / "M.java")],
                check=True,
                capture_output=True,
            )

            dex_out = tmp / "dex"
            dex_out.mkdir()
            class_files = [str(f) for f in classes.rglob("*.class")]
            subprocess.run([d8, "--output", str(dex_out)] + class_files, check=True, capture_output=True)

            with zipfile.ZipFile(apk_unsigned, "a") as z:
                z.write(dex_out / "classes.dex", "classes.dex")
                z.writestr("assets/webtoapp_config.json", self._config_json("https://example.com", {}))

            aligned = tmp / "app-aligned.apk"
            self._align_apk(apk_unsigned, aligned)

            signed = tmp / "app-signed.apk"
            shutil.copy(aligned, signed)
            keystore, password, alias = self._ensure_template_keystore()
            subprocess.run(
                [
                    apksigner,
                    "sign",
                    "--ks",
                    str(keystore),
                    "--ks-pass",
                    f"pass:{password}",
                    "--key-pass",
                    f"pass:{password}",
                    "--ks-key-alias",
                    alias,
                    str(signed),
                ],
                check=True,
                capture_output=True,
            )
            shutil.copy(signed, template_apk)
            return template_apk

    def _ensure_template_keystore(self):
        """Keystore for signing the throwaway base template APK.

        Not security-critical (the template is re-signed per-app), but the
        password is sourced from config rather than hard-coded. Returns
        ``(keystore_path, password, alias)``.
        """
        keystore = self.certs_dir / "android-template.keystore"
        password = config.android_template_keystore_password()
        alias = self.TEMPLATE_KEY_ALIAS
        if keystore.exists():
            return keystore, password, alias
        self._generate_keystore(
            keystore=keystore,
            password=password,
            alias=alias,
            dname="CN=WebToApp Build Template,O=WebToApp,C=CN",
        )
        return keystore, password, alias

    def _ensure_app_keystore(self, app_id: str):
        """Return ``(keystore_path, password, alias)`` for ``app_id``.

        Generated once on first build and reused on every later build of the
        same app_id, so the signing certificate stays stable — required for
        Android to accept reinstalls as in-place updates (same package name +
        same signer). Each app_id gets a distinct random key, so no two
        generated apps share a signing certificate.

        The key *alias* is also randomized per app. apksigner derives the v1
        (JAR) signature filenames from the alias (e.g. alias ``Ab3xK`` →
        ``META-INF/AB3XK.SF`` / ``.RSA``), so a fixed alias would make every
        generated APK share the same ``APP.SF``/``APP.RSA`` names — a uniform
        pattern AV engines can fingerprint in bulk. A random alias gives each
        app distinct META-INF filenames. The alias is persisted so rebuilds of
        the same app_id keep stable filenames (filename changes don't affect
        update-eligibility, which is keyed on the certificate, but keeping them
        stable avoids churn).
        """
        safe_id = re.sub(r"[^a-z0-9_]", "", str(app_id or "").lower()) or "app"
        keystore = self.app_keys_dir / f"{safe_id}.keystore"
        meta_path = self.app_keys_dir / f"{safe_id}.json"
        if keystore.exists() and meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text())
                password = str(meta.get("password") or "")
                stored_alias = str(meta.get("alias") or "")
                if password and stored_alias:
                    return keystore, password, stored_alias
            except Exception:
                pass  # corrupt metadata: fall through and regenerate
        # First build for this app_id (or metadata lost): mint a fresh key.
        if keystore.exists():
            keystore.unlink()
        password = secrets.token_urlsafe(24)
        alias = self._random_key_alias()
        self._generate_keystore(
            keystore=keystore,
            password=password,
            alias=alias,
            dname=self._random_cert_dname(),
        )
        meta_path.write_text(json.dumps({"alias": alias, "password": password}, ensure_ascii=False))
        for path in (meta_path, keystore):
            try:
                os.chmod(path, 0o600)
            except OSError:
                pass
        return keystore, password, alias

    @staticmethod
    def _random_key_alias() -> str:
        """A random, alpha-led alias (letters/digits). apksigner uppercases it
        for the v1 META-INF/<ALIAS>.SF/.RSA filenames, so this randomizes those
        names per app while staying a valid keystore alias."""
        first = secrets.choice("abcdefghijklmnopqrstuvwxyz")
        rest = "".join(
            secrets.choice("abcdefghijklmnopqrstuvwxyz0123456789")
            for _ in range(secrets.randbelow(5) + 7)  # total length 8..12
        )
        return first + rest

    @staticmethod
    def _random_cert_dname() -> str:
        """A neutral, randomized certificate subject. Avoids every generated
        APK sharing an identical ``CN=WebToApp ...`` subject, which would be
        another easy bulk-fingerprint signal for AV engines."""
        cn = "".join(secrets.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(12))
        return f"CN={cn}"

    def _generate_keystore(self, keystore: Path, password: str, alias: str, dname: str):
        keystore.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "keytool",
                "-J-Djava.security.egd=file:/dev/urandom",
                "-genkeypair",
                "-v",
                "-storetype",
                "PKCS12",
                "-keystore",
                str(keystore),
                "-alias",
                alias,
                "-keyalg",
                "RSA",
                "-keysize",
                "2048",
                # Self-signed cert signed with SHA1withRSA. Real-device testing
                # showed AV engines flag the SHA256withRSA self-signed certs that
                # modern toolchains (apksigner/keytool defaults) emit, while the
                # older SHA1 cert signature (what MT Manager produces) is not
                # flagged. This only affects the certificate's OWN signature; the
                # v2/v3 APK content digests remain SHA-256.
                "-sigalg",
                "SHA1withRSA",
                "-validity",
                "36500",
                "-storepass",
                password,
                "-keypass",
                password,
                "-dname",
                dname,
            ],
            check=True,
            capture_output=True,
        )

    def _export_signing_material(self, keystore: Path, password: str, alias: str, tmp: Path):
        """Export (key_pem, cert_pem, key_der, cert_der, pubkey_der) from a
        PKCS12 keystore so our custom v1/v2/v3 signer (openssl-based) can use it."""
        p12 = tmp / "ks.p12"
        shutil.copy(keystore, p12)
        key_pem = tmp / "key.pem"
        cert_pem = tmp / "cert.pem"
        # private key (unencrypted PEM)
        subprocess.run(
            ["openssl", "pkcs12", "-in", str(p12), "-nodes", "-nocerts",
             "-passin", f"pass:{password}", "-out", str(key_pem)],
            check=True, capture_output=True,
        )
        # leaf certificate (PEM)
        subprocess.run(
            ["openssl", "pkcs12", "-in", str(p12), "-nokeys", "-clcerts",
             "-passin", f"pass:{password}", "-out", str(cert_pem)],
            check=True, capture_output=True,
        )
        key_der = tmp / "key.der"
        cert_der = tmp / "cert.der"
        pub_der = tmp / "pub.der"
        subprocess.run(["openssl", "pkcs8", "-topk8", "-nocrypt", "-in", str(key_pem),
                        "-outform", "DER", "-out", str(key_der)], check=True, capture_output=True)
        subprocess.run(["openssl", "x509", "-in", str(cert_pem), "-outform", "DER",
                        "-out", str(cert_der)], check=True, capture_output=True)
        pub_pem = subprocess.run(["openssl", "x509", "-in", str(cert_pem), "-noout", "-pubkey"],
                                 check=True, capture_output=True).stdout
        (tmp / "pub.pem").write_bytes(pub_pem)
        res = subprocess.run(["openssl", "rsa", "-pubin", "-in", str(tmp / "pub.pem"),
                              "-outform", "DER", "-out", str(pub_der)], capture_output=True)
        if res.returncode != 0:
            subprocess.run(["openssl", "pkey", "-pubin", "-in", str(tmp / "pub.pem"),
                            "-outform", "DER", "-out", str(pub_der)], check=True, capture_output=True)
        return key_pem, cert_pem, key_der.read_bytes(), cert_der.read_bytes(), pub_der.read_bytes()

    def _patch_template_apk(self, template_apk: Path, output: Path, url: str, name: str, pkg: str, icon_png, version_code: int, version_name: str, feature_options: dict, app_id: str = None):
        """Produce a per-app APK by copying the cached template and patching it
        in place — no apktool decode/rebuild round-trip.

        apktool spent ~1.8 s per build decoding the template to text and
        re-encoding it, yet the patch set is tiny: the manifest's package /
        version / label, one JSON asset and the launcher icon. All of those
        live in plain ZIP entries, so the per-app APK is now a byte-level
        rewrite of three entries followed by re-alignment and re-signing:

        - AndroidManifest.xml: AXML string-pool edit + versionCode int patch
        - assets/webtoapp_config.json: rewritten wholesale
        - res/mipmap/ic_launcher.png: rewritten wholesale

        The template's stale v1 signature files are dropped; build_v1 writes
        a fresh set over the per-app key.
        """
        keystore, password, alias = self._ensure_app_keystore(app_id or pkg)

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            patched = tmp / "app-patched.apk"
            self._patch_apk_entries(
                template_apk,
                patched,
                manifest=self._patched_manifest_xml(
                    template_apk, pkg, version_code, version_name, name
                ),
                replacements={
                    "assets/webtoapp_config.json": self._config_json(url, feature_options).encode("utf-8"),
                    **({"res/mipmap/ic_launcher.png": icon_png} if icon_png else {}),
                },
            )

            built_aligned = tmp / "app-aligned.apk"
            self._align_apk(patched, built_aligned)

            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(built_aligned, output)
            # Custom signing: write v1 (JAR) ourselves with a Gradle-style
            # Created-By, then append v2+v3 blocks. This avoids apksigner's
            # hard-coded "Created-By: 1.0 (Android)" v1 string, which mobile AV
            # engines fingerprint to flag tool-signed APKs.
            key_pem, cert_pem, key_der, cert_der, pub_der = self._export_signing_material(
                keystore, password, alias, tmp
            )
            apk_v2_signer.build_v1(output, key_pem, cert_pem, alias)
            apk_v2_signer.sign_v2(output, key_der, cert_der, pub_der)

    # ===== Forkless template patching (no apktool in the per-app path) =====

    def _patched_manifest_xml(self, template_apk: Path, pkg: str, version_code: int, version_name: str, name: str) -> bytes:
        """Binary-patch the template's compiled AndroidManifest.xml (AXML).

        The template manifest is produced by our own aapt2 build and always
        carries these exact literal strings, so the patch is a constrained
        rewrite of the AXML string pool plus the versionCode attribute value:

        - package="com.webtoapp.template"  ->  pkg
        - label / versionName literal      ->  name / version_name
        - versionCode="1" int attribute    ->  version_code
        """
        with zipfile.ZipFile(template_apk, "r") as zf:
            axml = zf.read("AndroidManifest.xml")
        patched = _AxmlPatcher(axml).patch(
            {
                self.TEMPLATE_PACKAGE: pkg,
                self.TEMPLATE_APP_NAME: name,
                self.TEMPLATE_VERSION_NAME: version_name,
            },
            version_code=int(version_code),
        )
        return patched

    def _patch_apk_entries(self, source_apk: Path, output_apk: Path, manifest: bytes, replacements: dict) -> None:
        """Copy ``source_apk`` to ``output_apk`` replacing whole ZIP entries.

        The template's v1 signature (META-INF/MANIFEST.MF and the template
        keystore's .SF/.RSA) is dropped — build_v1 writes a fresh set over the
        per-app key, and a stale template MANIFEST.MF would survive as a
        duplicate entry that v1 verifiers reject. Each entry keeps the
        template's original compression (``resources.arsc`` stays STORED as
        Android requires); the final zipalign pass restores the 4-byte
        alignment the rewrite shifts around.
        """
        output_apk.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(source_apk, "r") as zin, zipfile.ZipFile(output_apk, "w") as zout:
            for info in zin.infolist():
                if info.filename == "AndroidManifest.xml":
                    data = manifest
                elif info.filename in replacements:
                    data = replacements[info.filename]
                elif info.filename == "META-INF/MANIFEST.MF" or (
                    info.filename.startswith("META-INF/") and info.filename.upper().endswith((".SF", ".RSA"))
                ):
                    continue
                else:
                    data = zin.read(info.filename)
                zinfo = zipfile.ZipInfo(info.filename, date_time=info.date_time)
                zinfo.compress_type = info.compress_type
                zinfo.external_attr = info.external_attr
                zout.writestr(zinfo, data)

    def _align_apk(self, source: Path, output: Path) -> None:
        zipalign = self._find_tool("zipalign")
        output.parent.mkdir(parents=True, exist_ok=True)
        if zipalign:
            subprocess.run([zipalign, "-f", "4", str(source), str(output)], check=True, capture_output=True)
            return
        self._python_zipalign(source, output, alignment=4)

    def _python_zipalign(self, source: Path, output: Path, alignment: int = 4) -> None:
        """Align stored ZIP entries without relying on the external zipalign tool."""
        alignment = max(1, int(alignment or 1))
        tmp_output = output.with_suffix(output.suffix + ".tmp")
        if tmp_output.exists():
            tmp_output.unlink()
        with zipfile.ZipFile(source, "r") as zin, open(tmp_output, "wb") as raw_fp:
            with zipfile.ZipFile(raw_fp, "w") as zout:
                zout.comment = zin.comment
                for info in zin.infolist():
                    zinfo = zipfile.ZipInfo(info.filename, date_time=info.date_time)
                    zinfo.compress_type = info.compress_type
                    zinfo.comment = getattr(info, "comment", b"")
                    zinfo.extra = info.extra or b""
                    zinfo.create_system = info.create_system
                    zinfo.create_version = info.create_version
                    zinfo.extract_version = info.extract_version
                    zinfo.flag_bits = info.flag_bits
                    zinfo.volume = info.volume
                    zinfo.internal_attr = info.internal_attr
                    zinfo.external_attr = info.external_attr
                    zinfo.header_offset = 0

                    if info.is_dir():
                        zout.writestr(zinfo, b"")
                        continue

                    data = zin.read(info.filename)
                    if info.compress_type == zipfile.ZIP_STORED:
                        extra = self._alignment_extra(zout.fp.tell(), info.filename, zinfo.extra, alignment)
                        zinfo.extra = zinfo.extra + extra
                    zout.writestr(zinfo, data)
        tmp_output.replace(output)

    def _alignment_extra(self, current_offset: int, filename: str, existing_extra: bytes, alignment: int) -> bytes:
        """Return a valid extra-field padding block that keeps the next file aligned."""
        alignment = max(1, int(alignment or 1))
        name_len = len(str(filename or "").encode("utf-8"))
        extra_len = len(existing_extra or b"")
        pad_data_len = (alignment - ((current_offset + 30 + name_len + extra_len + 4) % alignment)) % alignment
        return b"\xff\xff" + pad_data_len.to_bytes(2, "little") + (b"\x00" * pad_data_len)

    def _validate_built_apk(self, apk_path: Path) -> bool:
        try:
            with zipfile.ZipFile(apk_path, "r") as zf:
                arsc = zf.getinfo("resources.arsc")
                if arsc.compress_type != zipfile.ZIP_STORED:
                    return False
                offset = self._zip_data_offset(zf, arsc)
                if offset % 4 != 0:
                    return False
                dex = zf.getinfo("classes.dex")
                if self._zip_data_offset(zf, dex) % 4 != 0:
                    return False
            return True
        except Exception:
            return False

    def _zip_data_offset(self, zf: zipfile.ZipFile, info: zipfile.ZipInfo) -> int:
        fp = zf.fp
        if fp is None:
            raise RuntimeError("zip file is closed")
        fp.seek(info.header_offset)
        header = fp.read(30)
        _, _, _, _, _, _, _, _, _, name_len, extra_len = struct.unpack("<IHHHHHIIIHH", header)
        return info.header_offset + 30 + name_len + extra_len

    def _run_aapt2_with_fallback(self, candidates, compiled, tmp, manifest, jar, apk_unsigned):
        for aapt2 in candidates:
            try:
                res_zip = compiled / "res.zip"
                if res_zip.exists():
                    res_zip.unlink()
                if apk_unsigned.exists():
                    apk_unsigned.unlink()
                subprocess.run([aapt2, "compile", "-o", str(res_zip), "--dir", str(tmp / "res")], check=True, capture_output=True)
                subprocess.run([aapt2, "link", "-o", str(apk_unsigned), "-I", jar, "--manifest", str(manifest), str(res_zip)], check=True, capture_output=True)
                return aapt2
            except subprocess.CalledProcessError as e:
                print(f"[ApkBuilder] aapt2 {aapt2} failed (exit={e.returncode}), trying next version")
                continue
        return None

    def build_fallback(self, output, url, name, icon_png=None, color="#000000"):
        manifest = {
            "name": name,
            "short_name": name[:12],
            "start_url": url,
            "display": "fullscreen",
            "background_color": color,
            "theme_color": color,
            "icons": [{"src": "icon.png", "sizes": "256x256", "type": "image/png"}] if icon_png else [],
        }
        html = f"""<!DOCTYPE html>
<html><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="{color}">
<meta name="apple-mobile-web-app-capable" content="yes">
<title>{name}</title><link rel="manifest" href="manifest.json">
<style>*{{margin:0}}html,body,iframe{{width:100%;height:100%;border:0;overflow:hidden}}</style>
</head><body>
<iframe src="{url}" allow="fullscreen"></iframe>
<script>if('serviceWorker' in navigator)navigator.serviceWorker.register('sw.js');</script>
</body></html>"""
        sw = "self.addEventListener('fetch',e=>{e.respondWith(fetch(e.request).catch(()=>caches.match(e.request)))});"
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(f"{name}/index.html", html)
            z.writestr(f"{name}/manifest.json", json.dumps(manifest, ensure_ascii=False))
            z.writestr(f"{name}/sw.js", sw)
            if icon_png:
                z.writestr(f"{name}/icon.png", icon_png)
            z.writestr(
                f"{name}/README.txt",
                f"【{name} — Android 安装指南】\n\n"
                f"方法一：将此文件夹部署到任意 HTTPS 服务器，用 Chrome 打开后点击「添加到主屏幕」\n"
                f"方法二：直接在浏览器中访问 {url}\n",
            )

    def _config_json(self, url: str, feature_options: dict) -> str:
        raw = feature_options or {}
        payload = {
            "url": str(url or "").strip() or "about:blank",
            "immersive_fullscreen": bool(
                raw.get("feature-immersive-fullscreen") or raw.get("feature_immersive_fullscreen")
            ),
            "desktop_mode": bool(
                raw.get("feature-desktop-mode") or raw.get("feature_desktop_mode")
            ),
            # Extra ad hosts injected per-build by the server. Passed through to
            # the APK's webtoapp_config.json asset and loaded at runtime by
            # AppConfig so site-specific domains can be blocked without a
            # template rebuild.
            "extra_ad_hosts": list(raw.get("extra_ad_hosts") or []),
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def _blank_png(self):
        size = 128
        rgba = (124, 58, 237, 255)
        ihdr_data = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
        ihdr = b"IHDR" + ihdr_data
        ihdr_chunk = struct.pack(">I", len(ihdr_data)) + ihdr + struct.pack(">I", zlib.crc32(ihdr))
        raw = b"".join(b"\x00" + bytes(rgba) * size for _ in range(size))
        idat_data = zlib.compress(raw, 9)
        idat = b"IDAT" + idat_data
        idat_chunk = struct.pack(">I", len(idat_data)) + idat + struct.pack(">I", zlib.crc32(idat))
        iend_chunk = struct.pack(">I", 0) + b"IEND" + struct.pack(">I", zlib.crc32(b"IEND"))
        return b"\x89PNG\r\n\x1a\n" + ihdr_chunk + idat_chunk + iend_chunk

    def _xml_escape(self, text: str) -> str:
        return (
            text.replace("&", "&amp;")
            .replace('"', "&quot;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    def _set_manifest_attr(self, manifest_text: str, attr_name: str, attr_value: str) -> str:
        attr_pattern = rf'{re.escape(attr_name)}="[^"]*"'
        if re.search(attr_pattern, manifest_text):
            return re.sub(attr_pattern, f'{attr_name}="{self._xml_escape(attr_value)}"', manifest_text, count=1)
        manifest_open = re.search(r"<manifest\b", manifest_text)
        if not manifest_open:
            return manifest_text
        insert_at = manifest_text.find(">", manifest_open.start())
        if insert_at == -1:
            return manifest_text
        return (
            manifest_text[:insert_at]
            + f' {attr_name}="{self._xml_escape(attr_value)}"'
            + manifest_text[insert_at:]
        )

    def _run_tool(self, tool, args):
        if tool.startswith("java -jar "):
            jar = tool[len("java -jar "):].strip("'")
            subprocess.run(["java", "-jar", jar] + args, check=True, capture_output=True)
            return
        subprocess.run([tool] + args, check=True, capture_output=True)

    def _sign_apk(self, apk_path: Path, keystore: Path, apksigner: str, apksigner_jar: Path, password: str = None, alias: str = None):
        base_args = [
            "sign",
            "--ks",
            str(keystore),
            "--ks-pass",
            f"pass:{password if password is not None else config.android_template_keystore_password()}",
            "--key-pass",
            f"pass:{password if password is not None else config.android_template_keystore_password()}",
            "--ks-key-alias",
            alias if alias is not None else self.TEMPLATE_KEY_ALIAS,
            str(apk_path),
        ]
        if apksigner:
            subprocess.run([apksigner] + base_args, check=True, capture_output=True)
            return
        if apksigner_jar and shutil.which("java"):
            subprocess.run(["java", "-jar", str(apksigner_jar)] + base_args, check=True, capture_output=True)
            return
        raise RuntimeError("No apksigner available")

    def _shell_quote(self, value: str) -> str:
        return value.replace("'", "'\"'\"'")
