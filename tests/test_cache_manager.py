"""CacheManager tests — validates two-tier caching, TTL, and cache-aside pattern (T-116)."""

import unittest
import sys
import time
import json
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestCacheManagerMemoryOnly(unittest.TestCase):
    """Test CacheManager with Redis unavailable (in-memory only)."""

    def _make_cache(self, default_ttl=60):
        from utils.cache import CacheManager

        cm = CacheManager(redis_url="redis://localhost:0", default_ttl=default_ttl)
        # Force Redis unavailable
        cm._redis_available = False
        cm._redis_client = None
        return cm

    def test_set_and_get(self):
        """Basic set/get cycle works in memory."""
        cache = self._make_cache()
        cache.set("test_key", {"value": 42})
        result = cache.get("test_key")
        self.assertEqual(result, {"value": 42})

    def test_get_missing_key(self):
        """Returns None for missing key."""
        cache = self._make_cache()
        result = cache.get("nonexistent")
        self.assertIsNone(result)

    def test_ttl_expiry(self):
        """Entries expire after TTL."""
        cache = self._make_cache(default_ttl=1)
        cache.set("short_key", {"value": 1}, ttl=1)
        time.sleep(1.1)
        result = cache.get("short_key")
        self.assertIsNone(result)

    def test_invalidate_clears_memory(self):
        """Invalidate clears all in-memory entries."""
        cache = self._make_cache()
        cache.set("key1", {"a": 1})
        cache.set("key2", {"b": 2})
        cache.invalidate()
        self.assertIsNone(cache.get("key1"))
        self.assertIsNone(cache.get("key2"))

    def test_get_or_compute_caches(self):
        """get_or_compute caches the result of compute_fn."""
        cache = self._make_cache()
        call_count = 0

        def compute():
            nonlocal call_count
            call_count += 1
            return {"computed": True}

        result1 = cache.get_or_compute("mykey", compute)
        result2 = cache.get_or_compute("mykey", compute)

        self.assertEqual(result1, {"computed": True})
        self.assertEqual(result2, {"computed": True})
        self.assertEqual(call_count, 1)  # compute only called once

    def test_get_or_compute_with_ttl(self):
        """get_or_compute respects TTL."""
        cache = self._make_cache()
        cache.get_or_compute("ttl_key", lambda: {"val": 1}, ttl=1)
        time.sleep(1.1)
        result = cache.get_or_compute("ttl_key", lambda: {"val": 2}, ttl=1)
        self.assertEqual(result, {"val": 2})  # Recomputed after expiry

    def test_stats(self):
        """Stats returns memory_keys count."""
        cache = self._make_cache()
        cache.set("k1", {"v": 1})
        cache.set("k2", {"v": 2})
        stats = cache.stats
        self.assertEqual(stats["memory_keys"], 2)
        self.assertEqual(stats["redis_status"], "unavailable")


class TestCacheManagerWithRedis(unittest.TestCase):
    """Test CacheManager with mocked Redis."""

    def _make_cache_with_mock_redis(self):
        from utils.cache import CacheManager

        cm = CacheManager(redis_url="redis://mock:6379/0")

        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.get.return_value = None
        mock_redis.setex.return_value = True
        mock_redis.scan_iter.return_value = []
        mock_redis.delete.return_value = 1

        cm._redis_client = mock_redis
        cm._redis_available = True
        return cm, mock_redis

    def test_set_writes_to_redis(self):
        """set() writes to both memory and Redis."""
        cache, mock_redis = self._make_cache_with_mock_redis()
        cache.set("rkey", {"data": "hello"}, ttl=30)

        mock_redis.setex.assert_called_once()
        args = mock_redis.setex.call_args[0]
        self.assertEqual(args[0], "api:rkey")
        self.assertEqual(args[1], 30)
        self.assertIn("hello", args[2])

    def test_get_reads_from_redis(self):
        """get() reads from Redis when available."""
        cache, mock_redis = self._make_cache_with_mock_redis()
        mock_redis.get.return_value = json.dumps({"data": "from_redis"})

        result = cache.get("rkey")
        self.assertEqual(result, {"data": "from_redis"})
        mock_redis.get.assert_called_once_with("api:rkey")

    def test_get_falls_back_to_memory(self):
        """get() falls back to memory when Redis returns None."""
        cache, mock_redis = self._make_cache_with_mock_redis()
        mock_redis.get.return_value = None
        cache.set("mkey", {"data": "from_memory"})

        # Clear Redis mock to return None, but memory has it
        result = cache.get("mkey")
        self.assertEqual(result, {"data": "from_memory"})

    def test_invalidate_clears_redis(self):
        """invalidate() clears Redis keys matching pattern."""
        cache, mock_redis = self._make_cache_with_mock_redis()
        mock_redis.scan_iter.return_value = ["api:k1", "api:k2"]

        cache.invalidate("api:*")
        self.assertEqual(mock_redis.delete.call_count, 2)

    def test_stats_redis_connected(self):
        """Stats shows Redis as connected."""
        cache, _ = self._make_cache_with_mock_redis()
        stats = cache.stats
        self.assertEqual(stats["redis_status"], "connected")


if __name__ == "__main__":
    unittest.main()
