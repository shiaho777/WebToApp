"""
Server-wide configuration loaded from environment variables.

For iOS "免签" (signed .mobileconfig) support, set the following env vars
(or create certs/ios-cert.pem, certs/ios-key.pem, certs/ios-chain.pem files):

    IOS_CERT_FILE   - PEM-encoded signing certificate (the leaf cert for your domain)
    IOS_KEY_FILE    - PEM-encoded private key
    IOS_CHAIN_FILE  - (optional) intermediate cert chain; greatly improves trust

    PUBLIC_BASE_URL - public URL of this server (e.g. https://example.com).
                      Used as the Web Clip target so target URL can be swapped
                      later without re-installing the profile.
                      If unset, the request Host header is used at build time.
"""

import os
from pathlib import Path
from typing import Optional

_ROOT = Path(__file__).parent.parent
_DEFAULT_CERT_DIR = _ROOT / "certs"


def _first_existing(*paths):
    for p in paths:
        if p and os.path.isfile(p):
            return str(p)
    return None


def ios_cert_file() -> Optional[str]:
    return _first_existing(
        os.environ.get("IOS_CERT_FILE"),
        _DEFAULT_CERT_DIR / "ios-cert.pem",
    )


def ios_key_file() -> Optional[str]:
    return _first_existing(
        os.environ.get("IOS_KEY_FILE"),
        _DEFAULT_CERT_DIR / "ios-key.pem",
    )


def ios_chain_file() -> Optional[str]:
    return _first_existing(
        os.environ.get("IOS_CHAIN_FILE"),
        _DEFAULT_CERT_DIR / "ios-chain.pem",
    )


def ios_signing_available() -> bool:
    """True when both certificate and private key are configured and readable."""
    return bool(ios_cert_file() and ios_key_file())


def public_base_url() -> Optional[str]:
    """Return the configured public base URL, without trailing slash. May be None."""
    url = os.environ.get("PUBLIC_BASE_URL", "").strip()
    return url.rstrip("/") if url else None


def android_package_prefix() -> str:
    """Return the default Android package prefix."""
    prefix = os.environ.get("ANDROID_PACKAGE_PREFIX", "").strip().lower()
    return prefix or "com.webtoapp"


def android_keystore_dir() -> str:
    """Directory holding per-app Android signing keystores.

    Each generated app gets its own keystore here (keyed by app_id) so that
    no two apps share a signing certificate — this avoids the "test key"
    family being flagged en masse by mobile AV engines. Override the location
    with ANDROID_KEYSTORE_DIR; defaults to ``certs/app-keys`` (gitignored).

    Keep this OUTSIDE any publicly served directory. These files are private
    signing keys; leaking one lets an attacker forge updates for that app.
    """
    custom = os.environ.get("ANDROID_KEYSTORE_DIR", "").strip()
    if custom:
        return custom
    return str(_DEFAULT_CERT_DIR / "app-keys")


def android_template_keystore_password() -> str:
    """Password for the internal template-build keystore.

    This keystore only signs the throwaway base template APK (which is then
    re-signed per-app), so it is not security-critical, but we still avoid the
    hard-coded weak default by allowing an env override.
    """
    return os.environ.get("ANDROID_TEMPLATE_KEYSTORE_PASSWORD", "").strip() or "android"


def daily_build_quota_per_device() -> int:
    """Per device-fingerprint daily build quota. 0 disables quota."""
    try:
        return max(0, int(os.environ.get("DAILY_BUILD_QUOTA", "10").strip() or "10"))
    except ValueError:
        return 10


def distill_worker_count() -> int:
    try:
        return max(1, min(4, int(os.environ.get("DISTILL_WORKER_COUNT", "2").strip() or "2")))
    except ValueError:
        return 2


def build_parallelism() -> int:
    try:
        return max(1, min(5, int(os.environ.get("BUILD_PARALLELISM", "4").strip() or "4")))
    except ValueError:
        return 4


def icon_cache_ttl_seconds() -> int:
    try:
        return max(60, int(os.environ.get("ICON_CACHE_TTL_SECONDS", "3600").strip() or "3600"))
    except ValueError:
        return 3600


