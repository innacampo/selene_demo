"""
Unit tests for med_logic.py caching infrastructure.

Covers: CacheEntry, TTLCache (get/set/eviction/stats/clear),
generate_cache_key, get_user_context_hash, and high-level cache
management helpers (clear_all_caches, invalidate_*).
"""

import sys
import time
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest

# Streamlit must be patched before importing med_logic.
_st_mock = MagicMock()
sys.modules.setdefault("streamlit", _st_mock)

def _passthrough_decorator(*args, **kwargs):
    if args and callable(args[0]):
        return args[0]
    def wrapper(fn):
        return fn
    return wrapper

_st_mock.cache_data = _passthrough_decorator
_st_mock.cache_resource = _passthrough_decorator
_st_mock.session_state = {}

from selene.core.med_logic import (
    CacheEntry,
    TTLCache,
    generate_cache_key,
    get_user_context_hash,
    contextualized_query_cache,
    rag_cache,
    user_context_cache,
    clear_all_caches,
    invalidate_user_context_cache,
    invalidate_rag_cache,
    get_cache_stats,
)


# ===================================================================
# CacheEntry
# ===================================================================


class TestCacheEntry:
    def test_not_expired_within_ttl(self):
        entry = CacheEntry(value="hello", timestamp=datetime.now(), ttl_seconds=60)
        assert entry.is_expired() is False

    def test_expired_after_ttl(self):
        past = datetime.now() - timedelta(seconds=120)
        entry = CacheEntry(value="old", timestamp=past, ttl_seconds=60)
        assert entry.is_expired() is True

    def test_zero_ttl_expires_immediately(self):
        # With 0-second TTL and a timestamp in the past, should expire
        entry = CacheEntry(
            value="instant",
            timestamp=datetime.now() - timedelta(seconds=1),
            ttl_seconds=0,
        )
        assert entry.is_expired() is True

    def test_stores_value(self):
        entry = CacheEntry(value={"key": "val"}, timestamp=datetime.now(), ttl_seconds=10)
        assert entry.value == {"key": "val"}


# ===================================================================
# TTLCache – basic operations
# ===================================================================


class TestTTLCacheBasic:
    def setup_method(self):
        self.cache = TTLCache(max_size=5)

    def test_miss_returns_none(self):
        assert self.cache.get("nonexistent") is None

    def test_set_and_get(self):
        self.cache.set("k1", "v1", ttl_seconds=60)
        assert self.cache.get("k1") == "v1"

    def test_overwrite_existing_key(self):
        self.cache.set("k1", "old", ttl_seconds=60)
        self.cache.set("k1", "new", ttl_seconds=60)
        assert self.cache.get("k1") == "new"

    def test_expired_entry_returns_none(self):
        self.cache.set("k1", "v1", ttl_seconds=1)
        # Manually backdate the entry
        self.cache.cache["k1"].timestamp = datetime.now() - timedelta(seconds=10)
        assert self.cache.get("k1") is None

    def test_clear(self):
        self.cache.set("a", 1, ttl_seconds=60)
        self.cache.set("b", 2, ttl_seconds=60)
        self.cache.clear()
        assert self.cache.get("a") is None
        assert self.cache.get("b") is None


# ===================================================================
# TTLCache – eviction
# ===================================================================


class TestTTLCacheEviction:
    def test_evicts_oldest_when_full(self):
        cache = TTLCache(max_size=3)
        # Insert with staggered timestamps so "k1" is oldest
        cache.set("k1", "v1", ttl_seconds=300)
        cache.cache["k1"].timestamp = datetime.now() - timedelta(seconds=30)

        cache.set("k2", "v2", ttl_seconds=300)
        cache.cache["k2"].timestamp = datetime.now() - timedelta(seconds=20)

        cache.set("k3", "v3", ttl_seconds=300)
        cache.cache["k3"].timestamp = datetime.now() - timedelta(seconds=10)

        # This should evict k1
        cache.set("k4", "v4", ttl_seconds=300)
        assert cache.get("k1") is None
        assert cache.get("k4") == "v4"

    def test_cache_size_respects_limit(self):
        cache = TTLCache(max_size=2)
        cache.set("a", 1, ttl_seconds=300)
        cache.set("b", 2, ttl_seconds=300)
        cache.set("c", 3, ttl_seconds=300)
        # Only 2 keys should remain
        assert len(cache.cache) == 2


# ===================================================================
# TTLCache – hit/miss statistics
# ===================================================================


