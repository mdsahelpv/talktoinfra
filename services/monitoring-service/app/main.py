"""
Monitoring Service - Main Application Entry Point.

FastAPI application for real-time infrastructure monitoring,
alerting, anomaly detection, and self-healing automation.
"""

import structlog
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db, close_db

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup and shutdown."""
    settings = get_settings()

    # Startup
    logger.info(
        "monitoring_service_starting",
        port=settings.service_port,
        environment=settings.debug,
    )

    # Initialize database
    await init_db()

    logger.info("monitoring_service_started")

    yield

    # Shutdown
    logger.info("monitoring_service_shutting_down")
    await close_db()
    logger.info("monitoring_service_stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="TalkAI Monitoring Service",
        description="Real-time infrastructure monitoring, alerting, and self-healing",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Import and include routers
    from app.api.v1 import health, metrics, alerts, rules
    from app.api.v1 import self_healing, insights

    # Health endpoints
    app.include_router(health.router, prefix="/api/v1/health", tags=["Health"])

    # Metrics endpoints
    app.include_router(
        metrics.router, prefix="/api/v1/metrics", tags=["Metrics"])

    # Alert endpoints
    app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["Alerts"])

    # Rules endpoints
    app.include_router(rules.router, prefix="/api/v1/rules", tags=["Rules"])

    # Self-healing endpoints
    app.include_router(
        self_healing.router,
        prefix="/api/v1/self-healing",
        tags=["Self-Healing"]
    )

    # Proactive insights endpoints
    app.include_router(
        insights.router, prefix="/api/v1/insights", tags=["Insights"])

    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "service": "monitoring-service",
            "version": "1.0.0",
            "status": "running",
        }

    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.service_host,
        port=settings.service_port,
        reload=settings.debug,
    )
