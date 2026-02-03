"""
API endpoints for discovery service status and information.
"""

from datetime import datetime, timedelta

import structlog
from fastapi import APIRouter, Depends, Request

from app.config import get_settings
from app.middleware import (
    UserContext,
    audit_log,
    get_current_user,
    # require_admin,  # TODO: Re-enable when implementing proper authorization
    admin_rate_limit,
)
from app.schemas import DiscoveryStatusSchema
from app.services.host_manager import HostManager
from app.services.job_manager import JobManager

logger = structlog.get_logger()
router = APIRouter()


def get_job_manager(request: Request) -> JobManager:
    """Get job manager from app state."""
    return request.app.state.job_manager


def get_host_manager(request: Request) -> HostManager:
    """Get host manager from app state."""
    return request.app.state.host_manager


@router.get("/discovery/status", response_model=DiscoveryStatusSchema)
async def get_discovery_status(
    job_manager: JobManager = Depends(get_job_manager),
    host_manager: HostManager = Depends(get_host_manager),
    current_user: UserContext = Depends(get_current_user),
):
    """Get overall discovery service status.

    Available to all authenticated users.
    """
    settings = get_settings()

    # Get scan stats
    scans_24h = await job_manager.list_jobs(limit=1000, offset=0)

    # Filter to last 24h
    cutoff = datetime.utcnow() - timedelta(hours=24)
    recent_scans = [s for s in scans_24h["items"] if s.created_at > cutoff]

    completed_24h = len([s for s in recent_scans if s.status == "completed"])
    active_scans = len([s for s in scans_24h["items"] if s.status == "running"])

    # Get host stats - respect user permissions
    if current_user.is_admin:
        host_counts = await host_manager.get_host_count_by_status()
    else:
        # For non-admin, only count their own hosts
        user_hosts = await host_manager.list_hosts(
            added_by=current_user.user_id,
            limit=10000,
            offset=0,
        )

        # Calculate counts
        online_count = len([h for h in user_hosts["items"] if h.status == "online"])
        offline_count = len([h for h in user_hosts["items"] if h.status == "offline"])
        host_counts = {
            "total": user_hosts["total"],
            "online": online_count,
            "offline": offline_count,
        }

    return DiscoveryStatusSchema(
        total_scans=scans_24h["total"],
        active_scans=active_scans,
        completed_scans_24h=completed_24h,
        total_managed_hosts=host_counts["total"],
        online_hosts=host_counts["online"],
        offline_hosts=host_counts["offline"],
        health_check_enabled=settings.health_check_enabled,
        last_health_check=None,  # TODO: Track last health check run
    )


@router.get("/discovery/config")
async def get_discovery_config(current_user: UserContext = Depends(get_current_user)):
    """Get discovery service configuration (safe values only).

    Available to all authenticated users.
    """
    settings = get_settings()

    # Base config for all users
    config = {
        "max_network_size": settings.max_network_size,
        "max_ports_per_scan": settings.max_ports_per_scan,
        "scan_result_retention_days": settings.scan_result_retention_days,
        "health_check_enabled": settings.health_check_enabled,
        "health_check_interval_seconds": settings.health_check_interval_seconds,
        "excluded_networks": settings.excluded_networks,
        "scanners": {
            "masscan_available": settings.masscan_path != "/usr/bin/masscan"
            or True,  # TODO: Check actual availability
            "nmap_available": settings.nmap_path != "/usr/bin/nmap" or True,
        },
    }

    # Admin-only configuration details
    if current_user.is_admin:
        config.update(
            {
                "rate_limits": {
                    "scan_per_minute": settings.scan_rate_limit_per_minute,
                    "api_per_minute": settings.api_rate_limit_per_minute,
                    "admin_per_minute": settings.admin_rate_limit_per_minute,
                },
                "security": {
                    "require_approval_threshold": settings.require_approval_threshold,
                    "max_concurrent_scans": settings.max_concurrent_scans,
                },
            }
        )

    # Audit log for admin access
    if current_user.is_admin:
        await audit_log(
            action="discovery_config_view",
            user=current_user,
            resource_type="config",
            details={"full_access": True},
            success=True,
        )

    return config


# Admin-only endpoints


@router.get(
    "/admin/discovery/system-status",
    # TODO: Implement proper authorization in future
    # Currently using get_current_user instead of require_admin
    dependencies=[Depends(get_current_user), Depends(admin_rate_limit)],
)
async def get_system_status(
    job_manager: JobManager = Depends(get_job_manager),
    host_manager: HostManager = Depends(get_host_manager),
    # TODO: Implement proper authorization in future
    # Currently using get_current_user instead of require_admin
    current_user: UserContext = Depends(get_current_user),
):
    """Get detailed system status (available to all authenticated users).

    Includes system-wide statistics and configuration.
    Admin rate limit: 30 requests per minute.
    """
    settings = get_settings()

    # Get all system stats
    all_scans = await job_manager.list_jobs(limit=10000, offset=0)
    all_hosts = await host_manager.list_hosts(limit=10000, offset=0)

    # Calculate statistics
    status_counts = {}
    for scan in all_scans["items"]:
        status_counts[scan.status] = status_counts.get(scan.status, 0) + 1

    host_status_counts = {}
    for host in all_hosts["items"]:
        host_status_counts[host.status] = host_status_counts.get(host.status, 0) + 1

    # Audit log
    await audit_log(
        action="admin_system_status_view",
        user=current_user,
        resource_type="system",
        details={
            "total_scans": all_scans["total"],
            "total_hosts": all_hosts["total"],
        },
        success=True,
    )

    return {
        "scans": {
            "total": all_scans["total"],
            "by_status": status_counts,
            "recent_24h": len(
                [
                    s
                    for s in all_scans["items"]
                    if s.created_at > datetime.utcnow() - timedelta(hours=24)
                ]
            ),
        },
        "hosts": {
            "total": all_hosts["total"],
            "by_status": host_status_counts,
        },
        "configuration": {
            "max_network_size": settings.max_network_size,
            "max_ports_per_scan": settings.max_ports_per_scan,
            "scan_rate_limit": settings.scan_rate_limit_per_minute,
            "max_concurrent_scans": settings.max_concurrent_scans,
            "excluded_networks_count": len(settings.excluded_networks),
        },
    }
