"""Health check endpoints."""

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    version: str
    timestamp: datetime
    service: str
    checks: Dict[str, Any]


class ReadyResponse(BaseModel):
    """Readiness check response model."""

    ready: bool
    checks: Dict[str, Any]


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Perform health check.

    Returns:
        Health status of the service

    """
    checks: Dict[str, Any] = {
        "database": "unknown",
        "vault": "not_configured",
    }

    # Check database connectivity
    try:
        from app.database import check_database_connection
        db_healthy = await check_database_connection()
        checks["database"] = "healthy" if db_healthy else "unhealthy"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"

    # Determine overall status
    overall_status = "healthy"
    if checks.get("database") != "healthy":
        overall_status = "degraded"

    return HealthResponse(
        status=overall_status,
        version="1.0.0",
        timestamp=datetime.utcnow(),
        service="onboarding-service",
        checks=checks,
    )


@router.get("/ready", response_model=ReadyResponse, tags=["Health"])
async def readiness_check() -> ReadyResponse:
    """Check if service is ready to accept traffic.

    Returns:
        Readiness status of the service

    """
    checks: Dict[str, Any] = {
        "database": False,
    }

    # Check database connectivity
    try:
        from app.database import check_database_connection
        checks["database"] = await check_database_connection()
    except Exception:
        checks["database"] = False

    is_ready = all(checks.values())

    return ReadyResponse(
        ready=is_ready,
        checks=checks,
    )
