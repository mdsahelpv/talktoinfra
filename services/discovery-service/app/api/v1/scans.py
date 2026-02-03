"""
API endpoints for scan operations.
"""

from typing import Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.config import get_settings
from app.middleware import (
    UserContext,
    audit_log,
    get_current_user,
    # require_admin,  # TODO: Re-enable when implementing proper authorization
    require_operator,
    scan_rate_limit,
    validate_network_access,
)
from app.scanners.factory import ScannerFactory
from app.schemas import (
    ErrorResponse,
    PortPresetsListSchema,
    PortPresetSchema,
    ScanJobListSchema,
    ScanJobSchema,
    ScanResultsResponse,
    ScanStartRequest,
    ScanStatusResponse,
    ScannersListSchema,
)
from app.services.job_manager import JobManager
from app.services.scan_orchestrator import ScanOrchestrator

logger = structlog.get_logger()
router = APIRouter()

# Port presets (matching frontend)
PORT_PRESETS = {
    "common": [22, 80, 443, 5432, 6379, 8000, 8001, 8002, 8003, 8004, 8005, 8006, 6443],
    "talkai": [8000, 8001, 8002, 8003, 8004, 8005, 8006],
    "databases": [5432, 3306, 27017, 6379, 9200, 5433, 3307],
    "kubernetes": [6443, 10250, 10251, 10252, 2379, 2380, 10255, 10256],
    "web": [80, 443, 8080, 8443, 3000, 3001, 8000, 9000],
    "ssh": [22, 2222, 8022],
}


def get_orchestrator(request: Request) -> ScanOrchestrator:
    """Get orchestrator from app state."""
    return request.app.state.orchestrator


def get_job_manager(request: Request) -> JobManager:
    """Get job manager from app state."""
    return request.app.state.job_manager


@router.post(
    "/scans",
    response_model=ScanJobSchema,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
    dependencies=[Depends(scan_rate_limit)],
)
async def start_scan(
    scan_request: ScanStartRequest,
    orchestrator: ScanOrchestrator = Depends(get_orchestrator),
    current_user: UserContext = Depends(require_operator),
):
    """Start a new network scan.

    Requires operator or admin role.
    Rate limited: 5 scans per minute per user.
    Large scans (>4096 hosts) require admin approval.
    """
    settings = get_settings()

    # Validate network access (checks exclusions and approval requirements)
    try:
        validation = await validate_network_access(
            scan_request.ip_range,
            current_user,
            require_approval_threshold=settings.require_approval_threshold,
        )
    except HTTPException as e:
        await audit_log(
            action="scan_create",
            user=current_user,
            resource_type="scan",
            details={
                "ip_range": scan_request.ip_range,
                "error": e.detail,
                "scan_type": scan_request.scan_type,
            },
            success=False,
        )
        raise

    # Log scan creation attempt
    logger.info(
        "scan_creation_attempt",
        user_id=current_user.user_id,
        username=current_user.username,
        ip_range=scan_request.ip_range,
        scan_type=scan_request.scan_type,
        network_size=validation["num_addresses"],
    )

    # Start scan
    try:
        job_id = await orchestrator.execute_scan(
            scan_type=scan_request.scan_type,
            ip_range=scan_request.ip_range,
            ports=scan_request.ports,
            timeout=scan_request.timeout,
            concurrent_limit=scan_request.concurrent_limit,
            service_detection=scan_request.service_detection,
            created_by=current_user.user_id,
        )

        # Audit log success
        await audit_log(
            action="scan_create",
            user=current_user,
            resource_type="scan",
            resource_id=str(job_id),
            details={
                "ip_range": scan_request.ip_range,
                "scan_type": scan_request.scan_type,
                "network_size": validation["num_addresses"],
            },
            success=True,
        )

        # Return job info
        job = await orchestrator.job_manager.get_job(job_id)
        return job

    except Exception as e:
        # Audit log failure
        await audit_log(
            action="scan_create",
            user=current_user,
            resource_type="scan",
            details={
                "ip_range": scan_request.ip_range,
                "scan_type": scan_request.scan_type,
                "error": str(e),
            },
            success=False,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start scan: {str(e)}",
        )


