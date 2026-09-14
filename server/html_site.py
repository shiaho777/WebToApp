"""
HTML site staging & serving helpers for the HTML-to-App feature.

An "HTML app" bundles its content on this server: the upload (a single
``.html`` file or a ``.zip`` site bundle) is validated, extracted under
``generated/<app_id>/site/`` and later served from ``/a/{app_id}/site/...``.
Every validation here treats the upload as hostile input — zip-slip,
zip bombs and oversized bundles must be rejected before anything is
written to disk.
"""

import base64
import hashlib
import io
import re
import shutil
import zipfile
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import unquote, urlparse

from server import config
from server.htmlmeta import parse_html_metadata

INDEX_NAME = "index.html"

# Entries that are archive junk rather than site content.
_JUNK_SEGMENTS = {"__MACOSX", ".DS_Store", "Thumbs.db"}

_MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".xml": "application/xml; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
    ".otf": "font/otf",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".wasm": "application/wasm",
    ".pdf": "application/pdf",
}

# zip-bomb heuristic: reject entries whose compression ratio exceeds this
# once the uncompressed size is large enough for the ratio to be meaningful.
_MAX_COMPRESSION_RATIO = 100
_RATIO_MIN_FILE_SIZE = 1024 * 1024


class HtmlUploadError(ValueError):
    """Upload failed validation. The message is user-facing (translated client-side by key where possible)."""


def _normalized_entry_name(raw: str) -> str:
    """Normalize a zip entry name; return "" for entries to skip, raise on unsafe ones."""
    name = raw.replace("\\", "/")
    while name.startswith("./"):
        name = name[2:]
    if not name or name.endswith("/"):
        return ""  # directory entry
    if name.startswith("/"):
        raise HtmlUploadError("Archive contains an absolute path")
    if re.match(r"^[A-Za-z]:", name):
        raise HtmlUploadError("Archive contains a drive-qualified path")
    parts = name.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise HtmlUploadError("Archive contains an unsafe path")
    if any(part in _JUNK_SEGMENTS for part in parts):
        return ""
    return "/".join(parts)


