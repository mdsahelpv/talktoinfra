"""
FastAPI middleware for Prometheus metrics collection.

Tracks:
- Request counts by endpoint and status
- Request duration
- Response sizes
- Error rates
"""

import time
import re
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class PrometheusMetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect Prometheus metrics for HTTP requests."""

    def __init__(self, app: ASGIApp, exclude_paths: Optional[list] = None):
        """Initialize middleware.

        Args:
            app: FastAPI/Starlette application
            exclude_paths: List of path prefixes to exclude from metrics
        """
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/metrics", "/health"]

    def _should_track(self, path: str) -> bool:
        """Check if request should be tracked.

        Args:
            path: Request path

        Returns:
            True if path should be tracked
        """
        for exclude in self.exclude_paths:
            if path.startswith(exclude):
                return False
        return True

    def _sanitize_endpoint(self, path: str) -> str:
        """Sanitize endpoint path for metric labels.

        Removes UUIDs and IDs to group similar endpoints.

        Args:
            path: Raw request path

        Returns:
            Sanitized path suitable for metric labels
        """
        # Replace UUIDs
        path = re.sub(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            "{id}",
            path,
        )

        # Replace numeric IDs
        path = re.sub(r"/\d+", "/{id}", path)

        return path

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and collect metrics.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response from handler
        """
        from app.monitoring import metrics

        if not self._should_track(request.url.path):
            return await call_next(request)

        method = request.method
        endpoint = self._sanitize_endpoint(request.url.path)
        start_time = time.time()

        try:
            response = await call_next(request)
            status_code = str(response.status_code)

            # Track request
            metrics.http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code,
            ).inc()

            # Track duration
            duration = time.time() - start_time
            metrics.http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint,
            ).observe(duration)

            # Track response size if available
            if hasattr(response, "body"):
                try:
                    body = response.body
                    if isinstance(body, bytes):
                        metrics.http_response_size_bytes.labels(
                            method=method,
                            endpoint=endpoint,
                        ).observe(len(body))
                except:
                    pass

            return response

        except Exception as e:
            # Track failed requests
            metrics.http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status_code="500",
            ).inc()

            # Track duration even on error
            duration = time.time() - start_time
            metrics.http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint,
            ).observe(duration)

            raise


class ResponseCaptureMiddleware:
    """Alternative ASGI middleware that captures response sizes."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Track response size
        response_body_size = 0

        async def wrapped_send(message: Message) -> None:
            nonlocal response_body_size

            if message["type"] == "http.response.body":
                body = message.get("body", b"")
                response_body_size += len(body)

            await send(message)

        await self.app(scope, receive, wrapped_send)


# Import and re-export from other middleware modules
from app.middleware.rate_limit import (
    RateLimitMiddleware,
    get_redis_client,
    scan_rate_limit,
    general_rate_limit,
    admin_rate_limit,
)
from app.middleware.security import (
    SecurityMiddleware,
    UserContext,
    get_current_user,
    require_admin,
    require_operator,
    audit_log,
    validate_network_access,
)

__all__ = [
    "PrometheusMetricsMiddleware",
    "ResponseCaptureMiddleware",
    "RateLimitMiddleware",
    "SecurityMiddleware",
    "get_redis_client",
    "UserContext",
    "get_current_user",
    "require_admin",
    "require_operator",
    "scan_rate_limit",
    "general_rate_limit",
    "admin_rate_limit",
    "audit_log",
    "validate_network_access",
]
