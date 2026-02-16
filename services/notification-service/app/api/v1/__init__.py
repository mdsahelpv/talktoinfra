"""API v1 Router."""

from fastapi import APIRouter

from app.api.v1 import notifications

api_router = APIRouter(prefix="/api/v1")

# Include sub-routers
api_router.include_router(notifications.router)
