import asyncio
import logging
import socket
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest

from server import config, htmlmeta, logging_util, net
from server.engine import cache as cache_module
from server.engine.cache import TTLCache
from server.engine.recipe import POPULAR_RECIPES, RecipeStore


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ("", None),
        ("https://example.com///", "https://example.com"),
        ("  https://example.com/path/  ", "https://example.com/path"),
    ],
)
def test_public_base_url(monkeypatch, value, expected):
    if value is None:
        monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    else:
        monkeypatch.setenv("PUBLIC_BASE_URL", value)
    assert config.public_base_url() == expected


def test_config_file_discovery_and_ios_helpers(monkeypatch, tmp_path):
    first = tmp_path / "first.pem"
    second = tmp_path / "second.pem"
    second.write_text("pem")
    assert config._first_existing(None, first, second) == str(second)
    assert config._first_existing(None, first) is None

    cert = tmp_path / "cert.pem"
    key = tmp_path / "key.pem"
    chain = tmp_path / "chain.pem"
    for path in (cert, key, chain):
        path.write_text("x")
    monkeypatch.setenv("IOS_CERT_FILE", str(cert))
    monkeypatch.setenv("IOS_KEY_FILE", str(key))
    monkeypatch.setenv("IOS_CHAIN_FILE", str(chain))
    assert config.ios_cert_file() == str(cert)
    assert config.ios_key_file() == str(key)
    assert config.ios_chain_file() == str(chain)
    assert config.ios_signing_available() is True
    key.unlink()
    assert config.ios_signing_available() is False


def test_config_android_strings(monkeypatch):
    monkeypatch.delenv("ANDROID_PACKAGE_PREFIX", raising=False)
    monkeypatch.delenv("ANDROID_KEYSTORE_DIR", raising=False)
    monkeypatch.delenv("ANDROID_TEMPLATE_KEYSTORE_PASSWORD", raising=False)
    assert config.android_package_prefix() == "com.webtoapp"
    assert config.android_keystore_dir().endswith("certs/app-keys")
    assert config.android_template_keystore_password() == "android"

    monkeypatch.setenv("ANDROID_PACKAGE_PREFIX", "  COM.Example.App ")
    monkeypatch.setenv("ANDROID_KEYSTORE_DIR", " /private/keys ")
    monkeypatch.setenv("ANDROID_TEMPLATE_KEYSTORE_PASSWORD", " secret ")
    assert config.android_package_prefix() == "com.example.app"
    assert config.android_keystore_dir() == "/private/keys"
    assert config.android_template_keystore_password() == "secret"


@pytest.mark.parametrize(
    ("function", "env_name", "empty_default", "invalid_default", "low", "low_expected", "high", "high_expected"),
    [
        (config.daily_build_quota_per_device, "DAILY_BUILD_QUOTA", 10, 10, "-3", 0, "21", 21),
        (config.distill_worker_count, "DISTILL_WORKER_COUNT", 2, 2, "0", 1, "9", 4),
        (config.build_parallelism, "BUILD_PARALLELISM", 4, 4, "0", 1, "9", 5),
        (config.icon_cache_ttl_seconds, "ICON_CACHE_TTL_SECONDS", 3600, 3600, "1", 60, "7200", 7200),
        (config.html_cache_ttl_seconds, "HTML_CACHE_TTL_SECONDS", 900, 900, "1", 60, "1800", 1800),
        (config.icon_fetch_timeout, "ICON_FETCH_TIMEOUT", 4.0, 4.0, "0", 1.0, "20", 15.0),
        (config.icon_candidate_limit, "ICON_CANDIDATE_LIMIT", 10, 10, "1", 2, "20", 14),
        (config.recipe_cache_size, "RECIPE_CACHE_SIZE", 512, 512, "0", 1, "900", 900),
        (config.outbound_response_max_bytes, "OUTBOUND_RESPONSE_MAX_BYTES", 4194304, 4194304, "1", 65536, "9000000", 9000000),
        (config.outbound_redirect_limit, "OUTBOUND_REDIRECT_LIMIT", 4, 4, "-2", 0, "8", 8),
        (config.launch_cache_max_age, "LAUNCH_CACHE_MAX_AGE", 60, 60, "-2", 0, "120", 120),
    ],
)
def test_config_numeric_values(
    monkeypatch,
    function,
    env_name,
    empty_default,
    invalid_default,
    low,
    low_expected,
    high,
    high_expected,
):
    monkeypatch.setenv(env_name, "")
    assert function() == empty_default
    monkeypatch.setenv(env_name, "not-a-number")
    assert function() == invalid_default
    monkeypatch.setenv(env_name, low)
    assert function() == low_expected
    monkeypatch.setenv(env_name, high)
    assert function() == high_expected


