import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

import server.engine.analyzer as analyzer_module
from server.engine.analyzer import SiteAnalyzer


class DummyCache:
    def __init__(self, initial=None):
        self.data = dict(initial or {})
        self.set_calls = []

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value):
        self.data[key] = value
        self.set_calls.append((key, value))


class FakeAsyncResponse:
    def __init__(self, status_code=200, headers=None, encoding="utf-8"):
        self.status_code = status_code
        self.headers = dict(headers or {})
        self.encoding = encoding
        self.raised = False

    def raise_for_status(self):
        self.raised = True


class FakeAsyncStream:
    def __init__(self, response):
        self.response = response

    async def __aenter__(self):
        return self.response

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class FakeAsyncClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def stream(self, method, url):
        self.requests.append((method, url))
        return FakeAsyncStream(self.responses.pop(0))


def test_analyze_cache_hit_returns_copy_and_duration(monkeypatch):
    cache = DummyCache({"analyze:https://cached.example": {"title": "Cached", "cacheHit": False}})
    monkeypatch.setattr(analyzer_module, "analysis_cache", cache)
    analyzer = SiteAnalyzer()
    analyzer._fetch_page = AsyncMock(side_effect=AssertionError("must not fetch"))

    result = asyncio.run(analyzer.analyze("https://cached.example"))
    assert result["title"] == "Cached"
    assert result["cacheHit"] is True
    assert isinstance(result["durationMs"], int)
    assert cache.data["analyze:https://cached.example"]["cacheHit"] is False


def test_analyze_miss_normalizes_url_and_populates_alias_caches(monkeypatch):
    analysis = DummyCache()
    html = DummyCache()
    monkeypatch.setattr(analyzer_module, "analysis_cache", analysis)
    monkeypatch.setattr(analyzer_module, "html_cache", html)
    analyzer = SiteAnalyzer()
    analyzer._fetch_page = AsyncMock(
        return_value=("https://final.example/page", "<title>Final</title>", 20, b"raw html", "")
    )
    analyzer._analyze_html = AsyncMock(return_value={"title": "Final"})

    result = asyncio.run(analyzer.analyze("start.example"))
    analyzer._fetch_page.assert_awaited_once_with("https://start.example")
    analyzer._analyze_html.assert_awaited_once_with("https://final.example/page", "<title>Final</title>", 20)
    assert result["cacheHit"] is False
    assert html.data["bytes:https://final.example/page"] == b"raw html"
    assert html.data["bytes:https://start.example"] == b"raw html"
    assert analysis.data["analyze:https://start.example"]["title"] == "Final"
    assert analysis.data["analyze:https://final.example/page"]["title"] == "Final"


def test_analyze_miss_same_url_and_no_raw_skips_aliases(monkeypatch):
    analysis = DummyCache()
    html = DummyCache()
    monkeypatch.setattr(analyzer_module, "analysis_cache", analysis)
    monkeypatch.setattr(analyzer_module, "html_cache", html)
    analyzer = SiteAnalyzer()
    analyzer._fetch_page = AsyncMock(return_value=("http://same.example", "html", 4, None, ""))
    analyzer._analyze_html = AsyncMock(return_value={"ok": True})

    result = asyncio.run(analyzer.analyze("http://same.example"))
    assert result["ok"] is True
    assert html.set_calls == []
    assert [key for key, _ in analysis.set_calls] == ["analyze:http://same.example"]


def test_fetch_page_uses_cached_bytes(monkeypatch):
    cache = DummyCache({"bytes:https://cached.example": "café".encode("utf-8")})
    monkeypatch.setattr(analyzer_module, "html_cache", cache)
    monkeypatch.setattr(analyzer_module, "avalidate_public_http_url", AsyncMock(return_value="https://cached.example"))
    analyzer = SiteAnalyzer()
    analyzer.client = FakeAsyncClient([])

    final_url, html, length, raw, auth_provider = asyncio.run(analyzer._fetch_page("https://cached.example"))
    assert final_url == "https://cached.example"
    assert html == "café"
    assert length == len(raw)
    assert auth_provider == ""
    assert analyzer.client.requests == []


