"""
Celery tasks for scan execution.
"""

from celery import shared_task
from app.workers.celery_app import celery_app
from app.services.scan_orchestrator import ScanOrchestrator
from app.services.job_manager import JobManager


@celery_app.task(bind=True)
def execute_scan_task(
    self, scan_type, ip_range, ports, timeout, service_detection, created_by
):
    """
    Execute a scan as a Celery task.

    Note: This is a placeholder for future distributed scanning.
    Currently scans run directly in the async orchestrator.
    """
    # This would be used if we wanted to distribute scans across workers
    # For now, scans run directly in the API request
    pass


@celery_app.task
def cleanup_old_scans():
    """Clean up old scan results based on retention policy."""
    import asyncio
    from app.config import get_settings
    from datetime import datetime, timedelta
    from sqlalchemy import delete, select
    from app.database import AsyncSessionLocal
    from app.models import ScanJob, DiscoveredHost, HostHealthCheck

    settings = get_settings()
    cutoff_date = datetime.utcnow() - timedelta(
        days=settings.scan_result_retention_days
    )

    async def do_cleanup():
        async with AsyncSessionLocal() as session:
            # Delete old completed/failed scans
            result = await session.execute(
                delete(ScanJob).where(
                    ScanJob.status.in_(["completed", "failed", "cancelled"]),
                    ScanJob.completed_at < cutoff_date,
                )
            )
            deleted_count = result.rowcount
            await session.commit()

            return deleted_count

    deleted = asyncio.run(do_cleanup())
    return f"Cleaned up {deleted} old scan jobs"