def test_trusted_proxy_cidrs(monkeypatch):
    monkeypatch.delenv("TRUSTED_PROXY_CIDRS", raising=False)
    assert config.trusted_proxy_cidrs() == ["127.0.0.1/32", "::1/128"]
    monkeypatch.setenv("TRUSTED_PROXY_CIDRS", " 10.0.0.0/8, , 192.0.2.0/24 ")
    assert config.trusted_proxy_cidrs() == ["10.0.0.0/8", "192.0.2.0/24"]
    monkeypatch.setenv("TRUSTED_PROXY_CIDRS", ", ,")
    assert config.trusted_proxy_cidrs() == ["127.0.0.1/32", "::1/128"]


def test_r2_and_cloudflare_config(monkeypatch):
    names = {
        "R2_ACCOUNT_ID": "acct",
        "R2_ACCESS_KEY_ID": "access",
        "R2_SECRET_ACCESS_KEY": "secret",
        "R2_BUCKET": "bucket",
        "R2_PUBLIC_BASE_URL": " https://cdn.example.com/// ",
    }
    for key, value in names.items():
        monkeypatch.setenv(key, value)
    assert config.r2_endpoint_url() == "https://acct.r2.cloudflarestorage.com"
    assert config.r2_access_key_id() == "access"
    assert config.r2_secret_access_key() == "secret"
    assert config.r2_bucket() == "bucket"
    assert config.r2_public_base_url() == "https://cdn.example.com"
    assert config.r2_configured() is True

    for missing in names:
        for key, value in names.items():
            monkeypatch.setenv(key, value)
        monkeypatch.setenv(missing, "  ")
        assert config.r2_configured() is False
    # The endpoint helper depends only on the account id: blanking that one
    # disables it, while the others only affect r2_configured().
    monkeypatch.setenv("R2_ACCOUNT_ID", "  ")
    assert config.r2_endpoint_url() is None
    monkeypatch.setenv("R2_ACCOUNT_ID", "acct")
    monkeypatch.delenv("R2_PUBLIC_BASE_URL", raising=False)
    assert config.r2_public_base_url() is None

    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", " token ")
    monkeypatch.setenv("CLOUDFLARE_ZONE_ID", " zone ")
    assert config.cloudflare_api_token() == "token"
    assert config.cloudflare_zone_id() == "zone"
    assert config.cloudflare_purge_available() is True
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "")
    assert config.cloudflare_purge_available() is False
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "token")
    monkeypatch.setenv("CLOUDFLARE_ZONE_ID", "")
    assert config.cloudflare_purge_available() is False


@pytest.mark.parametrize("url", ["", "ftp://example.com", "http:///path", "https://"])
def test_normalized_http_url_rejects_non_absolute_urls(url):
    with pytest.raises(net.UnsafeOutboundTarget, match="absolute"):
        net._normalized_http_url(url)


@pytest.mark.parametrize("url", ["https://user@example.com", "https://user:pw@example.com"])
def test_normalized_http_url_rejects_credentials(url):
    with pytest.raises(net.UnsafeOutboundTarget, match="credentials"):
        net._normalized_http_url(url)


def test_ports_and_normalization():
    assert net._normalized_http_url("  https://example.com/a  ") == "https://example.com/a"
    assert net._port_for(net.urlparse("http://example.com")) == 80
    assert net._port_for(net.urlparse("https://example.com")) == 443
    assert net._port_for(net.urlparse("https://example.com:8443")) == 8443


class _FakeIP:
    def __init__(self, true_name=None):
        for name in ("is_private", "is_loopback", "is_link_local", "is_multicast", "is_reserved", "is_unspecified"):
            setattr(self, name, name == true_name)


@pytest.mark.parametrize(
    ("true_name", "expected"),
    [(None, False)]
    + [(name, True) for name in ("is_private", "is_loopback", "is_link_local", "is_multicast", "is_reserved", "is_unspecified")],
)
def test_is_forbidden_ip_checks_every_category(monkeypatch, true_name, expected):
    monkeypatch.setattr(net.ipaddress, "ip_address", lambda _address: _FakeIP(true_name))
    assert net._is_forbidden_ip("ignored") is expected