@pytest.mark.parametrize("encoding", ["latin-1", None])
def test_fetch_page_reads_network_response_and_encoding(monkeypatch, encoding):
    cache = DummyCache()
    response = FakeAsyncResponse(200, encoding=encoding)
    monkeypatch.setattr(analyzer_module, "html_cache", cache)
    monkeypatch.setattr(analyzer_module, "avalidate_public_http_url", AsyncMock(return_value="https://page.example"))
    monkeypatch.setattr(analyzer_module, "aread_limited_response", AsyncMock(return_value=b"caf\xe9"))
    monkeypatch.setattr(analyzer_module.config, "outbound_redirect_limit", lambda: 2)
    monkeypatch.setattr(analyzer_module.config, "outbound_response_max_bytes", lambda: 123)
    analyzer = SiteAnalyzer()
    analyzer.client = FakeAsyncClient([response])

    final_url, html, length, raw, auth_provider = asyncio.run(analyzer._fetch_page("https://page.example"))
    assert final_url == "https://page.example"
    assert raw == b"caf\xe9"
    assert length == 4
    assert html == ("café" if encoding else "caf")
    assert response.raised is True
    analyzer_module.aread_limited_response.assert_awaited_once_with(response, 123)


def test_fetch_page_follows_redirect(monkeypatch):
    first = FakeAsyncResponse(302, {"location": "/final"})
    second = FakeAsyncResponse(200)
    monkeypatch.setattr(analyzer_module, "html_cache", DummyCache())
    monkeypatch.setattr(analyzer_module, "avalidate_public_http_url", AsyncMock(return_value="https://start.example"))
    monkeypatch.setattr(analyzer_module, "aread_limited_response", AsyncMock(return_value=b"ok"))
    monkeypatch.setattr(analyzer_module.config, "outbound_redirect_limit", lambda: 1)
    monkeypatch.setattr(analyzer_module.config, "outbound_response_max_bytes", lambda: 100)
    monkeypatch.setattr(
        analyzer_module.asyncio,
        "to_thread",
        AsyncMock(return_value="https://start.example/final"),
    )
    analyzer = SiteAnalyzer()
    analyzer.client = FakeAsyncClient([first, second])

    result = asyncio.run(analyzer._fetch_page("https://start.example"))
    assert result == ("https://start.example/final", "ok", 2, b"ok", "")
    analyzer_module.asyncio.to_thread.assert_awaited_once_with(
        analyzer_module.redirect_target, "https://start.example", "/final"
    )


@pytest.mark.parametrize(
    "location,headers,expected",
    [
        # Cloudflare Access: redirect to the access login portal.
        (
            "https://acme.cloudflareaccess.com/cdn-cgi/access/login/abc",
            {},
            "cloudflare_access",
        ),
        # Authelia: redirect to the portal with the rd= (redirect) marker.
        (
            "https://auth.example.com/auth/?rd=https%3A%2F%2Fstart.example",
            {},
            "authelia",
        ),
        # Authelia: session cookie set directly on a 200.
        (
            "",
            {"set-cookie": "authelia_session=xyz; Path=/; HttpOnly"},
            "authelia",
        ),
    ],
)
def test_fetch_page_stops_at_auth_wall(monkeypatch, location, headers, expected):
    first = FakeAsyncResponse(302, {"location": location, **headers} if location else headers)
    monkeypatch.setattr(analyzer_module, "html_cache", DummyCache())
    monkeypatch.setattr(analyzer_module, "avalidate_public_http_url", AsyncMock(return_value="https://start.example"))
    monkeypatch.setattr(analyzer_module.config, "outbound_redirect_limit", lambda: 5)
    analyzer = SiteAnalyzer()
    analyzer.client = FakeAsyncClient([first])

    result = asyncio.run(analyzer._fetch_page("https://start.example"))
    # Stops immediately at the auth redirect; no real page fetched.
    assert result == ("https://start.example", "", 0, b"", expected)


def test_fetch_page_raises_after_redirect_limit(monkeypatch):
    response = FakeAsyncResponse(301, {"location": "https://elsewhere.example"})
    monkeypatch.setattr(analyzer_module, "html_cache", DummyCache())
    monkeypatch.setattr(analyzer_module, "avalidate_public_http_url", AsyncMock(return_value="https://start.example"))
    monkeypatch.setattr(analyzer_module.config, "outbound_redirect_limit", lambda: 0)
    monkeypatch.setattr(analyzer_module.asyncio, "to_thread", AsyncMock(return_value="https://elsewhere.example"))
    analyzer = SiteAnalyzer()
    analyzer.client = FakeAsyncClient([response])

    with pytest.raises(httpx.TooManyRedirects, match="Exceeded redirect limit"):
        asyncio.run(analyzer._fetch_page("https://start.example"))