@router.get(
    "/scans",
    response_model=ScanJobListSchema,
)
async def list_scans(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    job_manager: JobManager = Depends(get_job_manager),
    current_user: UserContext = Depends(get_current_user),
):
    """List scan jobs with pagination.

    Users can only see their own scans unless they are admin.
    """
    # Admins can see all scans, regular users only their own
    created_by_filter = None if current_user.is_admin else current_user.user_id

    return await job_manager.list_jobs(
        status=status,
        created_by=created_by_filter,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/scans/{job_id}",
    response_model=ScanJobSchema,
    responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def get_scan(
    job_id: UUID,
    job_manager: JobManager = Depends(get_job_manager),
    current_user: UserContext = Depends(get_current_user),
):
    """Get scan job details.

    Users can only access their own scans unless they are admin.
    """
    job = await job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Scan job not found")

    # Check authorization
    if not current_user.is_admin and job.created_by != current_user.user_id:
        logger.warning(
            "unauthorized_scan_access",
            user_id=current_user.user_id,
            job_id=str(job_id),
            job_owner=job.created_by,
        )
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to access this scan",
        )

    return job


@router.get(
    "/scans/{job_id}/status",
    response_model=ScanStatusResponse,
    responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def get_scan_status(
    job_id: UUID,
    orchestrator: ScanOrchestrator = Depends(get_orchestrator),
    current_user: UserContext = Depends(get_current_user),
):
    """Get scan job status."""
    job = await orchestrator.job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Scan job not found")

    # Check authorization
    if not current_user.is_admin and job.created_by != current_user.user_id:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to access this scan",
        )

    return ScanStatusResponse(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        total_hosts=job.total_hosts,
        scanned_hosts=job.scanned_hosts,
        found_hosts=job.found_hosts,
        current_phase=job.config.get("current_phase") if job.config else None,
        estimated_time_remaining=None,  # TODO: Calculate ETA
        message=job.error_message if job.status == "failed" else None,
    )


@router.get(
    "/scans/{job_id}/results",
    response_model=ScanResultsResponse,
    responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def get_scan_results(
    job_id: UUID,
    alive_only: bool = Query(True, description="Only return alive hosts"),
    job_manager: JobManager = Depends(get_job_manager),
    current_user: UserContext = Depends(get_current_user),
):
    """Get scan results.

    Users can only access their own scan results unless they are admin.
    """
    job = await job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Scan job not found")

    # Check authorization
    if not current_user.is_admin and job.created_by != current_user.user_id:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to access this scan",
        )

    # Check if scan is complete
    if job.status not in ["completed", "failed", "cancelled"]:
        raise HTTPException(
            status_code=400,
            detail=f"Scan is still {job.status}. Results not available yet.",
        )

    # Get results
    hosts = await job_manager.get_job_results(job_id, alive_only=alive_only)

    # Convert to schema
    from app.schemas import DiscoveredHostSchema, ScanPortSchema

    host_schemas = []
    for host in hosts:
        port_schemas = [
            ScanPortSchema(
                port=port.port,
                status=port.status,
                service=port.service,
                service_version=port.service_version,
                banner=port.banner,
                protocol=port.protocol,
            )
            for port in host.ports
        ]

        host_schemas.append(
            DiscoveredHostSchema(
                id=host.id,
                ip_address=str(host.ip_address),
                hostname=host.hostname,
                status=host.status,
                response_time_ms=host.response_time_ms,
                ports=port_schemas,
                discovered_at=host.discovered_at,
            )
        )

    # Audit log results access
    await audit_log(
        action="scan_results_access",
        user=current_user,
        resource_type="scan",
        resource_id=str(job_id),
        details={
            "total_hosts": len(host_schemas),
            "alive_only": alive_only,
        },
        success=True,
    )

    return ScanResultsResponse(
        job_id=job_id,
        status=job.status,
        total_hosts=job.total_hosts or 0,
        found_hosts=len(host_schemas),
        hosts=host_schemas,
    )


