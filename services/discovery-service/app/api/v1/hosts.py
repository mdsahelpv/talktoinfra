"""
API endpoints for host management.
"""

from typing import Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.middleware import (
    UserContext,
    audit_log,
    get_current_user,
    # require_admin,  # TODO: Re-enable when implementing proper authorization
    require_operator,
    general_rate_limit,
    admin_rate_limit,
)
from app.schemas import (
    AddHostRequest,
    CreateHostRequest,
    ErrorResponse,
    HostHealthHistorySchema,
    ManagedHostListSchema,
    ManagedHostSchema,
    UpdateHostRequest,
)
from app.services.host_manager import HostManager

logger = structlog.get_logger()
router = APIRouter()


def get_host_manager(request: Request) -> HostManager:
    """Get host manager from app state."""
    return request.app.state.host_manager


@router.get(
    "/hosts",
    response_model=ManagedHostListSchema,
)
async def list_hosts(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    host_manager: HostManager = Depends(get_host_manager),
    current_user: UserContext = Depends(get_current_user),
):
    """List managed hosts with pagination.

    Users can only see hosts they added unless they are admin.
    """
    # Admins can see all hosts, regular users only their own
    added_by_filter = None if current_user.is_admin else current_user.user_id

    return await host_manager.list_hosts(
        status=status,
        added_by=added_by_filter,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/hosts",
    response_model=ManagedHostSchema,
    responses={409: {"model": ErrorResponse}},
    dependencies=[Depends(general_rate_limit)],
)
async def create_host(
    request: CreateHostRequest,
    host_manager: HostManager = Depends(get_host_manager),
    current_user: UserContext = Depends(require_operator),
):
    """Create a managed host manually.

    Requires operator or admin role.
    """
    try:
        host = await host_manager.create_host(
            name=request.name,
            ip_address=request.ip_address,
            ports=request.ports,
            services=request.services,
            added_by=current_user.user_id,
            notes=request.notes,
        )

        # Audit log
        await audit_log(
            action="host_create",
            user=current_user,
            resource_type="host",
            resource_id=str(host.id),
            details={
                "name": request.name,
                "ip_address": request.ip_address,
                "ports": request.ports,
            },
            success=True,
        )

        return host
    except ValueError as e:
        await audit_log(
            action="host_create",
            user=current_user,
            resource_type="host",
            details={
                "name": request.name,
                "ip_address": request.ip_address,
                "error": str(e),
            },
            success=False,
        )
        raise HTTPException(status_code=409, detail=str(e))


@router.post(
    "/hosts/from-discovery",
    response_model=ManagedHostSchema,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
    dependencies=[Depends(general_rate_limit)],
)
async def add_host_from_discovery(
    request: AddHostRequest,
    host_manager: HostManager = Depends(get_host_manager),
    current_user: UserContext = Depends(require_operator),
):
    """Add a discovered host to managed hosts.

    Requires operator or admin role.
    """
    try:
        host = await host_manager.add_host_from_discovery(
            discovered_host_id=request.discovered_host_id,
            added_by=current_user.user_id,
            name=request.name,
            notes=request.notes,
        )

        # Audit log
        await audit_log(
            action="host_add_from_discovery",
            user=current_user,
            resource_type="host",
            resource_id=str(host.id),
            details={
                "discovered_host_id": str(request.discovered_host_id),
                "name": request.name,
            },
            success=True,
        )

        return host
    except ValueError as e:
        error_msg = str(e)
        await audit_log(
            action="host_add_from_discovery",
            user=current_user,
            resource_type="host",
            details={
                "discovered_host_id": str(request.discovered_host_id),
                "error": error_msg,
            },
            success=False,
        )
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        raise HTTPException(status_code=409, detail=error_msg)


@router.get(
    "/hosts/{host_id}",
    response_model=ManagedHostSchema,
    responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def get_host(
    host_id: UUID,
    host_manager: HostManager = Depends(get_host_manager),
    current_user: UserContext = Depends(get_current_user),
):
    """Get managed host details.

    Users can only access their own hosts unless they are admin.
    """
    host = await host_manager.get_host(host_id)
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")

    # Check authorization
    if not current_user.is_admin and host.added_by != current_user.user_id:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to access this host",
        )

    return host


