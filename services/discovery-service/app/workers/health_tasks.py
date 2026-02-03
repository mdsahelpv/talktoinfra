"""
Celery tasks for health monitoring.
"""

import asyncio
from datetime import datetime
from typing import List

from celery import shared_task

from app.config import get_settings
from app.monitoring import metrics
from app.scanners.python_async import PythonAsyncScanner
from app.scanners.base import ScanConfig
from app.services.host_manager import HostManager
from app.workers.celery_app import celery_app


@celery_app.task
def run_health_checks():
    """Run health checks on all managed hosts."""
    settings = get_settings()

    if not settings.health_check_enabled:
        return "Health checks disabled"

    async def do_health_checks():
        host_manager = HostManager()
        scanner = PythonAsyncScanner(
            {
                "python_scan_timeout": settings.health_check_timeout,
                "python_scan_concurrent": 20,
            }
        )

        # Get all managed hosts
        hosts_result = await host_manager.list_hosts(limit=10000, offset=0)
        hosts = hosts_result["items"]

        checked_count = 0
        status_changes = 0

        for host in hosts:
            try:
                # Scan the host's ports
                ports_to_check = (
                    host.ports if host.ports else settings.health_check_ports
                )

                if not ports_to_check:
                    continue

                scan_config = ScanConfig(
                    ip_range=f"{host.ip_address}/32",
                    ports=ports_to_check[:5],  # Check up to 5 ports
                    timeout=settings.health_check_timeout,
                    service_detection=False,
                )

                results = await scanner.start_scan(
                    scan_config=scan_config,
                    job_id=f"health_check_{host.id}",
                    progress_callback=None,
                )

                # Determine new status
                if results and any(r.status == "alive" for r in results):
                    new_status = "online"
                    response_time = results[0].response_time_ms if results else None
                else:
                    new_status = "offline"
                    response_time = None

                # Record health check metric
                metrics.record_health_check(new_status)

                # Update if status changed
                if new_status != host.status:
                    status_changes += 1
                    await host_manager.update_host_status(
                        host.id, new_status, response_time
                    )
                else:
                    # Just update last checked time
                    await host_manager.update_host_status(
                        host.id,
                        host.status,  # Keep current status
                        response_time,
                    )

                checked_count += 1

            except Exception as e:
                # Log error but continue with other hosts
                print(f"Health check failed for host {host.id}: {e}")
                continue

        return f"Checked {checked_count} hosts, {status_changes} status changes"

    result = asyncio.run(do_health_checks())
    return result


@celery_app.task
def cleanup_old_health_checks():
    """Clean up old health check records."""
    from datetime import datetime, timedelta
    from sqlalchemy import delete
    from app.database import AsyncSessionLocal
    from app.models import HostHealthCheck
    from app.config import get_settings

    settings = get_settings()
    cutoff_date = datetime.utcnow() - timedelta(
        days=settings.health_history_retention_days
    )

    async def do_cleanup():
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                delete(HostHealthCheck).where(HostHealthCheck.checked_at < cutoff_date)
            )
            deleted_count = result.rowcount
            await session.commit()
            return deleted_count

    deleted = asyncio.run(do_cleanup())
    return f"Cleaned up {deleted} old health check records"
