"""Selective gzip for text responses (issue #161).

Starlette's stock ``GZipMiddleware`` compresses every response over a size
threshold, including streamed APK/IPA/ZIP downloads that are already
compressed — burning CPU for nothing and dropping ``Content-Length`` so
browsers lose download progress. This middleware only touches text-like
200 responses (HTML, CSS, JS, JSON, SVG, manifests), leaves Range and HEAD
requests alone, and weakens the ETag of compressed bodies so conditional
requests keep yielding cheap 304s.
"""

import gzip
from typing import List, Optional

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

COMPRESSIBLE_TYPES = (
    "text/",
    "application/javascript",
    "application/json",
    "application/manifest+json",
    "application/xml",
    "image/svg+xml",
)
MINIMUM_SIZE = 1024
MAXIMUM_SIZE = 4 * 1024 * 1024


def accepts_gzip(accept_encoding: Optional[str]) -> bool:
    """True when the client lists gzip (or ``*``) without ``q=0``."""
    for part in str(accept_encoding or "").split(","):
        token, _, params = part.strip().partition(";")
        token = token.strip().lower()
        if token not in ("gzip", "*"):
            continue
        quality = 1.0
        for param in params.split(";"):
            key, _, value = param.strip().partition("=")
            if key.strip().lower() == "q":
                try:
                    quality = float(value)
                except ValueError:
                    quality = 0.0
        if quality > 0:
            return True
    return False


def is_compressible(content_type: Optional[str]) -> bool:
    media_type = str(content_type or "").split(";", 1)[0].strip().lower()
    return bool(media_type) and media_type.startswith(COMPRESSIBLE_TYPES)


class TextCompressionMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        minimum_size: int = MINIMUM_SIZE,
        maximum_size: int = MAXIMUM_SIZE,
        compresslevel: int = 6,
    ) -> None:
        self.app = app
        self.minimum_size = minimum_size
        self.maximum_size = maximum_size
        self.compresslevel = compresslevel

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("method") == "HEAD":
            await self.app(scope, receive, send)
            return
        request_headers = Headers(scope=scope)
        gzip_ok = accepts_gzip(request_headers.get("accept-encoding")) and "range" not in request_headers
        responder = _Responder(self, send, gzip_ok)
        await self.app(scope, receive, responder)


class _Responder:
    def __init__(self, owner: TextCompressionMiddleware, send: Send, gzip_ok: bool) -> None:
        self.owner = owner
        self.send = send
        self.gzip_ok = gzip_ok
        self.start: Optional[Message] = None
        self.buffering = False
        self.chunks: List[bytes] = []
        self.size = 0

    async def __call__(self, message: Message) -> None:
        kind = message["type"]
        if kind == "http.response.start":
            await self._on_start(message)
        elif kind == "http.response.body" and self.buffering:
            await self._on_body(message)
        else:
            await self.send(message)

    async def _on_start(self, message: Message) -> None:
        headers = MutableHeaders(scope=message)
        eligible = (
            message.get("status") == 200
            and "content-encoding" not in headers
            and is_compressible(headers.get("content-type"))
        )
        if eligible:
            # Caches must key on Accept-Encoding whether or not this client
            # gets the gzip variant.
            headers.add_vary_header("Accept-Encoding")
        if eligible and self.gzip_ok:
            declared = headers.get("content-length")
            if declared is not None and declared.isdigit():
                eligible = self.owner.minimum_size <= int(declared) <= self.owner.maximum_size
        else:
            eligible = False
        if not eligible:
            await self.send(message)
            return
        self.start = message
        self.buffering = True

    async def _on_body(self, message: Message) -> None:
        body = message.get("body", b"")
        more_body = message.get("more_body", False)
        self.chunks.append(body)
        self.size += len(body)
        if self.size > self.owner.maximum_size:
            await self._flush_plain(more_body)
            return
        if more_body:
            return
        if self.size < self.owner.minimum_size:
            await self._flush_plain(False)
            return
        payload = gzip.compress(b"".join(self.chunks), compresslevel=self.owner.compresslevel)
        headers = MutableHeaders(scope=self.start)
        headers["Content-Encoding"] = "gzip"
        headers["Content-Length"] = str(len(payload))
        etag = headers.get("etag")
        if etag and not etag.startswith("W/"):
            headers["ETag"] = "W/" + etag
        self.buffering = False
        await self.send(self.start)
        await self.send({"type": "http.response.body", "body": payload, "more_body": False})

    async def _flush_plain(self, more_body: bool) -> None:
        self.buffering = False
        await self.send(self.start)
        await self.send({"type": "http.response.body", "body": b"".join(self.chunks), "more_body": more_body})
        self.chunks = []
