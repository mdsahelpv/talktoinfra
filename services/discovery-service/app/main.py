"""
Main FastAPI application for Discovery Service.
"""

from contextlib import asynccontextmanager
from datetime import datetime

import structlog
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST

from app.config import get_settings
from app.database import close_db, init_db
from app.middleware import (
    PrometheusMetricsMiddleware,
    RateLimitMiddleware,
    SecurityMiddleware,
    get_redis_client,
)
from app.monitoring import metrics
from app.services.host_manager import HostManager
from app.services.job_manager import JobManager
from app.scanners.factory import ScannerFactory
from app.services.scan_orchestrator import ScanOrchestrator

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    await init_db()

    # Initialize services
    job_manager = JobManager()
    host_manager = HostManager()
    orchestrator = ScanOrchestrator(job_manager)

    # Store in app state
    app.state.job_manager = job_manager
    app.state.host_manager = host_manager
    app.state.orchestrator = orchestrator
    app.state.startup_time = datetime.utcnow()

    # Initialize Redis client for rate limiting
    app.state.redis_client = get_redis_client()
    if app.state.redis_client:
        logger.info("redis_connected", message="Rate limiting uses Redis backend")
    else:
        logger.warning(
            "redis_not_available", message="Rate limiting uses in-memory storage"
        )

    # Check scanner availability and update metrics
    for scanner_type in ["fast", "detailed", "python"]:
        try:
            scanner = ScannerFactory.create_scanner(scanner_type)
            metrics.update_scanner_availability(scanner.name, scanner.available)
        except Exception:
            metrics.update_scanner_availability(scanner_type, False)

    yield

    # Shutdown
    await close_db()
    if hasattr(app.state, "redis_client") and app.state.redis_client:
        app.state.redis_client.close()


def create_application() -> FastAPI:
    """Create FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Discovery Service",
        description="Network discovery and infrastructure scanning service",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # Security headers middleware
    app.add_middleware(SecurityMiddleware)

    # Trusted host middleware (production only)
    if not settings.debug and settings.allowed_hosts != ["*"]:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.allowed_hosts,
        )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins if not settings.debug else ["*"],
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
        expose_headers=[
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            "X-RateLimit-Category",
        ],
    )

    # Rate limiting middleware
    app.add_middleware(RateLimitMiddleware, redis_client=None)

    # Prometheus metrics middleware
    app.add_middleware(PrometheusMetricsMiddleware)

    # Exception handlers
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions with structured logging."""
        logger.warning(
            "http_exception",
            status_code=exc.status_code,
            detail=exc.detail,
            path=request.url.path,
            method=request.method,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail, "status_code": exc.status_code},
            headers=exc.headers or {},
        )

    # Health check endpoint with metrics (public, no auth required)
    @app.get("/health")
    async def health_check():
        """Health check endpoint with service metrics."""
        from sqlalchemy import text
        from app.database import engine

        # Check database connectivity
        db_healthy = True
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        except Exception:
            db_healthy = False

        # Record health check
        metrics.record_health_check("online" if db_healthy else "offline")

        # Get scanner availability
        scanner_status = {}
        for scanner_type in ["fast", "detailed", "python"]:
            try:
                scanner = ScannerFactory.create_scanner(scanner_type)
                scanner_status[scanner.name] = scanner.available
            except Exception:
                scanner_status[scanner_type] = False

        uptime = None
        if hasattr(app.state, "startup_time"):
            uptime_seconds = (
                datetime.utcnow() - app.state.startup_time
            ).total_seconds()
            uptime = f"{int(uptime_seconds // 3600)}h {int((uptime_seconds % 3600) // 60)}m {int(uptime_seconds % 60)}s"

        return {
            "status": "healthy" if db_healthy else "degraded",
            "service": settings.service_name,
            "version": "1.0.0",
            "database": "connected" if db_healthy else "disconnected",
            "scanners": scanner_status,
            "uptime": uptime,
        }

    # Readiness probe (public)
    @app.get("/ready")
    async def readiness_check():
        """Readiness check for orchestration."""
        return {"status": "ready", "service": settings.service_name}

    # Prometheus metrics endpoint
    @app.get("/metrics")
    async def prometheus_metrics():
        """Prometheus metrics endpoint for scraping."""
        return Response(
            content=metrics.get_metrics(),
            media_type=CONTENT_TYPE_LATEST,
        )

    return app


# Create the application instance
app = create_application()

# Import and include routers
from app.api.v1 import scans, hosts, discovery

app.include_router(scans.router, prefix="/api/v1", tags=["scans"])
app.include_router(hosts.router, prefix="/api/v1", tags=["hosts"])
app.include_router(discovery.router, prefix="/api/v1", tags=["discovery"])
