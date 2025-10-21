"""
Caching utilities for performance optimization.

Implements simple in-memory and Redis caching for RAG queries and embeddings.
"""

import hashlib
import json
import pickle
from datetime import datetime, timedelta
from typing import Any, Optional


class SimpleCache:
    """
    Simple in-memory cache with TTL.

    Usage:
        cache = SimpleCache(ttl_seconds=3600)
        cache.set("key", value)
        value = cache.get("key")
    """

    def __init__(self, ttl_seconds: int = 3600):
        """
        Initialize cache.

        Args:
            ttl_seconds: Time to live for cached items
        """
        self._cache: dict[str, tuple[Any, datetime]] = {}
        self.ttl = timedelta(seconds=ttl_seconds)

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if expired/missing
        """
        if key not in self._cache:
            return None

        value, expiry = self._cache[key]

        if datetime.utcnow() > expiry:
            del self._cache[key]
            return None

        return value

    def set(self, key: str, value: Any) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        expiry = datetime.utcnow() + self.ttl
        self._cache[key] = (value, expiry)

    def delete(self, key: str) -> None:
        """Delete key from cache."""
        if key in self._cache:
            del self._cache[key]

    def clear(self) -> None:
        """Clear all cached items."""
        self._cache.clear()

    def size(self) -> int:
        """Get number of cached items."""
        # Clean expired items first
        now = datetime.utcnow()
        expired = [k for k, (_, expiry) in self._cache.items() if now > expiry]
        for k in expired:
            del self._cache[k]

        return len(self._cache)


class RAGCache:
    """
    Specialized cache for RAG query results.

    Caches query results based on normalized query text.
    """

    def __init__(self, ttl_seconds: int = 1800):
        """
        Initialize RAG cache.

        Args:
            ttl_seconds: Cache TTL (default 30 minutes)
        """
        self.cache = SimpleCache(ttl_seconds=ttl_seconds)

    def get_key(self, query: str, top_k: int = 10) -> str:
        """
        Generate cache key for query.

        Args:
            query: Query text
            top_k: Number of results

        Returns:
            Cache key
        """
        # Normalize query
        normalized = query.lower().strip()

        # Hash for key
        key_str = f"{normalized}:{top_k}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def get(self, query: str, top_k: int = 10) -> Optional[dict]:
        """
        Get cached RAG results.

        Args:
            query: Query text
            top_k: Number of results

        Returns:
            Cached results or None
        """
        key = self.get_key(query, top_k)
        return self.cache.get(key)

    def set(self, query: str, result: dict, top_k: int = 10) -> None:
        """
        Cache RAG results.

        Args:
            query: Query text
            result: Query result to cache
            top_k: Number of results
        """
        key = self.get_key(query, top_k)
        self.cache.set(key, result)


class EmbeddingCache:
    """
    Cache for text embeddings.

    Avoids regenerating embeddings for the same text.
    """

    def __init__(self, ttl_seconds: int = 86400):  # 24 hours
        """
        Initialize embedding cache.

        Args:
            ttl_seconds: Cache TTL (default 24 hours)
        """
        self.cache = SimpleCache(ttl_seconds=ttl_seconds)

    def get_key(self, text: str) -> str:
        """
        Generate cache key for text.

        Args:
            text: Input text

        Returns:
            Cache key
        """
        return hashlib.sha256(text.encode()).hexdigest()

    def get(self, text: str) -> Optional[list[float]]:
        """
        Get cached embedding.

        Args:
            text: Input text

        Returns:
            Cached embedding or None
        """
        key = self.get_key(text)
        return self.cache.get(key)

    def set(self, text: str, embedding: list[float]) -> None:
        """
        Cache embedding.

        Args:
            text: Input text
            embedding: Embedding vector
        """
        key = self.get_key(text)
        self.cache.set(key, embedding)


# Optional Redis cache (if redis is available)
try:
    import redis

    class RedisCache:
        """
        Redis-backed cache for distributed systems.

        Usage:
            cache = RedisCache(host='localhost', port=6379)
            cache.set("key", value)
            value = cache.get("key")
        """

        def __init__(
            self,
            host: str = "localhost",
            port: int = 6379,
            db: int = 0,
            ttl_seconds: int = 3600,
        ):
            """
            Initialize Redis cache.

            Args:
                host: Redis host
                port: Redis port
                db: Redis database
                ttl_seconds: Default TTL
            """
            self.client = redis.Redis(host=host, port=port, db=db)
            self.ttl = ttl_seconds

        def get(self, key: str) -> Optional[Any]:
            """Get value from Redis."""
            value = self.client.get(key)
            if value:
                return pickle.loads(value)
            return None

        def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
            """Set value in Redis."""
            ttl = ttl or self.ttl
            self.client.setex(key, ttl, pickle.dumps(value))

        def delete(self, key: str) -> None:
            """Delete key from Redis."""
            self.client.delete(key)

        def clear(self) -> None:
            """Clear all keys."""
            self.client.flushdb()

except ImportError:
    # Redis not available
    pass


# Global cache instances
_rag_cache = None
_embedding_cache = None


def get_rag_cache() -> RAGCache:
    """Get or create global RAG cache."""
    global _rag_cache
    if _rag_cache is None:
        _rag_cache = RAGCache()
    return _rag_cache


def get_embedding_cache() -> EmbeddingCache:
    """Get or create global embedding cache."""
    global _embedding_cache
    if _embedding_cache is None:
        _embedding_cache = EmbeddingCache()
    return _embedding_cache
