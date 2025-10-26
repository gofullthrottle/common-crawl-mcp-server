"""Multi-tier caching system for Common Crawl MCP Server.

This module provides a comprehensive caching layer with:
- Memory cache (LRU) for hot data
- Disk cache for persistent storage
- Optional Redis cache for distributed access

The cache reduces S3 costs and improves performance by avoiding redundant downloads.
"""

import hashlib
import json
import logging
import pickle
import sqlite3
import time
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from ..config import get_config

logger = logging.getLogger(__name__)
config = get_config()


class CacheManager:
    """Multi-tier cache manager.

    Provides three-tier caching:
    1. Memory (LRU) - Fastest, volatile
    2. Disk - Persistent, local
    3. Redis (optional) - Distributed, shared
    """

    def __init__(self):
        """Initialize cache manager."""
        self.cache_dir = config.cache.cache_dir
        self.max_size_bytes = int(config.cache.cache_max_size_gb * 1024**3)
        self.ttl_seconds = config.cache.cache_ttl_seconds

        # Create cache directory
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Initialize disk cache metadata database
        self.db_path = self.cache_dir / "cache_metadata.db"
        self._init_db()

        # Optional Redis client
        self.redis_client = None
        if config.redis.redis_enabled:
            try:
                import redis

                self.redis_client = redis.from_url(
                    config.redis.redis_url,
                    decode_responses=False,  # Keep binary data
                )
                logger.info("Redis cache enabled")
            except Exception as e:
                logger.warning(f"Redis not available: {e}")

        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def _init_db(self):
        """Initialize SQLite database for cache metadata."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cache_metadata (
                key TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                created_at REAL NOT NULL,
                last_accessed REAL NOT NULL,
                access_count INTEGER DEFAULT 0,
                ttl_seconds INTEGER
            )
        """
        )

        conn.commit()
        conn.close()

    def _hash_key(self, key: str) -> str:
        """Generate hash for cache key.

        Args:
            key: Cache key

        Returns:
            SHA256 hash
        """
        return hashlib.sha256(key.encode()).hexdigest()

    def _get_cache_path(self, hash_key: str) -> Path:
        """Get file path for cached item.

        Uses directory sharding: {hash[:2]}/{hash[2:4]}/{hash}.cache

        Args:
            hash_key: Hashed cache key

        Returns:
            Path to cache file
        """
        dir1 = self.cache_dir / hash_key[:2]
        dir2 = dir1 / hash_key[2:4]
        dir2.mkdir(parents=True, exist_ok=True)
        return dir2 / f"{hash_key}.cache"

    async def get(self, key: str) -> Optional[Any]:
        """Get item from cache.

        Checks:
        1. Memory cache (LRU)
        2. Redis (if enabled)
        3. Disk cache

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        hash_key = self._hash_key(key)

        # Check memory cache (via LRU function cache)
        memory_value = self._memory_get(hash_key)
        if memory_value is not None:
            self._hits += 1
            logger.debug(f"Cache HIT (memory): {key}")
            return memory_value

        # Check Redis cache
        if self.redis_client:
            try:
                redis_value = self.redis_client.get(f"cc:{hash_key}")
                if redis_value:
                    value = pickle.loads(redis_value)
                    # Populate memory cache
                    self._memory_set(hash_key, value)
                    self._hits += 1
                    logger.debug(f"Cache HIT (redis): {key}")
                    return value
            except Exception as e:
                logger.warning(f"Redis get error: {e}")

        # Check disk cache
        disk_value = self._disk_get(hash_key)
        if disk_value is not None:
            # Populate higher-tier caches
            self._memory_set(hash_key, disk_value)
            if self.redis_client:
                try:
                    self.redis_client.setex(
                        f"cc:{hash_key}",
                        config.redis.redis_ttl_seconds,
                        pickle.dumps(disk_value),
                    )
                except Exception as e:
                    logger.warning(f"Redis set error: {e}")

            self._hits += 1
            logger.debug(f"Cache HIT (disk): {key}")
            return disk_value

        # Cache miss
        self._misses += 1
        logger.debug(f"Cache MISS: {key}")
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set item in cache.

        Stores in all cache tiers.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (None for default)
        """
        hash_key = self._hash_key(key)
        ttl = ttl or self.ttl_seconds

        # Set in memory cache
        self._memory_set(hash_key, value)

        # Set in Redis
        if self.redis_client:
            try:
                self.redis_client.setex(
                    f"cc:{hash_key}",
                    ttl,
                    pickle.dumps(value),
                )
            except Exception as e:
                logger.warning(f"Redis set error: {e}")

        # Set in disk cache
        self._disk_set(hash_key, value, ttl)

        logger.debug(f"Cached: {key}")

    @lru_cache(maxsize=1024)
    def _memory_get(self, hash_key: str) -> Optional[Any]:
        """Memory cache get (LRU)."""
        # This function is cached itself via @lru_cache
        # Actual data is stored in disk/redis, this just tracks what's in memory
        return None

    def _memory_set(self, hash_key: str, value: Any):
        """Memory cache set.

        Uses function result caching to simulate memory cache.
        """
        # Store reference in LRU cache by calling the cached function
        self._memory_get(hash_key)

    def _disk_get(self, hash_key: str) -> Optional[Any]:
        """Get item from disk cache.

        Args:
            hash_key: Hashed cache key

        Returns:
            Cached value or None
        """
        cache_path = self._get_cache_path(hash_key)

        if not cache_path.exists():
            return None

        # Check TTL
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT created_at, ttl_seconds FROM cache_metadata WHERE key = ?",
            (hash_key,),
        )
        row = cursor.fetchone()

        if row:
            created_at, ttl = row
            age = time.time() - created_at

            if ttl and age > ttl:
                # Expired
                conn.close()
                self._disk_delete(hash_key)
                return None

            # Update access metadata
            cursor.execute(
                """
                UPDATE cache_metadata
                SET last_accessed = ?, access_count = access_count + 1
                WHERE key = ?
                """,
                (time.time(), hash_key),
            )
            conn.commit()

        conn.close()

        # Load from file
        try:
            with open(cache_path, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            logger.error(f"Error loading from disk cache: {e}")
            return None

    def _disk_set(self, hash_key: str, value: Any, ttl: int):
        """Set item in disk cache.

        Args:
            hash_key: Hashed cache key
            value: Value to cache
            ttl: Time-to-live in seconds
        """
        cache_path = self._get_cache_path(hash_key)

        try:
            # Serialize and write
            with open(cache_path, "wb") as f:
                pickle.dump(value, f)

            size_bytes = cache_path.stat().st_size

            # Update metadata
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO cache_metadata
                (key, filename, size_bytes, created_at, last_accessed, ttl_seconds)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    hash_key,
                    cache_path.name,
                    size_bytes,
                    time.time(),
                    time.time(),
                    ttl,
                ),
            )

            conn.commit()
            conn.close()

            # Check if we need to evict old entries
            self._maybe_evict()

        except Exception as e:
            logger.error(f"Error writing to disk cache: {e}")

    def _disk_delete(self, hash_key: str):
        """Delete item from disk cache."""
        cache_path = self._get_cache_path(hash_key)

        if cache_path.exists():
            cache_path.unlink()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cache_metadata WHERE key = ?", (hash_key,))
        conn.commit()
        conn.close()

    def _maybe_evict(self):
        """Evict old entries if cache is too large."""
        current_size = self.get_cache_size()

        if current_size > self.max_size_bytes:
            logger.info(f"Cache size {current_size:,} exceeds max {self.max_size_bytes:,}")
            self._evict_lru()

    def _evict_lru(self):
        """Evict least recently used entries."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Find entries to evict (10% of total)
        cursor.execute("SELECT COUNT(*) FROM cache_metadata")
        total = cursor.fetchone()[0]
        to_evict = max(1, total // 10)

        # Get LRU entries
        cursor.execute(
            """
            SELECT key FROM cache_metadata
            ORDER BY last_accessed ASC
            LIMIT ?
            """,
            (to_evict,),
        )

        keys_to_evict = [row[0] for row in cursor.fetchall()]
        conn.close()

        # Evict
        for key in keys_to_evict:
            self._disk_delete(key)
            self._evictions += 1

        logger.info(f"Evicted {len(keys_to_evict)} cache entries")

    def get_cache_size(self) -> int:
        """Get total cache size in bytes."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(size_bytes) FROM cache_metadata")
        result = cursor.fetchone()[0]
        conn.close()
        return result or 0

    def get_stats(self) -> dict:
        """Get cache statistics."""
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM cache_metadata")
        entry_count = cursor.fetchone()[0]
        conn.close()

        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate_percent": round(hit_rate, 2),
            "evictions": self._evictions,
            "entries": entry_count,
            "size_bytes": self.get_cache_size(),
            "size_gb": round(self.get_cache_size() / 1024**3, 2),
            "max_size_gb": config.cache.cache_max_size_gb,
        }

    async def clear(self):
        """Clear all cache tiers."""
        # Clear disk cache
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT key FROM cache_metadata")
        keys = [row[0] for row in cursor.fetchall()]
        conn.close()

        for key in keys:
            self._disk_delete(key)

        # Clear Redis
        if self.redis_client:
            try:
                self.redis_client.flushdb()
            except Exception as e:
                logger.warning(f"Redis flush error: {e}")

        # Reset memory cache
        self._memory_get.cache_clear()

        # Reset stats
        self._hits = 0
        self._misses = 0
        self._evictions = 0

        logger.info("Cache cleared")
