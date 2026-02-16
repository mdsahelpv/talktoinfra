"""Permission API Routes."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import PermissionLevel
from schemas import (
    ClusterAccessCreate,
    ClusterAccessResponse,
    ClusterAccessUpdate,
    PermissionCheckRequest,
    PermissionCheckResponse,
)
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/permissions", tags=["Permissions"])


@router.post("/check", response_model=PermissionCheckResponse)
async def check_permission(
    request: PermissionCheckRequest,
    current_user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Check if current user has permission for an action."""
    permission_service = PermissionService(db)

    try:
        cluster_id = uuid.UUID(request.resource_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid cluster ID format",
        )

    allowed, reason = await permission_service.check_resource_access(
        user_id=current_user_id,
        cluster_id=cluster_id,
        namespace=None,
        resource_kind=request.resource_type,
        action=request.action,
    )

    return PermissionCheckResponse(allowed=allowed, reason=reason)


@router.get("/clusters", response_model=list[dict])
async def get_accessible_clusters(
    current_user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get all clusters the current user has access to."""
    permission_service = PermissionService(db)

    clusters = await permission_service.get_accessible_clusters(current_user_id)

    return clusters


# Cluster Access Management (Admin endpoints)
@router.post(
    "/teams/{team_id}/clusters",
    response_model=ClusterAccessResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_cluster_access(
    team_id: uuid.UUID,
    access_data: ClusterAccessCreate,
    current_user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Create cluster access for a team."""
    # Check if user is superuser
    permission_service = PermissionService(db)
    is_super = await permission_service.is_superuser(current_user_id)
    
    if not is_super:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can manage cluster access",
        )

    from app.services.user_service import UserService
    user_service = UserService(db)

    # Verify team exists
    team = await user_service.get_team(team_id)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    access = await user_service.create_cluster_access(team_id, access_data)

    return ClusterAccessResponse(
        id=access.id,
        team_id=access.team_id,
        cluster_id=access.cluster_id,
        permission_level=access.permission_level.value,
        namespace_access=access.namespace_access,
        label_selector=access.label_selector,
        created_at=access.created_at,
        updated_at=access.updated_at,
    )


@router.get("/teams/{team_id}/clusters", response_model=list[ClusterAccessResponse])
async def get_team_cluster_access(
    team_id: uuid.UUID,
    current_user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get all cluster access for a team."""
    # Check if user is superuser or team member
    permission_service = PermissionService(db)
    is_super = await permission_service.is_superuser(current_user_id)
    
    if not is_super:
        teams = await permission_service.get_user_teams(current_user_id)
        team_ids = [t.id for t in teams]
        if team_id not in team_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this team's access",
            )

    from app.services.user_service import UserService
    user_service = UserService(db)

    accesses = await user_service.get_team_cluster_access(team_id)

    return [
        ClusterAccessResponse(
            id=access.id,
            team_id=access.team_id,
            cluster_id=access.cluster_id,
            permission_level=access.permission_level.value,
            namespace_access=access.namespace_access,
            label_selector=access.label_selector,
            created_at=access.created_at,
            updated_at=access.updated_at,
        )
        for access in accesses
    ]


@router.patch("/cluster-access/{access_id}", response_model=ClusterAccessResponse)
async def update_cluster_access(
    access_id: uuid.UUID,
    access_data: ClusterAccessUpdate,
    current_user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Update cluster access."""
    # Check if user is superuser
    permission_service = PermissionService(db)
    is_super = await permission_service.is_superuser(current_user_id)
    
    if not is_super:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can manage cluster access",
        )

    from app.services.user_service import UserService
    user_service = UserService(db)

    access = await user_service.update_cluster_access(access_id, access_data)
    if not access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cluster access not found",
        )

    return ClusterAccessResponse(
        id=access.id,
        team_id=access.team_id,
        cluster_id=access.cluster_id,
        permission_level=access.permission_level.value,
        namespace_access=access.namespace_access,
        label_selector=access.label_selector,
        created_at=access.created_at,
        updated_at=access.updated_at,
    )


@router.delete("/cluster-access/{access_id}")
async def delete_cluster_access(
    access_id: uuid.UUID,
    current_user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete cluster access."""
    # Check if user is superuser
    permission_service = PermissionService(db)
    is_super = await permission_service.is_superuser(current_user_id)
    
    if not is_super:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can manage cluster access",
        )

    from app.services.user_service import UserService
    user_service = UserService(db)

    success = await user_service.delete_cluster_access(access_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cluster access not found",
        )

    return {"message": "Cluster access deleted successfully"}
