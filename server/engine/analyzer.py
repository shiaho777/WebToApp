"""
Site Intelligence Engine — Analyzes any URL.
Extracts structure, detects bloat, calculates optimization potential.
"""

import asyncio
import time
import base64
import httpx
import re
from urllib.parse import urljoin, urlparse

from server.engine.distiller import Distiller
from server.engine.cache import analysis_cache, html_cache, icon_cache
from server.htmlmeta import parse_html_metadata
from server.net import aread_limited_response, avalidate_public_http_url, redirect_target
from server import config


# Common ad/tracker domains
AD_DOMAINS = {
    'doubleclick.net', 'googlesyndication.com', 'googleadservices.com',
    'facebook.net', 'analytics.google.com', 'googletagmanager.com',
    'hotjar.com', 'mixpanel.com', 'segment.com', 'amplitude.com',
    'taboola.com', 'outbrain.com', 'criteo.com', 'quantserve.com',
    'scorecardresearch.com', 'bluekai.com', 'chartbeat.com',
    'baidu.com/hm', 'cnzz.com', 'umeng.com', '51.la', 'tongji.baidu.com',
}

# Popup/overlay patterns
POPUP_PATTERNS = [
    r'cookie[_-]?(banner|consent|notice|popup)',
    r'newsletter[_-]?(modal|popup|signup)',
    r'subscribe[_-]?(modal|popup|overlay)',
    r'overlay[_-]?(backdrop|modal)',
    r'interstitial',
    r'gdpr',
]

# Authentication-wall (reverse-proxy SSO) signatures. When a site sits behind
# one of these, an unauthenticated server-side fetch is redirected to the
# provider's login portal and never sees the real page. We detect that and
# return a structured "auth-protected" result instead of analyzing the login
# page (which would yield the portal's name/icon as if it were the app).
#
# The generated app itself still works: the WebView loads the target URL, the
# user authenticates inside it once, and the session cookie persists in the
# platform CookieManager. This detection only governs the analysis step.
AUTH_WALL_HOST_SUFFIXES = (
    "cloudflareaccess.com",     # Cloudflare Zero Trust / Access
    ".cloudflareaccess.com",
)
AUTH_WALL_COOKIE_NAMES = (
    "authelia_session",         # Authelia
    "cf_authorization",         # Cloudflare Access (JWT)
)
AUTH_WALL_LOCATION_MARKERS = (
    "cloudflareaccess.com/cdn-cgi/access",
    "/auth/?rd=",               # Authelia redirect-to-portal: ?rd=<origin>
    "/auth/reminder",           # Authelia reminder endpoint
)


def _detect_auth_wall(resp, location: str) -> str:
    """Return the auth-provider name when ``resp`` looks like an auth wall, else "".

    Checks, in order: the redirect Location URL, the response's Set-Cookie
    header, and the final-page URL host. Mirrors how Authelia and Cloudflare
    Access intercept unauthenticated requests.
    """
    loc = (location or "").lower()
    for marker in AUTH_WALL_LOCATION_MARKERS:
        if marker in loc:
            return "cloudflare_access" if "cloudflareaccess" in marker else "authelia"

    # Set-Cookie may be a list (multiple cookies) or a single string.
    set_cookie = resp.headers.get("set-cookie") if resp is not None else None
    if set_cookie:
        cookies = set_cookie if isinstance(set_cookie, list) else [set_cookie]
        joined = "\n".join(cookies).lower()
        for name in AUTH_WALL_COOKIE_NAMES:
            if name in joined:
                return "authelia" if name.startswith("authelia") else "cloudflare_access"

    return ""