def _read_capped(zin: zipfile.ZipFile, info: zipfile.ZipInfo, cap: int) -> bytes:
    """Read one entry, enforcing the advertised size cap even if the local
    header lies about it."""
    chunks = []
    total = 0
    with zin.open(info, "r") as stream:
        while True:
            chunk = stream.read(64 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > cap:
                raise HtmlUploadError("Archive is larger than allowed once extracted")
            chunks.append(chunk)
    return b"".join(chunks)


def _extract_zip(data: bytes, dest: Path) -> List[str]:
    """Extract an in-memory zip into ``dest`` (created, must not exist yet).

    Applies zip-slip / bomb / count defenses and flattens a single shared
    top-level directory. Returns the written relative paths.
    """
    max_files = config.html_site_max_file_count()
    max_bytes = config.html_site_max_uncompressed_bytes()
    try:
        zin = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise HtmlUploadError("File is not a valid zip archive") from exc
    with zin:
        infos = zin.infolist()
        if len(infos) > max_files * 2 + 16:
            raise HtmlUploadError(f"Archive has too many entries (max {max_files} files)")
        entries: Dict[str, bytes] = {}
        total = 0
        for info in infos:
            if info.flag_bits & 0x1:
                raise HtmlUploadError("Encrypted archive entries are not supported")
            name = _normalized_entry_name(info.filename)
            if not name:
                continue
            if info.file_size > max_bytes:
                raise HtmlUploadError("Archive is larger than allowed once extracted")
            if (
                info.file_size > _RATIO_MIN_FILE_SIZE
                and info.compress_size > 0
                and info.file_size / info.compress_size > _MAX_COMPRESSION_RATIO
            ):
                raise HtmlUploadError("Archive looks like a zip bomb")
            total += info.file_size
            if total > max_bytes:
                raise HtmlUploadError("Archive is larger than allowed once extracted")
            entries[name] = _read_capped(zin, info, max_bytes)
        if len(entries) > max_files:
            raise HtmlUploadError(f"Archive has too many files (max {max_files})")
        if not entries:
            raise HtmlUploadError("Archive is empty")
        entries = _flatten_single_root(entries)
        if INDEX_NAME not in entries:
            raise HtmlUploadError(f"Archive must contain {INDEX_NAME} at its root")
        dest.mkdir(parents=True, exist_ok=False)
        for name, blob in sorted(entries.items()):
            target = _contained_path(dest, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(blob)
        return sorted(entries)


class _BytesReader(io.BytesIO):
    """zipfile needs a file-like object; plain BytesIO already qualifies."""


def _flatten_single_root(entries: Dict[str, bytes]) -> Dict[str, bytes]:
    """``mysite/index.html`` … → ``index.html`` … when every entry lives under
    one shared top-level directory and nothing sits at the root."""
    first_parts = {name.split("/", 1)[0] for name in entries}
    if len(first_parts) != 1:
        return entries
    if not all("/" in name for name in entries):
        return entries  # a file at the root level: keep the layout as-is
    prefix = next(iter(first_parts)) + "/"
    return {name[len(prefix):]: blob for name, blob in entries.items()}


def _contained_path(root: Path, rel: str) -> Path:
    """Join and verify the result stays inside ``root`` (defense in depth for
    path traversal; entries are pre-validated but callers may pass raw input)."""
    candidate = (root / rel).resolve()
    root_resolved = root.resolve()
    if candidate != root_resolved and root_resolved not in candidate.parents:
        raise HtmlUploadError("Path escapes the site directory")
    return candidate


def _hash_content(entries: Dict[str, bytes]) -> str:
    digest = hashlib.sha256()
    for name in sorted(entries):
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(entries[name]).digest())
    return digest.hexdigest()


def validate_and_extract(data: bytes, filename: str, dest: Path) -> dict:
    """Validate an HTML upload and write it to ``dest`` (must not exist yet).

    Returns ``{"content_hash", "index_name", "file_count", "total_bytes"}``.
    Raises :class:`HtmlUploadError` with a user-facing message; nothing is
    written to disk when validation fails.
    """
    if not data:
        raise HtmlUploadError("Uploaded file is empty")
    if len(data) > config.html_upload_max_bytes():
        raise HtmlUploadError("Uploaded file is too large")

    suffix = Path(str(filename or "")).suffix.lower()
    if suffix in (".html", ".htm"):
        dest.mkdir(parents=True, exist_ok=False)
        (dest / INDEX_NAME).write_bytes(data)
        entries = {INDEX_NAME: data}
        return {
            "content_hash": _hash_content(entries),
            "index_name": INDEX_NAME,
            "file_count": 1,
            "total_bytes": len(data),
        }
    if suffix == ".zip":
        names = _extract_zip(data, dest)
        entries = {name: (dest / name).read_bytes() for name in names}
        return {
            "content_hash": _hash_content(entries),
            "index_name": INDEX_NAME,
            "file_count": len(entries),
            "total_bytes": sum(len(blob) for blob in entries.values()),
        }
    raise HtmlUploadError("Only .html, .htm and .zip uploads are supported")


def app_id_for(content_hash: str, name: str) -> str:
    """Stable app id for an HTML upload — mirrors the URL flow's md5(url:name).
    Same content + same name rebuilds the same app (version bump, keystore reuse)."""
    return hashlib.md5(f"{content_hash}:{name}".encode()).hexdigest()[:8]


def stage_html_app(data: bytes, filename: str, name: str, apps_dir: Path) -> dict:
    """Stage an upload under ``apps_dir/<app_id>/site/`` and return staging info.

    On validation failure nothing is left behind. On success a pre-existing
    site directory (a rebuild of the same app) is replaced atomically enough
    for our purposes: extract to a sibling temp dir, then swap.
    """
    fallback_name = re.sub(r"[^A-Za-z0-9._-]+", " ", Path(str(filename or "app")).stem).strip() or "app"
    clean_name = str(name or "").strip() or fallback_name
    probe = apps_dir / f".stage-{hashlib.md5(data).hexdigest()[:12]}"
    if probe.exists():
        shutil.rmtree(probe, ignore_errors=True)
    try:
        info = validate_and_extract(data, filename, probe)
        app_id = app_id_for(info["content_hash"], clean_name)
        site_dir = apps_dir / app_id / "site"
        if site_dir.exists():
            shutil.rmtree(site_dir)
        site_dir.parent.mkdir(parents=True, exist_ok=True)
        probe.replace(site_dir)
        info.update({"app_id": app_id, "name": clean_name, "site_dir": site_dir})
        return info
    except Exception:
        shutil.rmtree(probe, ignore_errors=True)
        raise


_VIEWPORT_META_RE = re.compile(
    r'<meta[^>]*\bname\s*=\s*["\']?viewport["\']?[^>]*>', re.IGNORECASE)
_HEAD_OPEN_RE = re.compile(r'<head[^>]*>', re.IGNORECASE)
_CONTENT_ATTR_RE = re.compile(r'content\s*=\s*["\']([^"\']*)["\']', re.IGNORECASE)
_VIEWPORT_KEYS = {"width", "initial-scale", "minimum-scale", "maximum-scale",
                  "user-scalable", "viewport-fit"}
_APP_VIEWPORT = ("width=device-width,initial-scale=1,maximum-scale=1,"
                 "user-scalable=no,viewport-fit=cover")


def appify_index_html(data: bytes) -> bytes:
    """Patch a hosted page's viewport so it presents like an installed app:
    edge-to-edge under iOS chrome and no browser-style pinch zoom. Other
    viewport keys are preserved; everything else is untouched."""
    try:
        html = data.decode("utf-8")
    except UnicodeDecodeError:
        return data
    head = _HEAD_OPEN_RE.search(html)
    if not head:
        return data
    head_close = html.lower().find("</head>", head.end())
    scope = head_close if head_close != -1 else min(len(html), head.end() + 8192)
    region = html[head.end():scope]
    m = _VIEWPORT_META_RE.search(region)
    if m:
        content_m = _CONTENT_ATTR_RE.search(m.group(0))
        extra = []
        if content_m:
            for piece in content_m.group(1).split(","):
                piece = piece.strip()
                if piece and piece.split("=", 1)[0].strip().lower() not in _VIEWPORT_KEYS:
                    extra.append(piece)
        content = _APP_VIEWPORT + ("," + ",".join(extra) if extra else "")
        meta = f'<meta name="viewport" content="{content}">'
        html = html[:head.end()] + region[:m.start()] + meta + region[m.end():] + html[scope:]
    else:
        meta = f'<meta name="viewport" content="{_APP_VIEWPORT}">'
        html = html[:head.end()] + meta + html[head.end():]
    return html.encode("utf-8")


def resolve_site_file(site_dir: Path, rel_path: str) -> Optional[Path]:
    """Resolve a served path inside a site dir; directories fall back to
    ``index.html``. Returns None when the path does not exist or escapes."""
    cleaned = str(rel_path or "").lstrip("/")
    if not cleaned or "\x00" in cleaned:
        cleaned = INDEX_NAME
    try:
        candidate = _contained_path(site_dir, cleaned)
    except HtmlUploadError:
        return None
    if candidate.is_dir():
        candidate = candidate / INDEX_NAME
        if not candidate.is_file():
            return None
    if not candidate.is_file():
        return None
    return candidate


def mime_for(path: Path) -> str:
    return _MIME_TYPES.get(path.suffix.lower(), "application/octet-stream")


# ---------- Site metadata (shared by /api/analyze/html and the distiller) ----------

_ICON_RELS = ("apple-touch-icon", "apple-touch-icon-precomposed", "icon")
_ICON_FALLBACK_NAMES = ("apple-touch-icon.png", "apple-touch-icon-precomposed.png", "favicon.png", "favicon.ico")


def _looks_like_image(blob: bytes) -> bool:
    """Cheap magic check: only PNG / ICO / JPEG / GIF / WebP blobs pass. Keeps
    truncated or corrupt data URLs out of the icon pipeline."""
    if not blob or len(blob) < 12:
        return False
    if blob[:4] == b"\x89PNG" or blob[:4] == b"\x00\x00\x01\x00":
        return True
    if blob[:3] == b"\xff\xd8\xff" or blob[:4] == b"GIF8":
        return True
    return blob[:4] == b"RIFF" and blob[8:12] == b"WEBP"


def _icon_bytes_from_href(href: str, site_dir: Path) -> Optional[bytes]:
    """Resolve a declared favicon href to raw bytes: inline data URLs and
    files bundled inside the site. Remote URLs are ignored (no network here)."""
    href = str(href or "").strip()
    if not href:
        return None
    if href.startswith("data:"):
        try:
            _, b64 = href.split(",", 1)
            blob = base64.b64decode(b64, validate=False)
        except Exception:
            return None
        return blob if _looks_like_image(blob) else None
    if href.startswith(("http://", "https://", "//")):
        return None
    try:
        rel = unquote(urlparse(href).path).lstrip("/")
        blob = _contained_path(site_dir, rel).read_bytes()
    except (HtmlUploadError, OSError):
        return None
    return blob if _looks_like_image(blob) else None


def extract_site_meta(site_dir: Path) -> dict:
    """Local-only metadata for a staged site: ``<title>``, theme-color and
    the best declared favicon (raw PNG/ICO bytes). Never touches the network."""
    index = site_dir / INDEX_NAME
    try:
        html = index.read_text(errors="ignore")
    except OSError:
        html = ""
    doc = parse_html_metadata(html)
    icon_png = None
    for rel in _ICON_RELS:
        for attrs in doc.link_attrs_by_rel(rel):
            icon_png = _icon_bytes_from_href(attrs.get("href", ""), site_dir)
            if icon_png:
                break
        if icon_png:
            break
    if not icon_png:
        for name in _ICON_FALLBACK_NAMES:
            candidate = site_dir / name
            if candidate.is_file():
                icon_png = candidate.read_bytes()
                break
    theme_color = doc.meta_content("theme-color")
    return {"title": doc.title, "theme_color": theme_color, "icon_png": icon_png}


def iter_site_files(site_dir: Path) -> List[dict]:
    """All site files as ``{"name": relpath, "data": bytes}`` (sorted)."""
    files = []
    for path in sorted(site_dir.rglob("*")):
        if path.is_file() and site_dir.resolve() in path.resolve().parents:
            files.append({"name": path.relative_to(site_dir).as_posix(), "data": path.read_bytes()})
    return files


def restore_site_files(site_dir: Path, files: List[dict]) -> None:
    """Re-create a site directory from an exported snapshot. Same caps as a
    fresh upload apply — an imported snapshot is just as untrusted."""
    max_files = config.html_site_max_file_count()
    max_bytes = config.html_site_max_uncompressed_bytes()
    if len(files) > max_files:
        raise HtmlUploadError(f"Snapshot has too many files (max {max_files})")
    if sum(len(f.get("data") or b"") for f in files) > max_bytes:
        raise HtmlUploadError("Snapshot is larger than allowed")
    if site_dir.exists():
        shutil.rmtree(site_dir)
    site_dir.mkdir(parents=True, exist_ok=True)
    for item in files:
        name = str(item.get("name") or "")
        blob = bytes(item.get("data") or b"")
        if not name or name != _normalized_entry_name(name):
            raise HtmlUploadError("Snapshot contains an unsafe path")
        target = _contained_path(site_dir, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob)
    if not (site_dir / INDEX_NAME).is_file():
        shutil.rmtree(site_dir, ignore_errors=True)
        raise HtmlUploadError(f"Snapshot must contain {INDEX_NAME} at its root")