def html_cache_ttl_seconds() -> int:
    try:
        return max(60, int(os.environ.get("HTML_CACHE_TTL_SECONDS", "900").strip() or "900"))
    except ValueError:
        return 900


def icon_fetch_timeout() -> float:
    try:
        return max(1.0, min(15.0, float(os.environ.get("ICON_FETCH_TIMEOUT", "4").strip() or "4")))
    except ValueError:
        return 4.0


def icon_candidate_limit() -> int:
    # Default 10: a blocked-page host yields 6 well-known paths + 4 service
    # fallbacks; a smaller limit truncates the services out of the race and
    # foreign sites end up icon-less (see #71).
    try:
        return max(2, min(14, int(os.environ.get("ICON_CANDIDATE_LIMIT", "10").strip() or "10")))
    except ValueError:
        return 10


def recipe_cache_size() -> int:
    try:
        return max(1, int(os.environ.get("RECIPE_CACHE_SIZE", "512").strip() or "512"))
    except ValueError:
        return 512


def outbound_response_max_bytes() -> int:
    try:
        return max(65536, int(os.environ.get("OUTBOUND_RESPONSE_MAX_BYTES", "4194304").strip() or "4194304"))
    except ValueError:
        return 4194304


def outbound_redirect_limit() -> int:
    try:
        return max(0, int(os.environ.get("OUTBOUND_REDIRECT_LIMIT", "4").strip() or "4"))
    except ValueError:
        return 4


def trusted_proxy_cidrs() -> list[str]:
    raw = os.environ.get("TRUSTED_PROXY_CIDRS", "").strip()
    if not raw:
        return ["127.0.0.1/32", "::1/128"]
    values = []
    for chunk in raw.split(","):
        token = chunk.strip()
        if token:
            values.append(token)
    return values or ["127.0.0.1/32", "::1/128"]


def metrics_token() -> str:
    """Shared secret for GET /api/metrics.

    When set, callers must present it via ``Authorization: Bearer <token>``
    or ``X-Metrics-Token``. When unset, the endpoint falls back to allowing
    only loopback callers instead of being publicly readable (it discloses
    filesystem paths, queue depths and keystore stats).
    """
    return os.environ.get("METRICS_TOKEN", "").strip()


# ---------- HTML-to-App uploads ----------
#
# Uploaded HTML content (.html single file or .zip site bundle) is hosted by
# this server under generated/<app_id>/site/ and served via /a/{id}/site/.
# These caps bound disk usage and the zip-decompression attack surface.

def html_upload_max_bytes() -> int:
    """Maximum accepted request body for an HTML upload (compressed zip size
    counts against this too). Default 10 MB."""
    try:
        return max(64 * 1024, int(os.environ.get("HTML_UPLOAD_MAX_BYTES", str(10 * 1024 * 1024)).strip()))
    except ValueError:
        return 10 * 1024 * 1024


def html_site_max_uncompressed_bytes() -> int:
    """Maximum total uncompressed size of an extracted zip site bundle. Default 20 MB."""
    try:
        return max(64 * 1024, int(os.environ.get("HTML_SITE_MAX_UNCOMPRESSED_BYTES", str(20 * 1024 * 1024)).strip()))
    except ValueError:
        return 20 * 1024 * 1024


def html_site_max_file_count() -> int:
    """Maximum number of files inside an uploaded zip site bundle. Default 500."""
    try:
        return max(1, int(os.environ.get("HTML_SITE_MAX_FILE_COUNT", "500").strip() or "500"))
    except ValueError:
        return 500


def site_public_base_url() -> str:
    """Public origin that serves uploaded HTML-app content (/a/<id>/site/).

    When set, uploaded pages execute on this isolated host instead of the API
    origin: their JS then cannot invoke the API with the visitor's cookies
    attached (cross-site -> SameSite=Lax cookies are not sent), closing the
    same-origin hole in issue #20. The main origin 301-redirects /a/<id>/site/
    requests here. Empty = serve from the main origin (legacy behaviour).
    """
    return os.environ.get("SITE_PUBLIC_BASE_URL", "").strip().rstrip("/")