class SiteAnalyzer:
    """Analyzes a website's structure, performance, and bloat."""

    def __init__(self):
        self.client = httpx.AsyncClient(
            follow_redirects=False,
            timeout=15.0,
            headers={"User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/120.0 Mobile Safari/537.36"},
        )
        self.icon_distiller = Distiller()

    async def analyze(self, url: str) -> dict:
        if not url.startswith('http'):
            url = 'https://' + url
        started = time.perf_counter()
        cache_key = f"analyze:{url}"
        cached = analysis_cache.get(cache_key)
        if cached is not None:
            result = dict(cached)
            result["cacheHit"] = True
            result["durationMs"] = int((time.perf_counter() - started) * 1000)
            return result
        final_url, html, content_length, raw, auth_provider = await self._fetch_page(url)
        if auth_provider:
            # Site sits behind an auth proxy (Authelia / Cloudflare Access).
            # There is no real page to analyze; return a structured signal so
            # the UI can ask the user for the name/icon manually. The generated
            # app itself still works — the user authenticates inside the WebView.
            result = self._auth_protected_result(final_url, auth_provider)
        else:
            if raw is not None:
                html_cache.set(f"bytes:{final_url}", raw)
                if final_url != url:
                    html_cache.set(f"bytes:{url}", raw)
            result = await self._analyze_html(final_url, html, content_length)
        result["cacheHit"] = False
        result["durationMs"] = int((time.perf_counter() - started) * 1000)
        analysis_cache.set(cache_key, dict(result))
        if final_url != url:
            analysis_cache.set(f"analyze:{final_url}", dict(result))
        return result

    def _auth_protected_result(self, url: str, provider: str) -> dict:
        """Build a minimal but useful result for an auth-protected site.

        The UI uses ``authProtected`` to show an explanatory notice and to
        encourage the user to fill in the name/icon manually. We still provide
        sensible fallbacks (host-derived name, favicon service) so the form is
        usable without any server-side visibility into the protected page.
        """
        parsed = urlparse(url)
        host = parsed.hostname or url
        host_label = self._host_label(host) or host
        suggested_name = self._trim_app_name(host_label[:1].upper() + host_label[1:])
        favicon = f"https://www.google.com/s2/favicons?domain={parsed.hostname}&sz=64"
        return {
            "title": host,
            "suggestedName": suggested_name,
            "suggestedNameSource": "host_fallback",
            "siteName": "",
            "url": url,
            "host": host,
            "favicon": favicon,
            "faviconDataUrl": "",
            "themeColor": "#7c3aed",
            "description": "",
            "ads": 0,
            "trackers": 0,
            "popups": 0,
            "totalScripts": 0,
            "originalSize": "N/A",
            "distilledSize": "N/A",
            "speedBoost": "N/A",
            "authProtected": True,
            "authProvider": provider,
        }

    async def _fetch_page(self, url: str) -> tuple[str, str, int, bytes, str]:
        """Fetch the page, following redirects manually.

        Returns ``(final_url, html, content_length, raw_bytes, auth_provider)``
        where ``auth_provider`` is a non-empty string ("authelia" /
        "cloudflare_access") when the site is behind an authentication wall.
        In that case the fetch stops at the auth redirect and ``html`` is empty
        — there is no real page for the analyzer to read.
        """
        current_url = await avalidate_public_http_url(url)
        for _ in range(config.outbound_redirect_limit() + 1):
            cached = html_cache.get(f"bytes:{current_url}")
            if cached is not None:
                return current_url, cached.decode("utf-8", errors="ignore"), len(cached), cached, ""
            async with self.client.stream("GET", current_url) as resp:
                if resp.status_code in {301, 302, 303, 307, 308}:
                    location = resp.headers.get("location", "")
                    # Stop and report when the redirect targets an auth portal
                    # (Authelia / Cloudflare Access). Following it would only
                    # analyze the login page.
                    provider = _detect_auth_wall(resp, location)
                    if provider:
                        return current_url, "", 0, b"", provider
                    current_url = await asyncio.to_thread(redirect_target, current_url, location)
                    continue
                resp.raise_for_status()
                raw = await aread_limited_response(resp, config.outbound_response_max_bytes())
                encoding = getattr(resp, "encoding", None) or "utf-8"
                return current_url, raw.decode(encoding, errors="ignore"), len(raw), raw, ""
        raise httpx.TooManyRedirects(f"Exceeded redirect limit for {url}")

    async def _analyze_html(self, url: str, html: str, content_length: int) -> dict:
        parsed = urlparse(url)
        host = parsed.hostname or ''
        doc = parse_html_metadata(html)

        title = doc.title or host
        site_name, site_name_source = self._extract_site_name(doc)
        description = doc.meta_content('description', 'og:description')
        theme_color = doc.meta_content('theme-color') or '#7c3aed'
        favicon = self._extract_favicon(doc, url)
        favicon_data_url = await asyncio.to_thread(self._favicon_data_url, url)
        suggested_name, suggested_name_source = self._suggest_app_name(
            title,
            host,
            site_name,
            site_name_source,
        )

        scripts = list(doc.script_srcs)
        ad_scripts = [s for s in scripts if any(ad in s for ad in AD_DOMAINS)]
        tracker_scripts = [s for s in scripts if self._is_tracker(s)]
        popup_elements = sum(1 for p in POPUP_PATTERNS if re.search(p, html, re.I))
        inline_css_size = doc.inline_style_size
        inline_js_size = doc.inline_script_size
        total_bloat = len(ad_scripts) * 45000 + inline_js_size * 0.3  # estimated

        original_kb = content_length / 1024
        estimated_distilled_kb, speed_boost = self._estimate_distilled_metrics(
            original_kb=original_kb,
            total_scripts=len(scripts),
            ad_count=len(ad_scripts),
            tracker_count=len(tracker_scripts),
            popup_count=popup_elements,
            inline_js_kb=inline_js_size / 1024,
            inline_css_kb=inline_css_size / 1024,
            total_bloat_kb=total_bloat / 1024,
        )

        return {
            "title": title,
            "suggestedName": suggested_name,
            "suggestedNameSource": suggested_name_source,
            "siteName": site_name,
            "url": url,
            "host": host,
            "favicon": favicon,
            "faviconDataUrl": favicon_data_url,
            "themeColor": theme_color,
            "description": description,
            "ads": len(ad_scripts),
            "trackers": len(tracker_scripts),
            "popups": popup_elements,
            "totalScripts": len(scripts),
            "originalSize": f"{original_kb:.0f} KB" if original_kb < 1024 else f"{original_kb/1024:.1f} MB",
            "distilledSize": f"{estimated_distilled_kb:.0f} KB",
            "speedBoost": f"{speed_boost}x",
        }

    def _estimate_distilled_metrics(
        self,
        *,
        original_kb: float,
        total_scripts: int,
        ad_count: int,
        tracker_count: int,
        popup_count: int,
        inline_js_kb: float,
        inline_css_kb: float,
        total_bloat_kb: float,
    ) -> tuple[float, float]:
        original_kb = max(float(original_kb or 0), 0.5)
        total_scripts = max(int(total_scripts or 0), 0)
        ad_count = max(int(ad_count or 0), 0)
        tracker_count = max(int(tracker_count or 0), 0)
        popup_count = max(int(popup_count or 0), 0)
        inline_js_kb = max(float(inline_js_kb or 0), 0.0)
        inline_css_kb = max(float(inline_css_kb or 0), 0.0)
        total_bloat_kb = max(float(total_bloat_kb or 0), 0.0)

        if original_kb < 24:
            retained_ratio = 0.74 if total_scripts <= 4 else 0.62
            estimated_distilled_kb = max(original_kb * retained_ratio, 0.5)
            speed_boost = max(round(original_kb / estimated_distilled_kb, 1), 1.1)
            return estimated_distilled_kb, speed_boost

        estimated_savings_kb = (
            total_bloat_kb * 0.35
            + max(total_scripts - 4, 0) * 8.0
            + ad_count * 42.0
            + tracker_count * 18.0
            + popup_count * 6.0
            + inline_js_kb * 0.75
            + inline_css_kb * 0.35
        )
        min_savings_kb = original_kb * 0.08
        max_savings_kb = original_kb * 0.82
        bounded_savings_kb = min(max(estimated_savings_kb, min_savings_kb), max_savings_kb)
        estimated_distilled_kb = max(12.0, original_kb - bounded_savings_kb)
        estimated_distilled_kb = min(estimated_distilled_kb, original_kb * 0.92)
        speed_boost = max(round(original_kb / max(estimated_distilled_kb, 0.5), 1), 1.1)
        return estimated_distilled_kb, speed_boost

    def _extract_site_name(self, doc) -> tuple[str, str]:
        candidates = [
            ("site_name", doc.meta_content('og:site_name', 'site_name')),
            ("application_name", doc.meta_content('application-name')),
            ("apple_mobile_web_app_title", doc.meta_content('apple-mobile-web-app-title')),
        ]
        for source, value in candidates:
            if self._normalize_text(value):
                return value, source
        return "", ""

    def _suggest_app_name(
        self,
        title: str,
        host: str,
        site_name: str = '',
        site_name_source: str = '',
    ) -> tuple[str, str]:
        host_label = self._host_label(host)
        clean_site_name = self._normalize_text(site_name)
        clean_title = self._normalize_text(title)

        if clean_site_name:
            return self._trim_app_name(clean_site_name), (site_name_source or "site_name")

        if not clean_title:
            return self._trim_app_name(host_label or host or "WebToApp"), "host_fallback"

        parts = self._split_title_parts(clean_title)
        host_matches = [part for part in parts if self._part_matches_host(part, host_label)]
        if host_matches:
            best = min(host_matches, key=lambda part: (len(part), parts.index(part)))
            return self._trim_app_name(best), "title_host_match"

        short_parts = [part for part in parts if 1 < len(part) <= 36]
        if short_parts:
            source = "title_first_part" if len(parts) > 1 else "title_full"
            return self._trim_app_name(short_parts[0]), source

        return self._trim_app_name(clean_title), "title_full"

    def _normalize_text(self, value: str) -> str:
        text = re.sub(r"\s+", " ", str(value or "")).strip()
        text = re.sub(r"\s*([|｜\-—–·•:：])\s*", r" \1 ", text)
        return re.sub(r"\s+", " ", text).strip(" -—–|｜·•:：")

    def _split_title_parts(self, title: str) -> list[str]:
        parts = re.split(r"\s*[|｜\-—–·•:：]\s*", title)
        ordered = []
        seen = set()
        for part in parts:
            token = self._normalize_text(part)
            key = token.casefold()
            if len(token) < 2 or key in seen:
                continue
            seen.add(key)
            ordered.append(token)
        return ordered or ([title] if title else [])

    def _host_label(self, host: str) -> str:
        labels = [label for label in str(host or "").lower().split(".") if label]
        while labels and labels[0] in {"www", "m", "mobile"}:
            labels.pop(0)
        return labels[0] if labels else ""

    def _part_matches_host(self, part: str, host_label: str) -> bool:
        if not host_label:
            return False
        lowered = re.sub(r"[^a-z0-9]+", "", part.lower())
        return host_label in lowered or lowered in host_label

    def _trim_app_name(self, value: str) -> str:
        text = re.sub(r"\s+", " ", str(value or "")).strip()
        if len(text) <= 40:
            return text
        return text[:40].rstrip() + "..."

    def _extract_favicon(self, doc, base_url: str) -> str:
        for attrs in doc.link_attrs_by_rel('apple-touch-icon', 'icon'):
            href = attrs.get("href", "").strip()
            if href:
                return urljoin(base_url, href)
        parsed = urlparse(base_url)
        return f"https://www.google.com/s2/favicons?domain={parsed.hostname}&sz=64"

    def _favicon_data_url(self, url: str) -> str:
        try:
            host = urlparse(url).netloc.lower()
            cache_key = f"icon:{host}"
            icon_png = icon_cache.get(cache_key)
            if not icon_png:
                candidates = self.icon_distiller._collect_icon_candidates(url)
                icon_png = self.icon_distiller._choose_best_icon(candidates)
                if icon_png:
                    icon_cache.set(cache_key, icon_png)
        except Exception:
            return ""
        if not icon_png:
            return ""
        return "data:image/png;base64," + base64.b64encode(icon_png).decode("ascii")

    def _is_tracker(self, src: str) -> bool:
        tracker_kw = ['analytics', 'tracking', 'pixel', 'beacon', 'telemetry', 'metrics']
        return any(kw in src.lower() for kw in tracker_kw) or any(ad in src for ad in AD_DOMAINS)
