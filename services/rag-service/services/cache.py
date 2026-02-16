"""
Query Result Caching Service for RAG Pipeline.

This module provides Redis-based caching for query results with TTL support.
"""

import hashlib
import json
from datetime import timedelta
from typing import Any, Dict, List, Optional

import structlog
from redis import asyncio as aioredis

from config import get_settings

logger = structlog.get_logger()


class QueryCache:
    """Redis-based cache for RAG query results."""

    def __init__(self, redis_url: Optional[str] = None, ttl_seconds: int = 300):
        """Initialize the query cache.

        Args:
            redis_url: Redis connection URL
            ttl_seconds: Time-to-live for cached results in seconds (default: 5 minutes)
        """
        settings = get_settings()
        self.redis_url = redis_url or settings.redis_url
        self.ttl_seconds = ttl_seconds
        self._client: Optional[aioredis.Redis] = None

    async def _get_client(self) -> aioredis.Redis:
        """Get or create Redis client."""
        if self._client is None:
            self._client = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._client

    def _generate_cache_key(
        self,
        query: str,
        collection: str,
        top_k: int,
        filters: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate a cache key from query parameters.

        Args:
            query: Search query string
            collection: Collection name
            top_k: Number of results
            filters: Optional filter conditions

        Returns:
            Cache key string
        """
        # Create a deterministic string from all parameters
        key_parts = [
            query,
            collection,
            str(top_k),
            json.dumps(filters, sort_keys=True) if filters else "",
        ]
        key_string = "|".join(key_parts)

        # Hash the key string to keep it short
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()[:16]

        return f"rag:query:{key_hash}"

    async def get(
        self,
        query: str,
        collection: str,
        top_k: int,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        """Get cached query results.

        Args:
            query: Search query string
            collection: Collection name
            top_k: Number of results
            filters: Optional filter conditions

        Returns:
            Cached results or None if not found
        """
        cache_key = self._generate_cache_key(query, collection, top_k, filters)

        try:
            client = await self._get_client()
            cached_data = await client.get(cache_key)

            if cached_data:
                logger.info(
                    "cache_hit",
                    key=cache_key,
                    query=query[:50],
                )
                return json.loads(cached_data)

            logger.debug(
                "cache_miss",
                key=cache_key,
                query=query[:50],
            )
            return None

        except Exception as e:
            logger.warning(
                "cache_get_error",
                error=str(e),
                key=cache_key,
            )
            return None

    async def set(
        self,
        query: str,
        collection: str,
        top_k: int,
        results: List[Dict[str, Any]],
        filters: Optional[Dict[str, Any]] = None,
        ttl_seconds: Optional[int] = None,
    ) -> bool:
        """Cache query results.

        Args:
            query: Search query string
            collection: Collection name
            top_k: Number of results
            results: Search results to cache
            filters: Optional filter conditions
            ttl_seconds: Optional custom TTL (overrides default)

        Returns:
            True if cached successfully
        """
        cache_key = self._generate_cache_key(query, collection, top_k, filters)
        ttl = ttl_seconds or self.ttl_seconds

        try:
            client = await self._get_client()
            serialized = json.dumps(results)

            await client.setex(cache_key, ttl, serialized)

            logger.info(
                "cache_set",
                key=cache_key,
                query=query[:50],
                ttl_seconds=ttl,
                result_count=len(results),
            )
            return True

        except Exception as e:
            logger.warning(
                "cache_set_error",
                error=str(e),
                key=cache_key,
            )
            return False

    async def invalidate(
        self,
        collection: Optional[str] = None,
        pattern: Optional[str] = None,
    ) -> int:
        """Invalidate cached results.

        Args:
            collection: Invalidate all cached results for a specific collection
            pattern: Invalidate results matching a pattern

        Returns:
            Number of keys invalidated
        """
        try:
            client = await self._get_client()

            if collection:
                # Invalidate all keys for a specific collection
                pattern = f"rag:query:*"
                keys = await client.keys(pattern)
                if keys:
                    deleted = await client.delete(*keys)
                    logger.info(
                        "cache_invalidated",
                        collection=collection,
                        count=deleted,
                    )
                    return deleted
                return 0

            elif pattern:
                keys = await client.keys(pattern)
                if keys:
                    deleted = await client.delete(*keys)
                    logger.info(
                        "cache_invalidated",
                        pattern=pattern,
                        count=deleted,
                    )
                    return deleted
                return 0

            return 0

        except Exception as e:
            logger.warning(
                "cache_invalidate_error",
                error=str(e),
            )
            return 0

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        try:
            client = await self._get_client()
            keys = await client.keys("rag:query:*")

            return {
                "total_cached_queries": len(keys),
                "ttl_seconds": self.ttl_seconds,
                "redis_url": self.redis_url,
            }

        except Exception as e:
            logger.warning(
                "cache_stats_error",
                error=str(e),
            )
            return {
                "total_cached_queries": 0,
                "ttl_seconds": self.ttl_seconds,
                "error": str(e),
            }

    async def close(self):
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None


# Singleton instance
_query_cache: Optional[QueryCache] = None


def get_query_cache() -> QueryCache:
    """Get the singleton query cache instance."""
    global _query_cache
    if _query_cache is None:
        settings = get_settings()
        _query_cache = QueryCache(
            redis_url=settings.redis_url,
            ttl_seconds=300,  # 5 minutes default
        )
    return _query_cache
