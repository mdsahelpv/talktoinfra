"""
API endpoints for Discovered Infrastructure Management.

This module provides endpoints for viewing, managing, and onboarding
all discovered infrastructure resources.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.middleware import UserContext, audit_log, get_current_user
from app.schemas_discovered import (
    BulkIgnoreRequest,
    BulkOnboardRequest,
    BulkOperationResponse,
    BulkOperationStatus,
    DiscoveredFilterRequest,
    DiscoveredInfrastructureDetail,
    DiscoveredInfrastructureResponse,
    DiscoveredStatsSchema,
    ExportRequest,
    IgnoreRequest,
    OnboardingSuggestionSchema,
    PaginatedDiscoveredResponse,
    ReScanRequest,
    ServiceCatalogResponse,
    SuggestionsResponse,
    UpdateNotesRequest,
    UpdateStateRequest,
)
from app.services.discovered_manager import DiscoveredManager

logger = structlog.get_logger()
router = APIRouter()


def get_discovered_manager(request: Request) -> DiscoveredManager:
    """Get discovered manager from app state."""
    return request.app.state.discovered_manager


@router.get("/discovered", response_model=PaginatedDiscoveredResponse)
async def list_discovered(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    infra_type: Optional[str] = Query(
        None, description="Filter by infrastructure type"),
    state: Optional[str] = Query(None, description="Filter by state"),
    search: Optional[str] = Query(None, description="Search in IP/hostname"),
    sort_by: str = Query("discovered_at", description="Sort field"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all discovered infrastructure with pagination and filtering.

    Available to all authenticated users.
    """
    manager = DiscoveredManager(db)

    # Build filters
    filters = DiscoveredFilterRequest()
    if infra_type:
        from app.schemas_discovered import InfrastructureType
        try:
            filters.infra_types = [InfrastructureType(infra_type)]
        except ValueError:
            pass

    if state:
        from app.schemas_discovered import DiscoveredState
        try:
            filters.states = [DiscoveredState(state)]
        except ValueError:
            pass

    if search:
        filters.search_query = search

    try:
        result = await manager.list_discovered(
            page=page,
            page_size=page_size,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        return result
    except Exception as e:
        logger.error("list_discovered_error", error=str(e))
        raise HTTPException(
            status_code=500, detail="Failed to list discovered infrastructure")


@router.get("/discovered/stats", response_model=DiscoveredStatsSchema)
async def get_discovered_stats(
    request: Request,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get statistics for discovered infrastructure.

    Available to all authenticated users.
    """
    manager = DiscoveredManager(db)

    try:
        stats = await manager.get_stats()
        return stats
    except Exception as e:
        logger.error("get_stats_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get statistics")


@router.get("/discovered/{item_id}", response_model=DiscoveredInfrastructureDetail)
async def get_discovered_detail(
    request: Request,
    item_id: UUID,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed information for a discovered item.

    Available to all authenticated users.
    """
    manager = DiscoveredManager(db)

    try:
        detail = await manager.get_detail(item_id)
        if not detail:
            raise HTTPException(status_code=404, detail="Item not found")

        return detail
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_detail_error", item_id=str(item_id), error=str(e))
        raise HTTPException(
            status_code=500, detail="Failed to get item details")


@router.get("/discovered/suggestions", response_model=SuggestionsResponse)
async def get_suggestions(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get smart onboarding suggestions.

    Available to all authenticated users.
    """
    manager = DiscoveredManager(db)

    try:
        suggestions = await manager.get_suggestions(limit=limit)
        return suggestions
    except Exception as e:
        logger.error("get_suggestions_error", error=str(e))
        raise HTTPException(
            status_code=500, detail="Failed to get suggestions")


@router.post("/discovered/{item_id}/onboard", response_model=DiscoveredInfrastructureResponse)
async def onboard_item(
    request: Request,
    item_id: UUID,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start onboarding workflow for a discovered item.

    Available to all authenticated users.
    """
    manager = DiscoveredManager(db)

    try:
        from app.schemas_discovered import UpdateStateRequest, DiscoveredState

        result = await manager.update_state(
            item_id,
            UpdateStateRequest(
                new_state=DiscoveredState.PENDING_ONBOARDING,
                reason="Onboarding initiated by user",
            ),
            user_id=current_user.user_id,
        )

        if not result:
            raise HTTPException(
                status_code=400, detail="Invalid state transition")

        await audit_log(
            action="discovered_onboard",
            user=current_user,
            resource_type="discovered_infrastructure",
            resource_id=str(item_id),
            success=True,
        )

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("onboard_error", item_id=str(item_id), error=str(e))
        raise HTTPException(
            status_code=500, detail="Failed to start onboarding")


@router.post("/discovered/{item_id}/ignore", response_model=DiscoveredInfrastructureResponse)
async def ignore_item(
    request: Request,
    item_id: UUID,
    ignore_request: IgnoreRequest,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a discovered item as ignored.

    Available to all authenticated users.
    """
    manager = DiscoveredManager(db)

    try:
        result = await manager.ignore_item(
            item_id,
            ignore_request,
            user_id=current_user.user_id,
        )

        if not result:
            raise HTTPException(status_code=404, detail="Item not found")

        await audit_log(
            action="discovered_ignore",
            user=current_user,
            resource_type="discovered_infrastructure",
            resource_id=str(item_id),
            details={"reason": ignore_request.reason},
            success=True,
        )

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("ignore_error", item_id=str(item_id), error=str(e))
        raise HTTPException(status_code=500, detail="Failed to ignore item")


@router.post("/discovered/{item_id}/state")
async def update_item_state(
    request: Request,
    item_id: UUID,
    state_request: UpdateStateRequest,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the state of a discovered item.

    Available to all authenticated users.
    """
    manager = DiscoveredManager(db)

    try:
        result = await manager.update_state(
            item_id,
            state_request,
            user_id=current_user.user_id,
        )

        if not result:
            raise HTTPException(
                status_code=400, detail="Invalid state transition or item not found")

        await audit_log(
            action="discovered_state_update",
            user=current_user,
            resource_type="discovered_infrastructure",
            resource_id=str(item_id),
            details={
                "from_state": state_request.new_state.value,
                "reason": state_request.reason,
            },
            success=True,
        )

        return {"message": "State updated", "item": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("update_state_error", item_id=str(item_id), error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update state")


@router.post("/discovered/bulk-onboard", response_model=BulkOperationResponse)
async def bulk_onboard(
    request: Request,
    bulk_request: BulkOnboardRequest,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Initiate bulk onboarding for multiple items.

    Available to all authenticated users.
    """
    if not bulk_request.item_ids:
        raise HTTPException(status_code=400, detail="No items specified")

    manager = DiscoveredManager(db)

    try:
        result = await manager.bulk_onboard(
            bulk_request,
            user_id=current_user.user_id,
        )

        await audit_log(
            action="discovered_bulk_onboard",
            user=current_user,
            resource_type="discovered_infrastructure",
            details={
                "target_count": len(bulk_request.item_ids),
                "action_type": bulk_request.action_type,
            },
            success=True,
        )

        return result
    except Exception as e:
        logger.error("bulk_onboard_error", error=str(e))
        raise HTTPException(
            status_code=500, detail="Failed to start bulk operation")


@router.post("/discovered/bulk-ignore")
async def bulk_ignore(
    request: Request,
    bulk_request: BulkIgnoreRequest,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Ignore multiple discovered items.

    Available to all authenticated users.
    """
    if not bulk_request.item_ids:
        raise HTTPException(status_code=400, detail="No items specified")

    manager = DiscoveredManager(db)

    try:
        from app.schemas_discovered import IgnoreRequest, DiscoveredState

        results = []
        for item_id in bulk_request.item_ids:
            result = await manager.ignore_item(
                item_id,
                IgnoreRequest(reason=bulk_request.reason),
                user_id=current_user.user_id,
            )
            if result:
                results.append(result)

        await audit_log(
            action="discovered_bulk_ignore",
            user=current_user,
            resource_type="discovered_infrastructure",
            details={
                "target_count": len(bulk_request.item_ids),
                "success_count": len(results),
                "reason": bulk_request.reason,
            },
            success=True,
        )

        return {
            "message": f"Ignored {len(results)} items",
            "ignored_count": len(results),
            "total_count": len(bulk_request.item_ids),
        }
    except Exception as e:
        logger.error("bulk_ignore_error", error=str(e))
        raise HTTPException(
            status_code=500, detail="Failed to bulk ignore items")


@router.post("/discovered/export")
async def export_discovered(
    request: Request,
    export_request: ExportRequest,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export discovered items to CSV.

    Available to all authenticated users.
    """
    manager = DiscoveredManager(db)

    try:
        csv_content = await manager.export_to_csv(export_request)

        await audit_log(
            action="discovered_export",
            user=current_user,
            resource_type="discovered_infrastructure",
            details={"format": export_request.format},
            success=True,
        )

        from fastapi.responses import Response
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=discovered_infrastructure_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
            }
        )
    except Exception as e:
        logger.error("export_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to export data")


@router.get("/discovered/services/catalog", response_model=ServiceCatalogResponse)
async def get_service_catalog(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the service catalog with discovered services.

    Available to all authenticated users.
    """
    manager = DiscoveredManager(db)

    try:
        catalog = await manager.get_service_catalog(page=page, page_size=page_size)
        return catalog
    except Exception as e:
        logger.error("service_catalog_error", error=str(e))
        raise HTTPException(
            status_code=500, detail="Failed to get service catalog")


@router.get("/discovered/bulk/{operation_id}", response_model=BulkOperationStatus)
async def get_bulk_operation_status(
    request: Request,
    operation_id: UUID,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the status of a bulk operation.

    Available to all authenticated users.
    """
    # TODO: Implement bulk operation status lookup
    return BulkOperationStatus(
        operation_id=operation_id,
        operation_type="unknown",
        status="pending",
        target_count=0,
        success_count=0,
        failed_count=0,
        progress_percent=0.0,
    )
