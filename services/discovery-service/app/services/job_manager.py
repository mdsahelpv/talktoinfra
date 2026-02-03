"""
Job Manager - Handles scan job CRUD and database operations.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.monitoring import metrics
from app.models import DiscoveredHost, DiscoveredPort, ScanJob
from app.scanners.base import DiscoveredHost as DiscoveredHostData
from app.schemas import ScanJobSchema


class JobManager:
    """Manages scan jobs and their lifecycle."""

    async def create_job(
        self,
        scan_type: str,
        ip_range: str,
        ports: List[int],
        total_hosts: int,
        created_by: str,
        config: dict,
    ) -> ScanJob:
        """Create a new scan job."""
        async with AsyncSessionLocal() as session:
            job = ScanJob(
                status="pending",
                scan_type=scan_type,
                ip_range=ip_range,
                ports=ports,
                total_hosts=total_hosts,
                created_by=created_by,
                config=config,
            )
            session.add(job)
            await session.commit()
            await session.refresh(job)
            return job

    async def update_job_status(
        self, job_id: UUID, status: str, error: Optional[str] = None
    ):
        """Update job status."""
        async with AsyncSessionLocal() as session:
            stmt = (
                update(ScanJob)
                .where(ScanJob.id == job_id)
                .values(status=status, error_message=error)
            )
            if status in ["completed", "failed", "cancelled"]:
                from datetime import datetime

                stmt = stmt.values(completed_at=datetime.utcnow())

            await session.execute(stmt)
            await session.commit()

    async def update_job_progress(
        self,
        job_id: UUID,
        progress: int,
        scanned_hosts: int,
        found_hosts: int,
        current_phase: Optional[str] = None,
        message: Optional[str] = None,
    ):
        """Update job progress."""
        async with AsyncSessionLocal() as session:
            stmt = (
                update(ScanJob)
                .where(ScanJob.id == job_id)
                .values(
                    progress=progress,
                    scanned_hosts=scanned_hosts,
                    found_hosts=found_hosts,
                )
            )
            await session.execute(stmt)
            await session.commit()

    async def store_discovered_hosts(
        self, job_id: UUID, hosts: List[DiscoveredHostData], scan_type: str = "unknown"
    ):
        """Store discovered hosts in database with metrics tracking."""
        async with AsyncSessionLocal() as session:
            total_ports = 0
            open_ports = 0

            for host_data in hosts:
                # Create host record
                host = DiscoveredHost(
                    job_id=job_id,
                    ip_address=host_data.ip_address,
                    hostname=host_data.hostname,
                    status=host_data.status,
                    response_time_ms=host_data.response_time_ms,
                )
                session.add(host)
                await session.flush()  # Get host.id

                # Create port records
                for port_data in host_data.ports:
                    total_ports += 1
                    if port_data.status == "open":
                        open_ports += 1

                    port = DiscoveredPort(
                        host_id=host.id,
                        port=port_data.port,
                        status=port_data.status,
                        service=port_data.service,
                        service_version=port_data.service_version,
                        banner=port_data.banner,
                        protocol=port_data.protocol,
                    )
                    session.add(port)

            await session.commit()

            # Record port metrics
            if total_ports > 0:
                metrics.record_ports_scanned(scan_type, total_ports, open_ports)

    async def get_job(self, job_id: UUID) -> Optional[ScanJobSchema]:
        """Get job by ID."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(ScanJob).where(ScanJob.id == job_id))
            job = result.scalar_one_or_none()
            if job:
                return ScanJobSchema.model_validate(job)
            return None

    async def list_jobs(
        self,
        status: Optional[str] = None,
        created_by: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ):
        """List scan jobs with pagination."""
        async with AsyncSessionLocal() as session:
            query = select(ScanJob).order_by(ScanJob.created_at.desc())

            if status:
                query = query.where(ScanJob.status == status)
            if created_by:
                query = query.where(ScanJob.created_by == created_by)

            # Get total count
            count_result = await session.execute(
                select(ScanJob).select_from(query.subquery())
            )
            total = len(count_result.scalars().all())

            # Get paginated results
            query = query.offset(offset).limit(limit)
            result = await session.execute(query)
            jobs = result.scalars().all()

            return {
                "items": [ScanJobSchema.model_validate(job) for job in jobs],
                "total": total,
                "page": offset // limit + 1,
                "page_size": limit,
                "pages": (total + limit - 1) // limit,
            }

    async def get_job_results(self, job_id: UUID, alive_only: bool = True):
        """Get scan results for a job."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(DiscoveredHost)
                .where(DiscoveredHost.job_id == job_id)
                .order_by(DiscoveredHost.ip_address)
            )
            hosts = result.scalars().all()

            if alive_only:
                hosts = [h for h in hosts if h.status == "alive"]

            return hosts

    async def cancel_job(self, job_id: UUID) -> bool:
        """Cancel a running job."""
        job = await self.get_job(job_id)
        if not job:
            return False

        if job.status == "running":
            await self.update_job_status(job_id, "cancelled")
            return True

        return False

    async def delete_job(self, job_id: UUID) -> bool:
        """Delete a job and all its data."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(ScanJob).where(ScanJob.id == job_id))
            job = result.scalar_one_or_none()

            if job:
                await session.delete(job)
                await session.commit()
                return True
            return False