def test_validate_public_http_url_resolution(monkeypatch):
    calls = []

    def public_getaddrinfo(host, port, type):
        calls.append((host, port, type))
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port)),
        ]

    monkeypatch.setattr(net.socket, "getaddrinfo", public_getaddrinfo)
    assert net.validate_public_http_url("https://example.com") == "https://example.com"
    assert calls == [("example.com", 443, socket.SOCK_STREAM)]

    monkeypatch.setattr(net.socket, "getaddrinfo", lambda *a, **k: [])
    with pytest.raises(net.UnsafeOutboundTarget, match="does not resolve"):
        net.validate_public_http_url("http://example.com")

    monkeypatch.setattr(
        net.socket,
        "getaddrinfo",
        lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 80))],
    )
    with pytest.raises(net.UnsafeOutboundTarget, match="non-public"):
        net.validate_public_http_url("http://example.com")


def test_async_validation_and_redirect_target(monkeypatch):
    monkeypatch.setattr(net, "validate_public_http_url", lambda value: "validated:" + value)
    assert asyncio.run(net.avalidate_public_http_url("https://example.com")) == "validated:https://example.com"
    assert net.redirect_target("https://example.com/a/", "../b") == "validated:https://example.com/b"
    with pytest.raises(net.UnsafeOutboundTarget, match="missing"):
        net.redirect_target("https://example.com", "  ")


class _SyncResponse:
    def __init__(self, chunks=(), headers=None, status_code=200, error=None):
        self._chunks = list(chunks)
        self.headers = headers or {}
        self.status_code = status_code
        self.error = error

    def iter_bytes(self):
        return iter(self._chunks)

    def raise_for_status(self):
        if self.error:
            raise self.error

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class _AsyncResponse(_SyncResponse):
    async def aiter_bytes(self):
        for chunk in self._chunks:
            yield chunk

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


def test_read_limited_response_all_header_and_stream_paths():
    assert net.read_limited_response(_SyncResponse([b"ab", b"c"], {"content-length": "3"}), 3) == b"abc"
    assert net.read_limited_response(_SyncResponse([b"ok"], {"content-length": "invalid"}), 2) == b"ok"
    assert net.read_limited_response(_SyncResponse([], {}), 2) == b""
    with pytest.raises(ValueError, match="too large"):
        net.read_limited_response(_SyncResponse([], {"content-length": "3"}), 2)
    with pytest.raises(ValueError, match="too large"):
        net.read_limited_response(_SyncResponse([b"ab", b"c"], {}), 2)


def test_aread_limited_response_all_header_and_stream_paths():
    assert asyncio.run(net.aread_limited_response(_AsyncResponse([b"a", b"b"], {"content-length": "2"}), 2)) == b"ab"
    assert asyncio.run(net.aread_limited_response(_AsyncResponse([b"ok"], {"content-length": "bad"}), 2)) == b"ok"
    assert asyncio.run(net.aread_limited_response(_AsyncResponse([], {}), 2)) == b""
    with pytest.raises(ValueError, match="too large"):
        asyncio.run(net.aread_limited_response(_AsyncResponse([], {"content-length": "9"}), 2))
    with pytest.raises(ValueError, match="too large"):
        asyncio.run(net.aread_limited_response(_AsyncResponse([b"abc"], {}), 2))


class _FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []
        self.closed = False

    def stream(self, method, url, **kwargs):
        self.requests.append((method, url))
        return self.responses.pop(0)

    def close(self):
        self.closed = True


def test_fetch_public_url_bytes_redirect_success_and_options(monkeypatch):
    client = _FakeClient(
        [
            _SyncResponse(headers={"location": "/next"}, status_code=302),
            _SyncResponse([b"done"], status_code=200),
        ]
    )
    constructor = Mock(return_value=client)
    monkeypatch.setattr(net.httpx, "Client", constructor)
    monkeypatch.setattr(net, "validate_public_http_url", lambda value: value)
    monkeypatch.setattr(net, "pinned_targets", lambda value: [(value, {}, None)])
    monkeypatch.setattr(net, "redirect_target", lambda current, location: "https://example.com/next")
    assert net.fetch_public_url_bytes(
        "https://example.com/start",
        timeout=20,
        headers={"X-Test": "1"},
        max_bytes=8,
        max_redirects=1,
    ) == b"done"
    assert client.requests == [("GET", "https://example.com/start"), ("GET", "https://example.com/next")]
    assert client.closed is True
    kwargs = constructor.call_args.kwargs
    assert kwargs["follow_redirects"] is False
    assert kwargs["headers"] == {"X-Test": "1"}
    assert kwargs["timeout"].connect == 10.0