def site_origin_key() -> str:
    """Shared secret that lets the site gateway skip the sandbox redirect.

    The reverse proxy in front of ``SITE_PUBLIC_BASE_URL`` (e.g. a Cloudflare
    Worker) presents this in ``X-Site-Origin-Key``; the redirect in
    ``serve_app_site`` is skipped only for matching requests, so content is
    still served to the gateway while every direct main-origin request is
    pushed to the sandbox origin.
    """
    return os.environ.get("SITE_ORIGIN_KEY", "").strip()


def html_export_max_bytes() -> int:
    """Maximum total site size embedded in an exported history snapshot.
    Larger sites are skipped from the export and flagged instead. Default 2 MB."""
    try:
        return max(0, int(os.environ.get("HTML_EXPORT_MAX_BYTES", str(2 * 1024 * 1024)).strip()))
    except ValueError:
        return 2 * 1024 * 1024


# ---------- Cloudflare R2 (S3-compatible) ----------
#
# Set ALL of the following to enable R2 offload. Once configured, every
# build's APK/ZIP/mobileconfig is uploaded to R2 after generation, and
# /a/{id}/download/{platform} 302-redirects to the public CDN URL — so the
# origin server stops paying for download bandwidth.
#
#   R2_ACCOUNT_ID         Cloudflare account ID (URL-safe, hex)
#   R2_ACCESS_KEY_ID      API token's S3 access key
#   R2_SECRET_ACCESS_KEY  API token's S3 secret
#   R2_BUCKET             Bucket name
#   R2_PUBLIC_BASE_URL    Public URL prefix, e.g. https://files.example.com
#                         or https://pub-xxxxxxxx.r2.dev. Trailing slash optional.

def r2_endpoint_url() -> Optional[str]:
    account_id = os.environ.get("R2_ACCOUNT_ID", "").strip()
    if not account_id:
        return None
    return f"https://{account_id}.r2.cloudflarestorage.com"


def r2_access_key_id() -> str:
    return os.environ.get("R2_ACCESS_KEY_ID", "").strip()


def r2_secret_access_key() -> str:
    return os.environ.get("R2_SECRET_ACCESS_KEY", "").strip()


def r2_bucket() -> str:
    return os.environ.get("R2_BUCKET", "").strip()


def r2_public_base_url() -> Optional[str]:
    base = os.environ.get("R2_PUBLIC_BASE_URL", "").strip()
    return base.rstrip("/") if base else None


def r2_configured() -> bool:
    return bool(
        r2_endpoint_url()
        and r2_access_key_id()
        and r2_secret_access_key()
        and r2_bucket()
        and r2_public_base_url()
    )


# ---------- Cloudflare API (cache purge) ----------
#
# Optional. When set, PATCH /api/app/{id}/url calls the CF purge API to
# evict the cached /launch redirect immediately. Without it, edge caches
# expire on their own after ``launch_cache_max_age`` seconds.
#
#   CLOUDFLARE_API_TOKEN  Scoped token with "Zone Cache Purge" permission
#   CLOUDFLARE_ZONE_ID    Target zone ID

def cloudflare_api_token() -> str:
    return os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()


def cloudflare_zone_id() -> str:
    return os.environ.get("CLOUDFLARE_ZONE_ID", "").strip()


def cloudflare_purge_available() -> bool:
    return bool(cloudflare_api_token() and cloudflare_zone_id())


def launch_cache_max_age() -> int:
    """Seconds the iOS /launch 302 may be cached at the CDN edge.

    Lower = faster URL hot-swap propagation, higher = less origin traffic.
    Default 60s strikes a reasonable balance.
    """
    try:
        return max(0, int(os.environ.get("LAUNCH_CACHE_MAX_AGE", "60").strip() or "60"))
    except ValueError:
        return 60


def admin_token() -> str:
    """Bearer/X-Admin-Token for moderation endpoints (comment deletion).
    Empty = admin operations disabled."""
    return os.environ.get("ADMIN_TOKEN", "").strip()
