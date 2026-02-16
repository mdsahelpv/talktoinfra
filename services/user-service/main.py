"""User Service Main Application."""

import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Depends, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database import get_db, init_db
from schemas import HealthResponse
from app.api.v1 import api_router
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from models import User, UserStatus


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    await init_db()
    
    # Create default admin user if not exists
    async for db in get_db():
        user_service = UserService(db)
        admin = await user_service.get_user_by_email("admin@talkai.local")
        if not admin:
            try:
                await user_service.create_user(
                    UserCreate(
                        email="admin@talkai.local",
                        username="admin",
                        password="admin123",
                        full_name="System Admin",
                    )
                )
                # Make admin a superuser
                admin = await user_service.get_user_by_email("admin@talkai.local")
                if admin:
                    admin.is_superuser = True
                    await db.commit()
                print("Created default admin user")
            except Exception as e:
                print(f"Admin user creation skipped: {e}")
        break
    
    yield
    
    # Shutdown
    pass


# Create FastAPI app
app = FastAPI(
    title="TalkAI User Service",
    description="User authentication and management service",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include API router
app.include_router(api_router)


# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(status="healthy")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "user-service",
        "version": "1.0.0",
        "status": "running",
    }


# Dependency to get current user
async def get_current_user(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current authenticated user."""
    auth_service = AuthService(db)
    
    user = None
    
    # Try Bearer token
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        session = await auth_service.get_session_by_token(token)
        if session:
            result = await db.get(User, session.user_id)
            if result and result.status == UserStatus.ACTIVE:
                user = result
    
    # Try API key
    if not user and x_api_key:
        user = await auth_service.verify_api_key(x_api_key)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    
    return user


# Export for use in other modules
class UserCreate:
    """UserCreate schema for admin user creation."""
    def __init__(self, email: str, username: str, password: str, full_name: str = None):
        self.email = email
        self.username = username
        self.password = password
        self.full_name = full_name


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.service_host,
        port=settings.service_port,
        reload=True,
    )
