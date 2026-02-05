"""Cost Service - Main Application.

FastAPI application for cost management and optimization.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from app.config import get_settings
from app.database import init_db, close_db
from app.api.v1 import costs, budgets, estimates, recommendations
from app.schemas import HealthCheckResponse

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("cost_service_starting", version="1.0.0")

    # Initialize database
    await init_db()
    logger.info("cost_service_database_initialized")

    yield

    # Shutdown
    logger.info("cost_service_stopping")
    await close_db()
    logger.info("cost_service_stopped")


# Create FastAPI application
app = FastAPI(
    title="Cost Management Service",
    description="Cloud cost tracking, estimation, and optimization recommendations",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(
        "unhandled_exception",
        error=str(exc),
        path=request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Include routers
app.include_router(costs.router, prefix="/api/v1")
app.include_router(budgets.router, prefix="/api/v1")
app.include_router(estimates.router, prefix="/api/v1")
app.include_router(recommendations.router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Cost Management Service",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """Health check endpoint.

    Returns:
        Health check response with service status
    """
    # Check database connection
    db_status = "healthy"
    try:
        from app.database import engine
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
    except Exception as e:
        logger.error("database_health_check_failed", error=str(e))
        db_status = "unhealthy"

    # Collector status
    collector_status: Dict[str, str] = {
        "aws": "configured" if settings.aws_cost_explorer_enabled else "disabled",
        "azure": "configured" if settings.azure_cost_management_enabled else "disabled",
        "gcp": "configured" if settings.gcp_billing_enabled else "disabled",
        "kubernetes": "configured" if settings.kubecost_enabled else "disabled",
    }

    return HealthCheckResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        version="1.0.0",
        database_status=db_status,
        cache_status="healthy",  # Placeholder
        collector_status=collector_status,
        timestamp=datetime.utcnow(),
    )


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    return {"status": "ready"}


def create_app() -> FastAPI:
    """Factory function to create the FastAPI app.

    Returns:
        Configured FastAPI application
    """
    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.service_host,
        port=settings.service_port,
        reload=settings.debug,
    )
