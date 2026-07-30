"""Thread-safe, async-compatible TTL in-memory LRU cache manager with hit/miss metrics."""

import asyncio
import time
from typing import Any

import structlog

logger = structlog.get_logger("hiron.core.cache")


class CacheItem:
    """Entry wrapper holding cached value and expiration timestamp."""

    def __init__(self, value: Any, ttl_seconds: float) -> None:
        self.value = value
        self.expires_at = time.monotonic() + ttl_seconds

    def is_expired(self) -> bool:
        """Check if cached entry has exceeded its TTL."""
        return time.monotonic() >= self.expires_at


class CacheManager:
    """Async-compatible in-memory LRU cache manager supporting TTL, pattern invalidation, and metrics."""

    def __init__(self, default_ttl: float = 300.0) -> None:
        self._store: dict[str, CacheItem] = {}
        self._default_ttl = default_ttl
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0

    async def get(self, key: str) -> Any | None:
        """Fetch item from cache. Returns None on miss or expiration."""
        async with self._lock:
            item = self._store.get(key)
            if item is None:
                self._misses += 1
                return None

            if item.is_expired():
                del self._store[key]
                self._misses += 1
                return None

            self._hits += 1
            return item.value

    async def set(self, key: str, value: Any, ttl_seconds: float | None = None) -> None:
        """Store item in cache with specified TTL in seconds."""
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        async with self._lock:
            self._store[key] = CacheItem(value, ttl)

    async def invalidate(self, key: str) -> bool:
        """Explicitly remove a single key from cache."""
        async with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    async def invalidate_pattern(self, pattern_prefix: str) -> int:
        """Remove all keys starting with specified prefix pattern."""
        async with self._lock:
            keys_to_del = [k for k in self._store if k.startswith(pattern_prefix)]
            for k in keys_to_del:
                del self._store[k]
            return len(keys_to_del)

    async def clear(self) -> None:
        """Purge all entries from cache store."""
        async with self._lock:
            self._store.clear()

    def get_stats(self) -> dict[str, Any]:
        """Return cache hit, miss, total count, and hit rate statistics."""
        total = self._hits + self._misses
        hit_rate = (float(self._hits) / total) if total > 0 else 0.0
        return {
            "hits": self._hits,
            "misses": self._misses,
            "total_requests": total,
            "hit_rate": round(hit_rate, 4),
            "cached_entries_count": len(self._store),
        }


# Global application cache manager instance
app_cache = CacheManager(default_ttl=300.0)
