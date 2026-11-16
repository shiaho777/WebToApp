import threading
import time
from collections import OrderedDict
from typing import Any, Optional

from server import config


def _value_size(value: Any) -> int:
    """Approximate payload size for the byte budget; non-bytes values count
    as 1 so entry-count semantics stay meaningful for small dict caches."""
    if isinstance(value, (bytes, bytearray, memoryview)):
        return len(value)
    if isinstance(value, str):
        return len(value.encode("utf-8", errors="ignore"))
    return 1


class TTLCache:
    def __init__(self, max_size: int = 256, ttl_seconds: float = 600.0,
                 max_bytes: Optional[int] = None):
        self.max_size = max(1, int(max_size or 1))
        self.ttl_seconds = max(0.001, float(ttl_seconds or 1.0))
        self.max_bytes = int(max_bytes) if max_bytes else None
        self._data = OrderedDict()
        self._sizes = {}
        self._bytes = 0
        self._lock = threading.RLock()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        now = time.time()
        with self._lock:
            item = self._data.get(key)
            if not item:
                self.misses += 1
                return None
            expires_at, value = item
            if expires_at < now:
                self._data.pop(key, None)
                self._bytes -= self._sizes.pop(key, 0)
                self.misses += 1
                return None
            self._data.move_to_end(key)
            self.hits += 1
            return value

    def set(self, key: str, value: Any) -> None:
        expires_at = time.time() + self.ttl_seconds
        size = _value_size(value)
        with self._lock:
            if key in self._data:
                self._bytes -= self._sizes.pop(key, 0)
            self._data[key] = (expires_at, value)
            self._sizes[key] = size
            self._bytes += size
            self._data.move_to_end(key)
            while len(self._data) > self.max_size:
                old_key, _ = self._data.popitem(last=False)
                self._bytes -= self._sizes.pop(old_key, 0)
            if self.max_bytes is not None:
                # A single value larger than the whole budget is still stored
                # (evicting everything else); the next set will push it out.
                while self._bytes > self.max_bytes and len(self._data) > 1:
                    old_key, _ = self._data.popitem(last=False)
                    self._bytes -= self._sizes.pop(old_key, 0)

    def stats(self) -> dict:
        with self._lock:
            return {
                "size": len(self._data),
                "max_size": self.max_size,
                "bytes": self._bytes,
                "max_bytes": self.max_bytes,
                "ttl_seconds": self.ttl_seconds,
                "hits": self.hits,
                "misses": self.misses,
            }


# html_cache holds whole fetched pages (up to 4MB each): 128 entries could
# theoretically pin ~512MB. The byte budget caps real usage at 64MB while
# keeping the entry-count LRU for small pages.
html_cache = TTLCache(max_size=128, ttl_seconds=config.html_cache_ttl_seconds(),
                      max_bytes=config.html_cache_max_bytes())
icon_cache = TTLCache(max_size=256, ttl_seconds=config.icon_cache_ttl_seconds())
# Misses get a much shorter TTL: a transient network failure must not pin a
# host to the placeholder icon for a full hour, but a short marker still
# dedupes rebuild bursts (the candidate sweep is a few seconds on CN hosts).
icon_miss_cache = TTLCache(max_size=256, ttl_seconds=60)

analysis_cache = TTLCache(max_size=128, ttl_seconds=600)
