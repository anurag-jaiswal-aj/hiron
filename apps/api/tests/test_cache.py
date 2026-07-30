"""Unit tests for CacheManager TTL expiration, key invalidation, pattern clearing, and statistics."""

import asyncio

import pytest

from hiron.core.cache import CacheManager


@pytest.mark.asyncio
async def test_cache_set_get_hit() -> None:
    """Verify storing and retrieving items from CacheManager."""
    cache = CacheManager(default_ttl=60.0)

    await cache.set("user:123", {"name": "Alice"})
    val = await cache.get("user:123")

    assert val == {"name": "Alice"}
    stats = cache.get_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 0
    assert stats["hit_rate"] == 1.0


@pytest.mark.asyncio
async def test_cache_miss_and_expiration() -> None:
    """Verify cache miss on non-existent key and expired TTL."""
    cache = CacheManager(default_ttl=0.05)  # 50ms TTL

    val = await cache.get("non_existent")
    assert val is None

    await cache.set("temp_key", "temp_value")
    await asyncio.sleep(0.06)

    expired_val = await cache.get("temp_key")
    assert expired_val is None

    stats = cache.get_stats()
    assert stats["hits"] == 0
    assert stats["misses"] == 2


@pytest.mark.asyncio
async def test_cache_pattern_invalidation() -> None:
    """Verify invalidating keys by prefix pattern."""
    cache = CacheManager()

    await cache.set("pipeline:stage:1", "stage1")
    await cache.set("pipeline:stage:2", "stage2")
    await cache.set("user:profile:1", "user1")

    count = await cache.invalidate_pattern("pipeline:stage:")
    assert count == 2

    assert await cache.get("pipeline:stage:1") is None
    assert await cache.get("user:profile:1") == "user1"
