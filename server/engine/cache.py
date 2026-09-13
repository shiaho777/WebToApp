import threading
import time
from collections import OrderedDict
from typing import Any, Optional


class TTLCache:
    def __init__(self, max_size: int = 256, ttl_seconds: float = 600.0):
        self.max_size = max(1, int(max_size or 1))
        self.ttl_seconds = max(0.001, float(ttl_seconds or 1.0))
        self._data = OrderedDict()
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
                self.misses += 1
                return None
            self._data.move_to_end(key)
            self.hits += 1
            return value

    def set(self, key: str, value: Any) -> None:
        expires_at = time.time() + self.ttl_seconds
        with self._lock:
            self._data[key] = (expires_at, value)
            self._data.move_to_end(key)
            while len(self._data) > self.max_size:
                self._data.popitem(last=False)

    def stats(self) -> dict:
        with self._lock:
            return {
                "size": len(self._data),
                "max_size": self.max_size,
                "ttl_seconds": self.ttl_seconds,
                "hits": self.hits,
                "misses": self.misses,
            }


html_cache = TTLCache(max_size=128, ttl_seconds=900)
icon_cache = TTLCache(max_size=256, ttl_seconds=3600)
# Misses get a much shorter TTL: a transient network failure must not pin a
# host to the placeholder icon for a full hour, but a short marker still
# dedupes rebuild bursts (the candidate sweep is a few seconds on CN hosts).
icon_miss_cache = TTLCache(max_size=256, ttl_seconds=60)

analysis_cache = TTLCache(max_size=128, ttl_seconds=600)
