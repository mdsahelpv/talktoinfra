"""API versioning middleware — routes to different handler versions based on Accept-Version header."""

import logging
from datetime import datetime
from functools import wraps

from fastapi import Request, Response, APIRouter
from starlette.middleware.base import BaseHTTPMiddleware

from src.config import settings

logger = logging.getLogger(__name__)


class APIVersionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        version = request.headers.get("Accept-Version", settings.api_supported_versions.split(",")[0])
        request.state.api_version = version
        response = await call_next(request)
        response.headers["X-API-Version"] = version
        return response


def deprecated(router: APIRouter, sunset_date: str):
    """Decorator to mark a router as deprecated with a sunset date."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            sunset = datetime.fromisoformat(sunset_date)
            if datetime.utcnow() >= sunset:
                logger.warning("Deprecated endpoint called after sunset date %s", sunset_date)
            return await func(*args, **kwargs)

        return wrapper

    return decorator


class VersionRouter:
    def __init__(self) -> None:
        self._handlers: dict[str, dict[str, callable]] = {}

    def register(self, version: str, path: str, handler: callable) -> None:
        if version not in self._handlers:
            self._handlers[version] = {}
        self._handlers[version][path] = handler

    def route(self, version: str, path: str, default: callable):
        handlers = self._handlers.get(version, {})
        return handlers.get(path, default)


version_router = VersionRouter()