def test_analyze_html_extracts_all_metadata_and_mb_size(monkeypatch):
    html = """
    <html><head>
      <title> Example Portal | News </title>
      <meta name="description" content="A description">
      <meta property="og:site_name" content="Example Suite">
      <meta name="theme-color" content="#010203">
      <link rel="shortcut icon" href="/icon.png">
      <script src="https://doubleclick.net/ad.js"></script>
      <script src="https://cdn.example/analytics.js"></script>
      <script>inline code</script>
      <style>body { color: red; }</style>
    </head><body class="cookie-banner newsletter-modal gdpr"></body></html>
    """
    analyzer = SiteAnalyzer()
    monkeypatch.setattr(analyzer, "_favicon_data_url", lambda url: "data:image/png;base64,WA==")
    result = asyncio.run(analyzer._analyze_html("https://www.example.com/path", html, 2 * 1024 * 1024))

    assert result["title"] == "Example Portal | News"
    assert result["suggestedName"] == "Example Suite"
    assert result["suggestedNameSource"] == "site_name"
    assert result["siteName"] == "Example Suite"
    assert result["host"] == "www.example.com"
    assert result["favicon"] == "https://www.example.com/icon.png"
    assert result["faviconDataUrl"].startswith("data:image/png")
    assert result["themeColor"] == "#010203"
    assert result["description"] == "A description"
    assert result["ads"] == 1
    assert result["trackers"] == 2
    assert result["popups"] == 3
    assert result["totalScripts"] == 2
    assert result["originalSize"] == "2.0 MB"


def test_analyze_html_uses_host_and_default_metadata(monkeypatch):
    analyzer = SiteAnalyzer()
    monkeypatch.setattr(analyzer, "_favicon_data_url", lambda url: "")
    result = asyncio.run(analyzer._analyze_html("https://m.sample.example", "<html></html>", 512))

    assert result["title"] == "m.sample.example"
    assert result["siteName"] == ""
    assert result["themeColor"] == "#7c3aed"
    assert result["description"] == ""
    assert result["favicon"] == "https://www.google.com/s2/favicons?domain=m.sample.example&sz=64"
    assert result["originalSize"] == "0 KB"


def test_estimate_distilled_metrics_small_and_large_branches():
    analyzer = SiteAnalyzer()
    tiny_few = analyzer._estimate_distilled_metrics(
        original_kb=0,
        total_scripts=-1,
        ad_count=-1,
        tracker_count=-1,
        popup_count=-1,
        inline_js_kb=-1,
        inline_css_kb=-1,
        total_bloat_kb=-1,
    )
    tiny_many = analyzer._estimate_distilled_metrics(
        original_kb=10,
        total_scripts=5,
        ad_count=0,
        tracker_count=0,
        popup_count=0,
        inline_js_kb=0,
        inline_css_kb=0,
        total_bloat_kb=0,
    )
    low_savings = analyzer._estimate_distilled_metrics(
        original_kb=100,
        total_scripts=0,
        ad_count=0,
        tracker_count=0,
        popup_count=0,
        inline_js_kb=0,
        inline_css_kb=0,
        total_bloat_kb=0,
    )
    high_savings = analyzer._estimate_distilled_metrics(
        original_kb=100,
        total_scripts=100,
        ad_count=100,
        tracker_count=100,
        popup_count=100,
        inline_js_kb=100,
        inline_css_kb=100,
        total_bloat_kb=100,
    )
    floor_twelve = analyzer._estimate_distilled_metrics(
        original_kb=24,
        total_scripts=100,
        ad_count=100,
        tracker_count=100,
        popup_count=100,
        inline_js_kb=100,
        inline_css_kb=100,
        total_bloat_kb=100,
    )
    assert tiny_few == (0.5, 1.1)
    assert tiny_many[0] == pytest.approx(6.2)
    assert low_savings[0] == pytest.approx(92.0)
    assert high_savings[0] == pytest.approx(18.0)
    assert floor_twelve[0] == pytest.approx(12.0)


@pytest.mark.parametrize(
    ("metas", "expected"),
    [
        ([{"property": "og:site_name", "content": "Open Graph"}], ("Open Graph", "site_name")),
        ([{"name": "application-name", "content": "Application"}], ("Application", "application_name")),
        ([{"name": "apple-mobile-web-app-title", "content": "Apple"}], ("Apple", "apple_mobile_web_app_title")),
        ([], ("", "")),
    ],
)
def test_extract_site_name_sources(metas, expected):
    analyzer = SiteAnalyzer()
    doc = analyzer_module.parse_html_metadata("")
    doc.metas = metas
    assert analyzer._extract_site_name(doc) == expected


