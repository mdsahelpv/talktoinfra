"""
Redis Client Factory for Workflow Service

Provides a singleton Redis client for workflow state caching.
"""

import redis
from typing import Optional

_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """Get or create Redis client singleton."""
    global _redis_client
    if _redis_client is None:
        import os

        _redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=int(os.getenv("REDIS_DB", 0)),
            decode_responses=True,
        )
    return _redis_client


async def init_redis_client(host: str, port: int, db: int = 0) -> redis.Redis:
    """Initialize Redis client with connection details."""
    global _redis_client
    _redis_client = redis.Redis(host=host, port=port, db=db, decode_responses=True)
    return _redis_client


async def close_redis_client() -> None:
    """Close the Redis client connection."""
    global _redis_client
    if _redis_client is not None:
        _redis_client.close()
        _redis_client = None