class TestTTLCacheStats:
    def test_hit_miss_counters(self):
        cache = TTLCache(max_size=10)
        cache.set("x", 42, ttl_seconds=60)

        cache.get("x")  # hit
        cache.get("x")  # hit
        cache.get("y")  # miss

        stats = cache.get_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["size"] == 1
        assert stats["total_requests"] == 3
        assert stats["hit_rate"] == "66.7%"

    def test_stats_after_clear(self):
        cache = TTLCache(max_size=10)
        cache.set("x", 1, ttl_seconds=60)
        cache.get("x")
        cache.clear()

        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["size"] == 0

    def test_expired_entry_counted_as_miss(self):
        cache = TTLCache(max_size=10)
        cache.set("k", "val", ttl_seconds=1)
        cache.cache["k"].timestamp = datetime.now() - timedelta(seconds=10)

        cache.get("k")  # expired → counted as miss

        stats = cache.get_stats()
        assert stats["misses"] == 1
        assert stats["hits"] == 0


# ===================================================================
# generate_cache_key
# ===================================================================


class TestGenerateCacheKey:
    def test_deterministic(self):
        k1 = generate_cache_key("hello", "world", prefix="test")
        k2 = generate_cache_key("hello", "world", prefix="test")
        assert k1 == k2

    def test_different_args_different_keys(self):
        k1 = generate_cache_key("a", prefix="p")
        k2 = generate_cache_key("b", prefix="p")
        assert k1 != k2

    def test_prefix_included(self):
        key = generate_cache_key("data", prefix="rag")
        assert key.startswith("rag:")

    def test_no_prefix(self):
        key = generate_cache_key("data")
        assert ":" not in key  # pure hash, no prefix

    def test_key_is_sha256_hex(self):
        key = generate_cache_key("x", prefix="")
        # No prefix → raw hash
        assert len(key) == 64  # SHA-256 hex digest length


# ===================================================================
# get_user_context_hash
# ===================================================================


class TestGetUserContextHash:
    def test_uses_profile_hash(self):
        with patch(
            "selene.core.context_builder.get_user_profile_hash", return_value="abc123"
        ):
            result = get_user_context_hash()
            assert result == "abc123"

    def test_fallback_on_import_error(self):
        with patch.dict("sys.modules", {"selene.core.context_builder": None}):
            # Force ImportError inside the function by removing the module
            # get_user_context_hash does a local import, so removing the
            # module from sys.modules triggers the fallback path.
            result = get_user_context_hash()
            assert isinstance(result, str)
            assert len(result) > 0


# ===================================================================
# Global caches – management helpers
# ===================================================================


class TestCacheManagement:
    def setup_method(self):
        """Start each test with clean caches."""
        clear_all_caches()

    def test_clear_all_caches(self):
        contextualized_query_cache.set("q1", "v1", ttl_seconds=300)
        rag_cache.set("r1", "v1", ttl_seconds=300)
        user_context_cache.set("u1", "v1", ttl_seconds=300)

        clear_all_caches()

        assert contextualized_query_cache.get("q1") is None
        assert rag_cache.get("r1") is None
        assert user_context_cache.get("u1") is None

    def test_invalidate_user_context_cache(self):
        user_context_cache.set("ctx", "data", ttl_seconds=300)
        rag_cache.set("rag", "data", ttl_seconds=300)

        invalidate_user_context_cache()

        assert user_context_cache.get("ctx") is None
        # RAG cache should be untouched
        assert rag_cache.get("rag") == "data"

    def test_invalidate_rag_cache(self):
        rag_cache.set("rag", "data", ttl_seconds=300)
        user_context_cache.set("ctx", "data", ttl_seconds=300)

        invalidate_rag_cache()

        assert rag_cache.get("rag") is None
        # User context cache should be untouched
        assert user_context_cache.get("ctx") == "data"

    def test_get_cache_stats_structure(self):
        stats = get_cache_stats()
        assert "contextualized_query" in stats
        assert "rag" in stats
        assert "user_context" in stats
        for name in ("contextualized_query", "rag", "user_context"):
            s = stats[name]
            assert "size" in s
            assert "hits" in s
            assert "misses" in s
            assert "hit_rate" in s


# ===================================================================
# Thread-safety smoke test
# ===================================================================


class TestTTLCacheThreadSafety:
    def test_concurrent_set_get(self):
        """Verify no exceptions under concurrent access."""
        import threading

        cache = TTLCache(max_size=50)
        errors = []

        def writer(prefix, count):
            try:
                for i in range(count):
                    cache.set(f"{prefix}_{i}", i, ttl_seconds=60)
            except Exception as e:
                errors.append(e)

        def reader(prefix, count):
            try:
                for i in range(count):
                    cache.get(f"{prefix}_{i}")
            except Exception as e:
                errors.append(e)

        threads = []
        for p in ("a", "b", "c"):
            threads.append(threading.Thread(target=writer, args=(p, 20)))
            threads.append(threading.Thread(target=reader, args=(p, 20)))

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert errors == [], f"Thread errors: {errors}"
