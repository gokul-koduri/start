"""Standardized two-tier caching: Redis primary + in-memory fallback.

Usage:
    from utils.cache import cache

    # Simple get/set
    cache.set("key", {"data": 42}, ttl=60)
    result = cache.get("key")

    # Cache-aside pattern
    result = cache.get_or_compute("expensive_key", lambda: compute(), ttl=120)

    # Invalidate
    cache.invalidate("api:*")

The module creates a singleton `cache` instance on import. Redis is optional —
if unavailable, it gracefully falls back to in-memory caching.
"""

import json
import logging
import os
import time
from typing import Any, Callable, Optional

_logger = logging.getLogger(__name__)


class CacheManager:
    """Two-tier cache manager: Redis primary, in-memory fallback.

    Args:
        redis_url: Redis connection URL. Falls back to env REDIS_URL or
                   redis://localhost:6379/0.
        default_ttl: Default TTL in seconds for cache entries.
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        default_ttl: int = 60,
    ):
        self._default_ttl = default_ttl
        self._redis_url = redis_url or os.environ.get(
            "REDIS_URL", "redis://localhost:6379/0"
        )
        self._memory: dict[str, tuple[Any, float]] = {}  # key -> (value, expiry)
        self._redis_client: Any = None
        self._redis_available: Optional[bool] = None

    def _get_redis(self) -> Any:
        """Get or create Redis client with connection pooling."""
        if self._redis_client is not None:
            return self._redis_client

        try:
            import redis as _redis

            pool = _redis.ConnectionPool.from_url(
                self._redis_url,
                socket_connect_timeout=2,
                max_connections=10,
                decode_responses=True,
            )
            self._redis_client = _redis.Redis(connection_pool=pool)

            # Test connection
            self._redis_client.ping()
            self._redis_available = True
            _logger.info("CacheManager: Redis connected at %s", self._redis_url)
            return self._redis_client
        except Exception as e:
            _logger.warning(
                "CacheManager: Redis unavailable (%s) — using in-memory fallback", e
            )
            self._redis_available = False
            return None

    def get(self, key: str) -> Optional[dict]:
        """Retrieve cached value. Returns None if not found or expired.

        Tries Redis first, then in-memory fallback.
        """
        # Try Redis
        redis = self._get_redis()
        if self._redis_available and redis:
            try:
                raw = redis.get(f"api:{key}")
                if raw:
                    return json.loads(raw)
            except Exception:
                pass

        # Fallback to in-memory
        entry = self._memory.get(key)
        if entry:
            value, expiry = entry
            if expiry > time.time():
                return value
            del self._memory[key]

        return None

    def set(self, key: str, value: dict, ttl: Optional[int] = None) -> None:
        """Set cache value in both Redis and in-memory.

        Args:
            key: Cache key (without prefix).
            value: Dict value to cache.
            ttl: Time-to-live in seconds. Uses default_ttl if None.
        """
        ttl = ttl or self._default_ttl
        expiry = time.time() + ttl

        # Set in-memory
        self._memory[key] = (value, expiry)

        # Set in Redis
        redis = self._get_redis()
        if self._redis_available and redis:
            try:
                redis.setex(f"api:{key}", ttl, json.dumps(value, default=str))
            except Exception:
                pass

    def invalidate(self, pattern: str = "api:*") -> None:
        """Clear matching keys from both Redis and in-memory.

        Args:
            pattern: Glob pattern for Redis keys. For in-memory, clears all.
        """
        # Clear in-memory
        self._memory.clear()

        # Clear Redis
        redis = self._get_redis()
        if self._redis_available and redis:
            try:
                for key in redis.scan_iter(pattern):
                    redis.delete(key)
            except Exception:
                pass

    def get_or_compute(
        self,
        key: str,
        compute_fn: Callable[[], dict],
        ttl: Optional[int] = None,
    ) -> dict:
        """Cache-aside pattern: return cached value or compute, cache, and return.

        Args:
            key: Cache key.
            compute_fn: Callable that returns the value if not cached.
            ttl: TTL in seconds.

        Returns:
            The cached or freshly computed value.
        """
        cached = self.get(key)
        if cached is not None:
            return cached

        value = compute_fn()
        self.set(key, value, ttl=ttl)
        return value

    @property
    def stats(self) -> dict:
        """Return cache statistics."""
        redis_status = "connected" if self._redis_available else "unavailable"
        return {
            "redis_status": redis_status,
            "memory_keys": len(self._memory),
            "redis_url": self._redis_url,
        }


# Singleton instance for import
cache = CacheManager()
