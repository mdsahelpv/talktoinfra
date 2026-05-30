"""Rate limiting middleware — sliding window per-user, per-org, and global limits."""

import time
import logging
from collections import defaultdict, deque

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.config import settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._user_calls: dict[str, deque] = defaultdict(lambda: deque(maxlen=settings.rate_limit_per_user))
        self._org_calls: dict[str, deque] = defaultdict(lambda: deque(maxlen=settings.rate_limit_per_org))
        self._global_calls: deque = deque(maxlen=settings.rate_limit_global)

    async def dispatch(self, request: Request, call_next):
        user_id = request.headers.get("X-User-Id", "anonymous")
        org_id = request.headers.get("X-Org-Id", "")

        now = time.monotonic()
        window = 60.0

        # Global limit
        while self._global_calls and now - self._global_calls[0] > window:
            self._global_calls.popleft()
        if len(self._global_calls) >= settings.rate_limit_global:
            return self._rate_limit_response("global")
        self._global_calls.append(now)

        # Per-user limit
        user_deque = self._user_calls[user_id]
        while user_deque and now - user_deque[0] > window:
            user_deque.popleft()
        if len(user_deque) >= settings.rate_limit_per_user:
            return self._rate_limit_response("user")
        user_deque.append(now)

        # Per-org limit
        if org_id:
            org_deque = self._org_calls[org_id]
            while org_deque and now - org_deque[0] > window:
                org_deque.popleft()
            if len(org_deque) >= settings.rate_limit_per_org:
                return self._rate_limit_response("org")
            org_deque.append(now)

        response: Response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(settings.rate_limit_per_user)
        response.headers["X-RateLimit-Remaining"] = str(max(0, settings.rate_limit_per_user - len(self._user_calls.get(user_id, []))))
        return response

    def _rate_limit_response(self, limit_type: str) -> Response:
        logger.warning("Rate limit exceeded (%s)", limit_type)
        return Response(
            status_code=429,
            content=f'{{"detail":"Rate limit exceeded ({limit_type})","limit_type":"{limit_type}"}}',
            media_type="application/json",
            headers={"Retry-After": "60"},
        )