@router.delete(
    "/scans/{job_id}",
    responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def delete_scan(
    job_id: UUID,
    orchestrator: ScanOrchestrator = Depends(get_orchestrator),
    current_user: UserContext = Depends(get_current_user),
):
    """Delete a scan job and all its data.

    Users can delete their own scans. Admins can delete any scan.
    """
    # Get job to check ownership
    job = await orchestrator.job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Scan job not found")

    # Check authorization
    if not current_user.is_admin and job.created_by != current_user.user_id:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to delete this scan",
        )

    # Stop if running
    await orchestrator.stop_scan(job_id)

    # Delete from database
    success = await orchestrator.job_manager.delete_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Scan job not found")

    # Audit log
    await audit_log(
        action="scan_delete",
        user=current_user,
        resource_type="scan",
        resource_id=str(job_id),
        details={"ip_range": job.ip_range if job else None},
        success=True,
    )

    return {"message": "Scan job deleted successfully"}


@router.post(
    "/scans/{job_id}/stop",
    responses={400: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def stop_scan(
    job_id: UUID,
    orchestrator: ScanOrchestrator = Depends(get_orchestrator),
    current_user: UserContext = Depends(get_current_user),
):
    """Stop a running scan.

    Users can stop their own scans. Admins can stop any scan.
    """
    # Get job to check ownership
    job = await orchestrator.job_manager.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=400, detail="Scan not found or already completed"
        )

    # Check authorization
    if not current_user.is_admin and job.created_by != current_user.user_id:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to stop this scan",
        )

    success = await orchestrator.stop_scan(job_id)
    if not success:
        raise HTTPException(
            status_code=400, detail="Scan not found or already completed"
        )

    # Audit log
    await audit_log(
        action="scan_stop",
        user=current_user,
        resource_type="scan",
        resource_id=str(job_id),
        success=True,
    )

    return {"message": "Scan stopped successfully"}


@router.get("/scan/presets", response_model=PortPresetsListSchema)
async def get_port_presets():
    """Get available port presets. (Public endpoint)"""
    presets = [
        PortPresetSchema(name=name, description=f"Common {name} ports", ports=ports)
        for name, ports in PORT_PRESETS.items()
    ]

    return PortPresetsListSchema(presets=presets)


@router.get("/scan/scanners", response_model=ScannersListSchema)
async def get_available_scanners():
    """Get information about available scanners. (Public endpoint)"""
    scanners_info = ScannerFactory.get_available_scanners()

    # Determine recommended scanner
    settings = get_settings()
    recommended = "python"
    for scanner in scanners_info:
        if scanner["name"] == "hybrid" and scanner["available"]:
            recommended = "hybrid"
            break
        elif scanner["name"] == "detailed" and scanner["available"]:
            recommended = "detailed"

    return ScannersListSchema(
        scanners=[
            {
                "name": s["name"],
                "description": s["description"],
                "available": s["available"],
                "requires_root": s["requires_root"],
                "recommended_for": s["recommended_for"],
                "average_speed": s["average_speed"],
            }
            for s in scanners_info
        ],
        recommended=recommended,
    )


# Admin-only endpoints


@router.get(
    "/admin/scans/all",
    response_model=ScanJobListSchema,
    # TODO: Implement proper authorization in future
    # Currently using get_current_user instead of require_admin
    dependencies=[Depends(get_current_user)],
)
async def list_all_scans(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    job_manager: JobManager = Depends(get_job_manager),
    # TODO: Implement proper authorization in future
    # Currently using get_current_user instead of require_admin
    current_user: UserContext = Depends(get_current_user),
):
    """List all scan jobs (available to all authenticated users)."""
    await audit_log(
        action="admin_scan_list",
        user=current_user,
        resource_type="scan",
        details={"status_filter": status},
        success=True,
    )

    return await job_manager.list_jobs(
        status=status,
        created_by=None,  # All users
        limit=limit,
        offset=offset,
    )