@router.put(
    "/hosts/{host_id}",
    response_model=ManagedHostSchema,
    responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    dependencies=[Depends(general_rate_limit)],
)
async def update_host(
    host_id: UUID,
    request: UpdateHostRequest,
    host_manager: HostManager = Depends(get_host_manager),
    current_user: UserContext = Depends(get_current_user),
):
    """Update managed host.

    Users can update their own hosts. Admins can update any host.
    """
    # Get host to check ownership
    host = await host_manager.get_host(host_id)
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")

    # Check authorization
    if not current_user.is_admin and host.added_by != current_user.user_id:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to update this host",
        )

    success = await host_manager.update_host(
        host_id=host_id,
        name=request.name,
        notes=request.notes,
        metadata=request.metadata,
    )

    if not success:
        raise HTTPException(status_code=404, detail="Host not found")

    # Audit log
    await audit_log(
        action="host_update",
        user=current_user,
        resource_type="host",
        resource_id=str(host_id),
        details={
            "name": request.name,
            "notes_updated": request.notes is not None,
            "metadata_updated": request.metadata is not None,
        },
        success=True,
    )

    host = await host_manager.get_host(host_id)
    return host


@router.delete(
    "/hosts/{host_id}",
    responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    dependencies=[Depends(general_rate_limit)],
)
async def delete_host(
    host_id: UUID,
    host_manager: HostManager = Depends(get_host_manager),
    current_user: UserContext = Depends(get_current_user),
):
    """Delete a managed host.

    Users can delete their own hosts. Admins can delete any host.
    """
    # Get host to check ownership
    host = await host_manager.get_host(host_id)
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")

    # Check authorization
    if not current_user.is_admin and host.added_by != current_user.user_id:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to delete this host",
        )

    success = await host_manager.delete_host(host_id)
    if not success:
        raise HTTPException(status_code=404, detail="Host not found")

    # Audit log
    await audit_log(
        action="host_delete",
        user=current_user,
        resource_type="host",
        resource_id=str(host_id),
        details={"name": host.name if host else None},
        success=True,
    )

    return {"message": "Host deleted successfully"}


@router.get(
    "/hosts/{host_id}/health",
    response_model=HostHealthHistorySchema,
    responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def get_host_health_history(
    host_id: UUID,
    limit: int = Query(100, ge=1, le=1000),
    host_manager: HostManager = Depends(get_host_manager),
    current_user: UserContext = Depends(get_current_user),
):
    """Get health check history for a host.

    Users can only access their own hosts unless they are admin.
    """
    host = await host_manager.get_host(host_id)
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")

    # Check authorization
    if not current_user.is_admin and host.added_by != current_user.user_id:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to access this host",
        )

    # TODO: Implement health history query
    # For now, return empty
    return HostHealthHistorySchema(
        host_id=host_id,
        checks=[],
        uptime_percentage=0.0,
        total_checks=0,
        last_24h_status_changes=0,
    )


# Admin-only endpoints


@router.get(
    "/admin/hosts/all",
    response_model=ManagedHostListSchema,
    # TODO: Implement proper authorization in future
    # Currently using get_current_user instead of require_admin
    dependencies=[Depends(get_current_user), Depends(admin_rate_limit)],
)
async def list_all_hosts(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    host_manager: HostManager = Depends(get_host_manager),
    # TODO: Implement proper authorization in future
    # Currently using get_current_user instead of require_admin
    current_user: UserContext = Depends(get_current_user),
):
    """List all managed hosts (available to all authenticated users).

    Admin rate limit: 30 requests per minute.
    """
    await audit_log(
        action="admin_host_list",
        user=current_user,
        resource_type="host",
        details={"status_filter": status},
        success=True,
    )

    return await host_manager.list_hosts(
        status=status,
        added_by=None,  # All users
        limit=limit,
        offset=offset,
    )
