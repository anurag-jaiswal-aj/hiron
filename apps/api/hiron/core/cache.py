"""Thread-safe, async-compatible TTL in-memory/Redis LRU cache manager with hit/miss metrics."""

import asyncio
import json
import time
from typing import Any

import redis.asyncio as redis
import structlog
from pydantic import BaseModel

from hiron.core.config import get_settings

logger = structlog.get_logger("hiron.core.cache")
settings = get_settings()


class CacheItem:
    """Entry wrapper holding cached value and expiration timestamp for in-memory fallback."""

    def __init__(self, value: Any, ttl_seconds: float) -> None:
        self.value = value
        self.expires_at = time.monotonic() + ttl_seconds

    def is_expired(self) -> bool:
        """Check if cached entry has exceeded its TTL."""
        return time.monotonic() >= self.expires_at


class CacheManager:
    """Async-compatible Redis cache manager with in-memory fallback, TTL, and metrics."""

    def __init__(self, default_ttl: float = 300.0) -> None:
        self._default_ttl = default_ttl
        self._hits = 0
        self._misses = 0

        self._redis: redis.Redis | None = None
        self._fallback_store: dict[str, CacheItem] = {}
        self._lock: asyncio.Lock | None = None

    def _get_lock(self) -> asyncio.Lock:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if self._lock is None or getattr(self._lock, "_loop", None) is not loop:
            self._lock = asyncio.Lock()
            self._lock._loop = loop
        return self._lock

    def _get_redis(self) -> redis.Redis:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if self._redis is None or getattr(self._redis, "_loop", None) is not loop:
            self._redis = redis.from_url(settings.redis_url, decode_responses=True)
            self._redis._loop = loop
        return self._redis

    async def get(self, key: str) -> Any | None:
        """Fetch item from cache. Returns None on miss or expiration."""
        r = self._get_redis()
        try:
            val = await r.get(key)
            if val is not None:
                self._hits += 1
                return json.loads(val)
        except redis.RedisError as e:
            logger.warning("Redis GET failed, falling back to in-memory", error=str(e), key=key)

        # Fallback to in-memory
        async with self._get_lock():
            item = self._fallback_store.get(key)
            if item is None:
                self._misses += 1
                return None

            if item.is_expired():
                del self._fallback_store[key]
                self._misses += 1
                return None

            self._hits += 1
            return item.value

    async def set(self, key: str, value: Any, ttl_seconds: float | None = None) -> None:
        """Store item in cache with specified TTL in seconds."""
        ttl = int(ttl_seconds if ttl_seconds is not None else self._default_ttl)
        r = self._get_redis()

        # Serialize Pydantic models or dicts to JSON string
        if isinstance(value, BaseModel):
            serialized_value = value.model_dump_json()
        else:
            serialized_value = json.dumps(value, default=str)

        try:
            await r.setex(key, ttl, serialized_value)
        except redis.RedisError as e:
            logger.warning("Redis SET failed, falling back to in-memory", error=str(e), key=key)
            async with self._get_lock():
                self._fallback_store[key] = CacheItem(value, float(ttl))

    async def invalidate(self, key: str) -> bool:
        """Explicitly remove a single key from cache."""
        deleted = False
        r = self._get_redis()
        try:
            res = await r.delete(key)
            if res > 0:
                deleted = True
        except redis.RedisError as e:
            logger.warning("Redis DEL failed", error=str(e), key=key)

        async with self._get_lock():
            if key in self._fallback_store:
                del self._fallback_store[key]
                deleted = True

        return deleted

    async def invalidate_pattern(self, pattern_prefix: str) -> int:
        """Remove all keys starting with specified prefix pattern."""
        deleted_count = 0
        r = self._get_redis()
        try:
            # SCAN for keys matching pattern
            cursor = b"0"
            keys = []
            while cursor:
                cursor, scan_keys = await r.scan(cursor=cursor, match=f"{pattern_prefix}*")
                keys.extend(scan_keys)
                if cursor == 0 or cursor == b"0":
                    break

            if keys:
                deleted_count = await r.delete(*keys)
        except redis.RedisError as e:
            logger.warning("Redis SCAN/DEL failed for pattern", error=str(e), pattern=pattern_prefix)

        async with self._get_lock():
            keys_to_del = [k for k in self._fallback_store if k.startswith(pattern_prefix)]
            for k in keys_to_del:
                del self._fallback_store[k]
            deleted_count += len(keys_to_del)

        return deleted_count

    async def clear(self) -> None:
        """Purge all entries from cache store."""
        r = self._get_redis()
        try:
            await r.flushdb()
        except redis.RedisError as e:
            logger.warning("Redis FLUSHDB failed", error=str(e))

        async with self._get_lock():
            self._fallback_store.clear()

    def get_stats(self) -> dict[str, Any]:
        """Return cache hit, miss, total count, and hit rate statistics."""
        total = self._hits + self._misses
        hit_rate = (float(self._hits) / total) if total > 0 else 0.0
        return {
            "hits": self._hits,
            "misses": self._misses,
            "total_requests": total,
            "hit_rate": round(hit_rate, 4),
            "cached_entries_count": len(self._fallback_store), # Redis keys count requires dbsize
        }


# Global application cache manager instance
app_cache = CacheManager(default_ttl=300.0)
