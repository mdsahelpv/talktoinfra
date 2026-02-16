"""User API Routes."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import UserStatus
from schemas import (
    SessionResponse,
    TeamCreate,
    TeamListResponse,
    TeamMemberResponse,
    TeamResponse,
    TeamUpdate,
    UserCreate,
    UserListResponse,
    UserResponse,
    UserUpdate,
)
from app.services.auth_service import AuthService
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


# User endpoints
@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new user."""
    user_service = UserService(db)

    try:
        user = await user_service.create_user(user_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return UserResponse.model_validate(user)


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    current_user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get current user profile."""
    user_service = UserService(db)

    user = await user_service.get_user(current_user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserResponse.model_validate(user)


@router.get("/me/sessions", response_model=list[SessionResponse])
async def get_my_sessions(
    current_user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get current user's sessions."""
    user_service = UserService(db)

    sessions = await user_service.get_user_sessions(current_user_id)

    return [SessionResponse.model_validate(s) for s in sessions]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get user by ID."""
    user_service = UserService(db)

    user = await user_service.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserResponse.model_validate(user)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    user_data: UserUpdate,
    current_user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Update user."""
    # Only allow users to update themselves (unless superuser)
    user_service = UserService(db)
    current_user = await user_service.get_user(current_user_id)
    
    if current_user_id != user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot update other users",
        )

    try:
        user = await user_service.update_user(user_id, user_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserResponse.model_validate(user)


@router.get("", response_model=UserListResponse)
async def list_users(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status_filter: Optional[UserStatus] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
):
    """List users with pagination."""
    user_service = UserService(db)

    total, users = await user_service.list_users(
        limit=limit, offset=offset, status=status_filter
    )

    return UserListResponse(
        total=total,
        users=[UserResponse.model_validate(u) for u in users],
    )


# Team endpoints
@router.post("/teams", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    team_data: TeamCreate,
    current_user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Create a new team."""
    user_service = UserService(db)

    team = await user_service.create_team(team_data)

    # Add current user as owner
    await user_service.add_team_member(team.id, current_user_id, "owner")

    return TeamResponse.model_validate(team)


@router.get("/teams", response_model=TeamListResponse)
async def list_teams(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List teams."""
    user_service = UserService(db)

    total, teams = await user_service.list_teams(limit=limit, offset=offset)

    return TeamListResponse(
        total=total,
        teams=[TeamResponse.model_validate(t) for t in teams],
    )


@router.get("/teams/my", response_model=list[TeamResponse])
async def get_my_teams(
    current_user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get current user's teams."""
    user_service = UserService(db)

    teams = await user_service.get_user_teams(current_user_id)

    return [TeamResponse.model_validate(t) for t in teams]


@router.get("/teams/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get team by ID."""
    user_service = UserService(db)

    team = await user_service.get_team(team_id)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    return TeamResponse.model_validate(team)


@router.patch("/teams/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: uuid.UUID,
    team_data: TeamUpdate,
    current_user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Update team."""
    user_service = UserService(db)

    team = await user_service.update_team(team_id, team_data)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    return TeamResponse.model_validate(team)


@router.post("/teams/{team_id}/members/{user_id}", status_code=status.HTTP_201_CREATED)
async def add_team_member(
    team_id: uuid.UUID,
    user_id: uuid.UUID,
    role: str = Query("member"),
    db: AsyncSession = Depends(get_db),
):
    """Add a user to a team."""
    user_service = UserService(db)

    try:
        member = await user_service.add_team_member(team_id, user_id, role)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return {"message": "User added to team", "member_id": str(member.id)}


@router.delete("/teams/{team_id}/members/{user_id}")
async def remove_team_member(
    team_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Remove a user from a team."""
    user_service = UserService(db)

    success = await user_service.remove_team_member(team_id, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    return {"message": "User removed from team"}
