"""
Host Manager - Manages persistent host records.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.monitoring import metrics
from app.models import DiscoveredHost, ManagedHost
from app.schemas import ManagedHostSchema


class HostManager:
    """Manages persistent host records and their lifecycle."""

    async def _update_host_metrics(self):
        """Update managed hosts metrics."""
        counts = await self.get_host_count_by_status()
        metrics.update_managed_hosts_count(counts)

    async def add_host_from_discovery(
        self,
        discovered_host_id: UUID,
        added_by: str,
        name: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> ManagedHost:
        """Add a discovered host to managed hosts."""
        async with AsyncSessionLocal() as session:
            # Get discovered host
            result = await session.execute(
                select(DiscoveredHost).where(DiscoveredHost.id == discovered_host_id)
            )
            discovered = result.scalar_one_or_none()

            if not discovered:
                raise ValueError(f"Discovered host {discovered_host_id} not found")

            # Check if already managed
            existing_result = await session.execute(
                select(ManagedHost).where(
                    ManagedHost.ip_address == discovered.ip_address
                )
            )
            if existing_result.scalar_one_or_none():
                raise ValueError(
                    f"Host with IP {discovered.ip_address} already managed"
                )

            # Get ports from discovered host
            ports_result = await session.execute(
                select(DiscoveredPort).where(
                    DiscoveredPort.host_id == discovered_host_id,
                    DiscoveredPort.status == "open",
                )
            )
            ports = [p.port for p in ports_result.scalars().all()]

            # Get services
            services_result = await session.execute(
                select(DiscoveredPort.service)
                .where(
                    DiscoveredPort.host_id == discovered_host_id,
                    DiscoveredPort.service.isnot(None),
                )
                .distinct()
            )
            services = [s for s in services_result.scalars().all() if s]

            # Create managed host
            host_name = name or discovered.hostname or str(discovered.ip_address)

            host = ManagedHost(
                name=host_name,
                ip_address=discovered.ip_address,
                ports=ports,
                services=services,
                status="unknown",
                discovered_by_job_id=discovered.job_id,
                added_by=added_by,
                notes=notes,
                metadata={
                    "discovered_host_id": str(discovered_host_id),
                    "response_time_ms": discovered.response_time_ms,
                },
            )

            session.add(host)
            await session.commit()
            await session.refresh(host)

            # Update metrics
            await self._update_host_metrics()

            return host

    async def create_host(
        self,
        name: str,
        ip_address: str,
        ports: List[int],
        services: List[str],
        added_by: str,
        notes: Optional[str] = None,
    ) -> ManagedHost:
        """Create a managed host manually."""
        async with AsyncSessionLocal() as session:
            # Check for duplicate
            existing_result = await session.execute(
                select(ManagedHost).where(ManagedHost.ip_address == ip_address)
            )
            if existing_result.scalar_one_or_none():
                raise ValueError(f"Host with IP {ip_address} already exists")

            host = ManagedHost(
                name=name,
                ip_address=ip_address,
                ports=ports,
                services=services,
                status="unknown",
                added_by=added_by,
                notes=notes,
            )

            session.add(host)
            await session.commit()
            await session.refresh(host)

            # Update metrics
            await self._update_host_metrics()

            return host

    async def get_host(self, host_id: UUID) -> Optional[ManagedHostSchema]:
        """Get managed host by ID."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ManagedHost).where(ManagedHost.id == host_id)
            )
            host = result.scalar_one_or_none()
            if host:
                return ManagedHostSchema.model_validate(host)
            return None

    async def list_hosts(
        self,
        status: Optional[str] = None,
        added_by: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ):
        """List managed hosts with pagination."""
        async with AsyncSessionLocal() as session:
            query = select(ManagedHost).order_by(ManagedHost.added_at.desc())

            if status:
                query = query.where(ManagedHost.status == status)
            if added_by:
                query = query.where(ManagedHost.added_by == added_by)

            # Get total count
            count_result = await session.execute(
                select(ManagedHost).select_from(query.subquery())
            )
            total = len(count_result.scalars().all())

            # Get paginated results
            query = query.offset(offset).limit(limit)
            result = await session.execute(query)
            hosts = result.scalars().all()

            return {
                "items": [ManagedHostSchema.model_validate(host) for host in hosts],
                "total": total,
                "page": offset // limit + 1,
                "page_size": limit,
                "pages": (total + limit - 1) // limit,
            }

    async def update_host(
        self,
        host_id: UUID,
        name: Optional[str] = None,
        notes: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> bool:
        """Update managed host."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ManagedHost).where(ManagedHost.id == host_id)
            )
            host = result.scalar_one_or_none()

            if not host:
                return False

            if name:
                host.name = name
            if notes is not None:
                host.notes = notes
            if metadata:
                host.metadata.update(metadata)

            await session.commit()
            return True

    async def update_host_status(
        self, host_id: UUID, status: str, response_time_ms: Optional[int] = None
    ):
        """Update host status (used by health monitor)."""
        async with AsyncSessionLocal() as session:
            stmt = (
                update(ManagedHost)
                .where(ManagedHost.id == host_id)
                .values(status=status, last_checked_at=datetime.utcnow())
            )
            await session.execute(stmt)
            await session.commit()

    async def delete_host(self, host_id: UUID) -> bool:
        """Delete a managed host."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ManagedHost).where(ManagedHost.id == host_id)
            )
            host = result.scalar_one_or_none()

            if host:
                await session.delete(host)
                await session.commit()

                # Update metrics
                await self._update_host_metrics()

                return True
            return False

    async def get_host_count_by_status(self) -> dict:
        """Get count of hosts by status."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(ManagedHost))
            hosts = result.scalars().all()

            counts = {
                "total": len(hosts),
                "online": 0,
                "offline": 0,
                "unknown": 0,
                "degraded": 0,
            }
            for host in hosts:
                if host.status in counts:
                    counts[host.status] += 1

            return counts


# Need to import DiscoveredPort here to avoid circular import
from app.models import DiscoveredPort