def test_fetch_public_url_bytes_defaults_and_too_many_redirects(monkeypatch):
    monkeypatch.setattr(net, "validate_public_http_url", lambda value: value)
    monkeypatch.setattr(net, "pinned_targets", lambda value: [(value, {}, None)])
    monkeypatch.setattr(net.config, "outbound_response_max_bytes", lambda: 5)
    monkeypatch.setattr(net.config, "outbound_redirect_limit", lambda: 1)

    success_client = _FakeClient([_SyncResponse([b"ok"])])
    constructor = Mock(return_value=success_client)
    monkeypatch.setattr(net.httpx, "Client", constructor)
    assert net.fetch_public_url_bytes("http://example.com", timeout=2) == b"ok"
    assert constructor.call_args.kwargs["headers"] is None
    assert constructor.call_args.kwargs["timeout"].connect == 2.0

    redirect_client = _FakeClient(
        [
            _SyncResponse(status_code=301, headers={"location": "/1"}),
            _SyncResponse(status_code=308, headers={"location": "/2"}),
        ]
    )
    monkeypatch.setattr(net.httpx, "Client", Mock(return_value=redirect_client))
    monkeypatch.setattr(net, "redirect_target", lambda current, location: current + location)
    with pytest.raises(httpx.TooManyRedirects):
        net.fetch_public_url_bytes("http://example.com", timeout=1)
    assert redirect_client.closed is True


def test_html_metadata_parser_full_behavior():
    html = """
    <html><head>
      <TITLE>  Main &amp; More </TITLE>
      <meta NAME="description" CONTENT=" desc ">
      <meta property="og:title" content=" Social ">
      <meta name="empty" content>
      <link rel="stylesheet icon" href=" /icon.png ">
      <link rel="icon" href="">
      <link rel="stylesheet" href="/style.css">
      <script src=" /app.js ">ignored</script>
      <script>one &amp; two</script>
      <style>a { color: red }</style>
    </head></html>
    """
    doc = htmlmeta.parse_html_metadata(html)
    assert doc.title == "Main & More"
    assert doc.meta_content("", None, " DESCRIPTION ") == "desc"
    assert doc.meta_content("og:title") == "Social"
    assert doc.meta_content("missing") == ""
    assert [attrs["href"] for attrs in doc.link_attrs_by_rel("", None, "ICON")] == [" /icon.png "]
    assert list(doc.link_attrs_by_rel("manifest")) == []
    assert doc.script_srcs == ["/app.js"]
    # html.parser treats script/style bodies as CDATA: character references are
    # NOT decoded there, so the size counts the raw source bytes.
    assert doc.inline_script_size == len("one &amp; two")
    assert doc.inline_style_size == len("a { color: red }")
    assert htmlmeta.parse_html_metadata(None).title == ""


def test_html_parser_direct_state_transitions():
    parser = htmlmeta.HtmlMetadataParser()
    parser.handle_starttag("TITLE", [])
    parser.handle_starttag("script", [("src", None)])
    parser.handle_starttag("STYLE", [])
    parser.handle_data("x")
    assert parser.title == "x"
    assert parser.inline_script_size == 1
    assert parser.inline_style_size == 1
    parser.handle_endtag("TITLE")
    parser.handle_endtag("SCRIPT")
    parser.handle_endtag("STYLE")
    parser.handle_endtag("div")
    parser.handle_starttag("div", [])
    parser.handle_data("ignored")
    assert parser.title == "x"


