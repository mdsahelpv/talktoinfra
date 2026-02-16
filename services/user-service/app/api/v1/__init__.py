"""API v1 Router."""

from fastapi import APIRouter

from app.api.v1 import auth, permissions, users

api_router = APIRouter(prefix="/api/v1")

# Include sub-routers
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(permissions.router)
