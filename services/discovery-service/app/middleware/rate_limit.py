"""
Rate limiting middleware with Redis backend.
"""

import time
from enum import Enum
from typing import Any, Dict, Optional

import redis
import structlog
from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings

logger = structlog.get_logger()


class RateLimitCategory(Enum):
    """Rate limit categories for different endpoint types."""

    SCAN = "scan"
    GENERAL = "general"
    ADMIN = "admin"
    PUBLIC = "public"


class RateLimiter:
    """Redis-backed rate limiter."""

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client
        self._local_storage: Dict[str, Dict[str, Any]] = {}

        if not self.redis:
            logger.warning(
                "redis_not_available", message="Using in-memory rate limiting"
            )

    def _get_key(self, identifier: str, category: RateLimitCategory) -> str:
        """Generate Redis key for rate limit tracking."""
        return f"ratelimit:{category.value}:{identifier}"

    def _get_window_key(
        self, identifier: str, category: RateLimitCategory, window: int
    ) -> str:
        """Get time-windowed key for sliding window rate limiting."""
        current_window = int(time.time()) // window
        return f"ratelimit:{category.value}:{identifier}:{current_window}"

    async def is_allowed(
        self,
        identifier: str,
        category: RateLimitCategory,
        max_requests: int,
        window_seconds: int = 60,
    ) -> tuple[bool, Dict[str, Any]]:
        """Check if a request is allowed under rate limit.

        Args:
            identifier: User ID or IP address
            category: Rate limit category
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds

        Returns:
            Tuple of (allowed: bool, rate_limit_info: dict)
        """
        now = time.time()

        if self.redis:
            return await self._check_redis(
                identifier, category, max_requests, window_seconds, now
            )
        else:
            return self._check_memory(
                identifier, category, max_requests, window_seconds, now
            )

    async def _check_redis(
        self,
        identifier: str,
        category: RateLimitCategory,
        max_requests: int,
        window_seconds: int,
        now: float,
    ) -> tuple[bool, Dict[str, Any]]:
        """Check rate limit using Redis."""
        key = self._get_window_key(identifier, category, window_seconds)

        try:
            pipe = self.redis.pipeline()
            pipe.incr(key)
            pipe.expire(key, window_seconds)
            results = pipe.execute()

            current_count = results[0]
            remaining = max(0, max_requests - current_count)
            reset_time = int(now) + window_seconds - (int(now) % window_seconds)

            info = {
                "limit": max_requests,
                "remaining": remaining,
                "reset": reset_time,
                "window": window_seconds,
            }

            allowed = current_count <= max_requests

            if not allowed:
                logger.warning(
                    "rate_limit_exceeded",
                    identifier=identifier,
                    category=category.value,
                    current=current_count,
                    limit=max_requests,
                )

            return allowed, info

        except redis.RedisError as e:
            logger.error("redis_rate_limit_error", error=str(e))
            # Fail open - allow request if Redis is down
            return True, {
                "limit": max_requests,
                "remaining": max_requests,
                "reset": int(now) + window_seconds,
            }

    def _check_memory(
        self,
        identifier: str,
        category: RateLimitCategory,
        max_requests: int,
        window_seconds: int,
        now: float,
    ) -> tuple[bool, Dict[str, Any]]:
        """Check rate limit using in-memory storage."""
        key = self._get_window_key(identifier, category, window_seconds)

        # Clean up expired entries periodically
        if len(self._local_storage) > 10000:
            cutoff = now - 300  # 5 minutes
            self._local_storage = {
                k: v
                for k, v in self._local_storage.items()
                if v.get("timestamp", 0) > cutoff
            }

        if key not in self._local_storage:
            self._local_storage[key] = {"count": 0, "timestamp": now}

        entry = self._local_storage[key]
        entry["count"] += 1

        current_count = entry["count"]
        remaining = max(0, max_requests - current_count)
        reset_time = int(now) + window_seconds - (int(now) % window_seconds)

        info = {
            "limit": max_requests,
            "remaining": remaining,
            "reset": reset_time,
            "window": window_seconds,
        }

        allowed = current_count <= max_requests

        if not allowed:
            logger.warning(
                "rate_limit_exceeded",
                identifier=identifier,
                category=category.value,
                current=current_count,
                limit=max_requests,
            )

        return allowed, info

    async def get_current_usage(
        self,
        identifier: str,
        category: RateLimitCategory,
        window_seconds: int = 60,
    ) -> Dict[str, Any]:
        """Get current rate limit usage for an identifier."""
        now = time.time()

        if self.redis:
            key = self._get_window_key(identifier, category, window_seconds)
            try:
                count = int(self.redis.get(key) or 0)
            except redis.RedisError:
                count = 0
        else:
            key = self._get_window_key(identifier, category, window_seconds)
            count = self._local_storage.get(key, {}).get("count", 0)

        reset_time = int(now) + window_seconds - (int(now) % window_seconds)

        return {
            "count": count,
            "reset": reset_time,
            "window": window_seconds,
        }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce rate limits on API endpoints."""

    def __init__(self, app, redis_client: Optional[redis.Redis] = None):
        super().__init__(app)
        self.limiter = RateLimiter(redis_client)
        self.settings = get_settings()

        # Configure rate limits
        self.limits = {
            RateLimitCategory.SCAN: {
                "requests": self.settings.scan_rate_limit_per_minute,
                "window": 60,
            },
            RateLimitCategory.GENERAL: {
                "requests": 100,
                "window": 60,
            },
            RateLimitCategory.ADMIN: {
                "requests": 30,
                "window": 60,
            },
            RateLimitCategory.PUBLIC: {
                "requests": 200,
                "window": 60,
            },
        }

    def _get_category_from_path(self, path: str, method: str) -> RateLimitCategory:
        """Determine rate limit category based on path and method."""
        path_lower = path.lower()

        # Scan endpoints
        if "/scans" in path_lower:
            if method == "POST":
                return RateLimitCategory.SCAN
            return RateLimitCategory.GENERAL

        # Admin operations
        if any(x in path_lower for x in ["/admin", "/delete", "/config"]):
            if method in ["POST", "PUT", "DELETE", "PATCH"]:
                return RateLimitCategory.ADMIN

        # Host management - moderate rate limit
        if "/hosts" in path_lower:
            if method in ["POST", "PUT", "DELETE", "PATCH"]:
                return RateLimitCategory.GENERAL

        return RateLimitCategory.GENERAL

    def _get_identifier(self, request: Request) -> str:
        """Get rate limiting identifier from request."""
        # Try to get user ID from state (set by auth middleware)
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"

        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"

        return f"ip:{ip}"

    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        # Skip rate limiting for health checks and metrics
        path = request.url.path
        if path in ["/health", "/metrics", "/docs", "/openapi.json"]:
            return await call_next(request)

        # Determine category and limits
        category = self._get_category_from_path(path, request.method)
        limit_config = self.limits[category]

        # Get identifier
        identifier = self._get_identifier(request)

        # Check rate limit
        allowed, info = await self.limiter.is_allowed(
            identifier,
            category,
            limit_config["requests"],
            limit_config["window"],
        )

        # Store rate limit info in request state for response headers
        request.state.rate_limit_info = info
        request.state.rate_limit_category = category.value

        if not allowed:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Try again after {info['reset']}",
                headers={
                    "X-RateLimit-Limit": str(info["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(info["reset"]),
                    "Retry-After": str(info["reset"] - int(time.time())),
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(info["reset"])
        response.headers["X-RateLimit-Category"] = category.value

        return response


class RateLimitByEndpoint:
    """Decorator/dependency for rate limiting specific endpoints."""

    def __init__(
        self,
        category: RateLimitCategory,
        max_requests: int = 100,
        window_seconds: int = 60,
    ):
        self.category = category
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.limiter = None

    async def __call__(self, request: Request):
        """Check rate limit for the request."""
        if not self.limiter:
            self.limiter = RateLimiter()

        # Get identifier
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            identifier = f"user:{user_id}"
        else:
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                ip = forwarded.split(",")[0].strip()
            else:
                ip = request.client.host if request.client else "unknown"
            identifier = f"ip:{ip}"

        allowed, info = await self.limiter.is_allowed(
            identifier,
            self.category,
            self.max_requests,
            self.window_seconds,
        )

        # Store for response headers
        request.state.endpoint_rate_limit = info

        if not allowed:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded for {self.category.value} operations",
                headers={
                    "X-RateLimit-Limit": str(info["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(info["reset"]),
                    "Retry-After": str(info["reset"] - int(time.time())),
                },
            )

        return True


# Convenience instances for use as dependencies
scan_rate_limit = RateLimitByEndpoint(
    category=RateLimitCategory.SCAN,
    max_requests=5,
    window_seconds=60,
)

general_rate_limit = RateLimitByEndpoint(
    category=RateLimitCategory.GENERAL,
    max_requests=100,
    window_seconds=60,
)

admin_rate_limit = RateLimitByEndpoint(
    category=RateLimitCategory.ADMIN,
    max_requests=30,
    window_seconds=60,
)


def get_redis_client() -> Optional[redis.Redis]:
    """Get Redis client for rate limiting."""
    settings = get_settings()
    try:
        client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            health_check_interval=30,
        )
        # Test connection
        client.ping()
        return client
    except (redis.ConnectionError, redis.TimeoutError) as e:
        logger.error("redis_connection_failed", error=str(e))
        return None