def test_setup_logging_levels_and_idempotence(monkeypatch):
    root = logging.getLogger()
    old_handlers = list(root.handlers)
    old_level = root.level
    old_configured = logging_util._CONFIGURED
    try:
        logging_util._CONFIGURED = False
        logging_util.setup_logging("debug")
        assert root.level == logging.DEBUG
        handlers = list(root.handlers)
        logging_util.setup_logging("ERROR")
        assert root.handlers == handlers
        assert root.level == logging.DEBUG

        logging_util._CONFIGURED = False
        logging_util.setup_logging("not-a-level")
        assert root.level == logging.INFO
    finally:
        root.handlers[:] = old_handlers
        root.setLevel(old_level)
        logging_util._CONFIGURED = old_configured


def test_log_event_success_and_fallback(monkeypatch, capsys):
    monkeypatch.setattr(logging_util.time, "gmtime", lambda: "gmt")
    monkeypatch.setattr(logging_util.time, "strftime", lambda fmt, value: "2026-01-01T00:00:00Z")
    logging_util.log_event("built", app="a1", skipped=None)
    output = capsys.readouterr().out.strip()
    assert '"event": "built"' in output
    assert '"app": "a1"' in output
    assert "skipped" not in output

    monkeypatch.setattr(logging_util.json, "dumps", Mock(side_effect=TypeError("bad")))
    logging_util.log_event("fallback", value=object())
    assert capsys.readouterr().out.startswith("fallback ")


def test_get_logger_calls_setup(monkeypatch):
    setup = Mock()
    sentinel = object()
    original_get_logger = logging.getLogger

    def fake_get_logger(name=None):
        return original_get_logger() if name is None else sentinel

    monkeypatch.setattr(logging_util, "setup_logging", setup)
    monkeypatch.setattr(logging_util.logging, "getLogger", fake_get_logger)
    assert logging_util.get_logger("worker") is sentinel
    setup.assert_called_once_with()


def test_ttl_cache_initialization_hits_misses_expiry_eviction_and_stats(monkeypatch):
    cache = TTLCache(max_size=0, ttl_seconds=0)
    assert cache.max_size == 1
    assert cache.ttl_seconds == 1.0

    times = iter([10.0, 10.5, 12.0, 20.0, 20.0, 20.0, 20.0])
    monkeypatch.setattr(cache_module.time, "time", lambda: next(times))
    cache.set("a", 1)
    assert cache.get("a") == 1
    assert cache.get("a") is None
    assert cache.get("missing") is None
    cache.set("b", 2)
    cache.set("c", 3)
    assert cache.get("b") is None
    stats = cache.stats()
    assert stats == {
        "size": 1,
        "max_size": 1,
        "ttl_seconds": 1.0,
        "hits": 1,
        "misses": 3,
    }


def test_ttl_cache_positive_constructor_and_update_lru(monkeypatch):
    monkeypatch.setattr(cache_module.time, "time", lambda: 1.0)
    cache = TTLCache(max_size=2, ttl_seconds=5)
    cache.set("a", 1)
    cache.set("b", 2)
    assert cache.get("a") == 1
    cache.set("c", 3)
    assert cache.get("b") is None
    cache.set("a", 4)
    assert cache.get("a") == 4


def test_recipe_store_popular_and_lookup():
    store = RecipeStore()
    assert store.get_popular() is POPULAR_RECIPES
    assert store.get_by_id("gh-dark")["name"] == "GitHub 增强版"
    assert store.get_by_id("missing") is None


def test_pinned_request_preserves_host_and_sni():
    url, headers, ext = net._pinned_request("https://example.com:8443/p?q=1", "93.184.216.34")
    assert url == "https://93.184.216.34:8443/p?q=1"
    assert headers == {"Host": "example.com:8443"}
    assert ext == {"sni_hostname": "example.com"}

    url, headers, ext = net._pinned_request("http://example.com/a", "2001:db8::1")
    assert url == "http://[2001:db8::1]/a"
    assert headers == {"Host": "example.com"}
    assert ext is None


def test_pinned_targets_only_return_public_ips(monkeypatch):
    def fake_getaddrinfo(host, port, type):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.35", port)),
        ]

    monkeypatch.setattr(net.socket, "getaddrinfo", fake_getaddrinfo)
    targets = net.pinned_targets("https://example.com/x")
    assert [t[0] for t in targets] == [
        "https://93.184.216.34/x",
        "https://93.184.216.35/x",
    ]

    monkeypatch.setattr(
        net.socket,
        "getaddrinfo",
        lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("169.254.169.254", 80))],
    )
    with pytest.raises(net.UnsafeOutboundTarget):
        net.pinned_targets("http://example.com")
