"""Authentication API Routes."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas import (
    ApiKeyCreate,
    ApiKeyResponse,
    ApiKeyWithSecret,
    ChangePasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
)
from app.services.auth_service import AuthService
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Authentication"])


async def get_current_user_id(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> uuid.UUID:
    """Get current user ID from token or API key."""
    auth_service = AuthService(db)
    
    user = None
    
    # Try Bearer token
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        user = await auth_service.get_session_by_token(token)
        if user:
            user = await auth_service.verify_token(token)
            if user:
                return uuid.UUID(user["sub"])
    
    # Try API key
    if x_api_key:
        user = await auth_service.verify_api_key(x_api_key)
        if user:
            return user.id
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user and return tokens."""
    auth_service = AuthService(db)
    user_service = UserService(db)

    # Authenticate user
    result = await auth_service.authenticate_user(
        login_data.email, login_data.password
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    user, access_token, refresh_token = result

    # Create session
    await auth_service.create_session(
        user=user,
        device_info=request.headers.get("User-Agent"),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=30 * 60,  # 30 minutes
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    token_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """Refresh access token using refresh token."""
    auth_service = AuthService(db)

    result = await auth_service.refresh_session(token_data.refresh_token)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user, access_token, refresh_token = result

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=30 * 60,
    )


@router.post("/logout")
async def logout(
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """Logout current session."""
    auth_service = AuthService(db)

    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        session = await auth_service.get_session_by_token(token)
        if session:
            await auth_service.revoke_session(session.id)

    return {"message": "Logged out successfully"}


@router.post("/logout-all")
async def logout_all(
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Logout all sessions for current user."""
    auth_service = AuthService(db)

    count = await auth_service.revoke_all_sessions(current_user_id)

    return {"message": f"Logged out {count} sessions"}


@router.post("/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Change user password."""
    user_service = UserService(db)

    try:
        await user_service.change_password(current_user_id, password_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return {"message": "Password changed successfully"}


# API Key endpoints
@router.post("/api-keys", response_model=ApiKeyWithSecret)
async def create_api_key(
    key_data: ApiKeyCreate,
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Create a new API key."""
    auth_service = AuthService(db)
    user_service = UserService(db)

    user = await user_service.get_user(current_user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    api_key_obj, api_key = await auth_service.create_api_key(
        user=user,
        name=key_data.name,
        permissions=key_data.permissions,
        expires_at=key_data.expires_at,
    )

    return ApiKeyWithSecret(
        id=api_key_obj.id,
        user_id=api_key_obj.user_id,
        name=api_key_obj.name,
        prefix=api_key_obj.prefix,
        permissions=api_key_obj.permissions,
        is_active=api_key_obj.is_active,
        created_at=api_key_obj.created_at,
        expires_at=api_key_obj.expires_at,
        last_used_at=api_key_obj.last_used_at,
        api_key=api_key,
    )


@router.get("/api-keys", response_model=list[ApiKeyResponse])
async def list_api_keys(
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List all API keys for current user."""
    user_service = UserService(db)

    keys = await user_service.get_user_api_keys(current_user_id)

    return [
        ApiKeyResponse(
            id=key.id,
            user_id=key.user_id,
            name=key.name,
            prefix=key.prefix,
            permissions=key.permissions,
            is_active=key.is_active,
            created_at=key.created_at,
            expires_at=key.expires_at,
            last_used_at=key.last_used_at,
        )
        for key in keys
    ]


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: uuid.UUID,
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Revoke an API key."""
    auth_service = AuthService(db)

    success = await auth_service.revoke_api_key(key_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    return {"message": "API key revoked successfully"}