def test_suggest_app_name_all_strategies():
    analyzer = SiteAnalyzer()
    assert analyzer._suggest_app_name("Title", "example.com", " Site Name ", "custom") == ("Site Name", "custom")
    assert analyzer._suggest_app_name("Title", "example.com", " Site Name ", "") == ("Site Name", "site_name")
    assert analyzer._suggest_app_name("", "www.example.com") == ("example", "host_fallback")
    assert analyzer._suggest_app_name("", "") == ("WebToApp", "host_fallback")
    assert analyzer._suggest_app_name("News | Example | Other", "example.com") == ("Example", "title_host_match")
    assert analyzer._suggest_app_name("First | Second", "unrelated.com") == ("First", "title_first_part")
    assert analyzer._suggest_app_name("Single", "unrelated.com") == ("Single", "title_full")
    long = "X" * 50
    assert analyzer._suggest_app_name(long, "unrelated.com") == ("X" * 40 + "...", "title_full")


def test_text_title_host_and_trim_helpers_cover_edge_cases():
    analyzer = SiteAnalyzer()
    assert analyzer._normalize_text("  A\n -  B | C: ") == "A - B | C"
    assert analyzer._split_title_parts("A | Alpha | alpha | B | Beta") == ["Alpha", "Beta"]
    assert analyzer._split_title_parts("") == []
    assert analyzer._split_title_parts("A") == ["A"]
    assert analyzer._host_label("www.m.mobile.Example.com") == "example"
    assert analyzer._host_label("") == ""
    assert analyzer._part_matches_host("anything", "") is False
    assert analyzer._part_matches_host("Example App", "example") is True
    assert analyzer._part_matches_host("exam", "example") is True
    assert analyzer._part_matches_host("other", "example") is False
    assert analyzer._trim_app_name(" short ") == "short"
    assert analyzer._trim_app_name("word " * 20).endswith("...")


def test_extract_favicon_skips_empty_href_and_falls_back():
    analyzer = SiteAnalyzer()
    doc = analyzer_module.parse_html_metadata(
        '<link rel="icon"><link rel="apple-touch-icon" href="icons/touch.png">'
    )
    assert analyzer._extract_favicon(doc, "https://example.com/path/page") == "https://example.com/path/icons/touch.png"
    empty = analyzer_module.parse_html_metadata('<link rel="stylesheet" href="style.css">')
    assert analyzer._extract_favicon(empty, "https://example.com") == "https://www.google.com/s2/favicons?domain=example.com&sz=64"


def test_favicon_data_url_cache_hit_miss_empty_and_exception(monkeypatch):
    analyzer = SiteAnalyzer()
    cache = DummyCache({"icon:example.com": b"hit"})
    monkeypatch.setattr(analyzer_module, "icon_cache", cache)
    analyzer.icon_distiller = MagicMock()
    assert analyzer._favicon_data_url("https://EXAMPLE.com/path") == "data:image/png;base64,aGl0"
    analyzer.icon_distiller._collect_icon_candidates.assert_not_called()

    cache = DummyCache()
    monkeypatch.setattr(analyzer_module, "icon_cache", cache)
    analyzer.icon_distiller._collect_icon_candidates.return_value = ["candidate"]
    analyzer.icon_distiller._choose_best_icon.return_value = b"chosen"
    assert analyzer._favicon_data_url("https://new.example") == "data:image/png;base64,Y2hvc2Vu"
    assert cache.data["icon:new.example"] == b"chosen"

    cache = DummyCache()
    monkeypatch.setattr(analyzer_module, "icon_cache", cache)
    analyzer.icon_distiller._choose_best_icon.return_value = None
    assert analyzer._favicon_data_url("https://empty.example") == ""
    assert cache.set_calls == []

    cache = MagicMock()
    cache.get.side_effect = RuntimeError("cache failed")
    monkeypatch.setattr(analyzer_module, "icon_cache", cache)
    assert analyzer._favicon_data_url("https://error.example") == ""


def test_tracker_detection_keyword_ad_domain_and_clean():
    analyzer = SiteAnalyzer()
    assert analyzer._is_tracker("https://cdn.example/analytics.js") is True
    assert analyzer._is_tracker("https://doubleclick.net/plain.js") is True
    assert analyzer._is_tracker("https://cdn.example/application.js") is False
