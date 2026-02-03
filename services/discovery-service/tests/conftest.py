"""
Test fixtures and configuration for discovery service API tests.

These fixtures use real PostgreSQL database connections via testcontainers
instead of mocks for proper integration testing.
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, AsyncGenerator, Optional

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.main import app
from app.models import Base, DiscoveredHost, DiscoveredPort, ManagedHost, ScanJob
from app.schemas import (
    DiscoveredHostSchema,
    ManagedHostSchema,
    ScanJobSchema,
    ScanPortSchema,
)


# =============================================================================
# Test Data Fixtures
# =============================================================================


@pytest.fixture
def sample_job_id() -> uuid.UUID:
    """Sample job UUID."""
    return uuid.UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture
def sample_host_id() -> uuid.UUID:
    """Sample host UUID."""
    return uuid.UUID("87654321-4321-8765-4321-876543218765")


@pytest.fixture
def sample_discovered_host_id() -> uuid.UUID:
    """Sample discovered host UUID."""
    return uuid.UUID("11111111-2222-3333-4444-555555555555")


@pytest.fixture
def sample_scan_job(sample_job_id: uuid.UUID) -> ScanJobSchema:
    """Sample scan job schema."""
    return ScanJobSchema(
        id=sample_job_id,
        status="running",
        scan_type="hybrid",
        progress=45,
        ip_range="192.168.1.0/24",
        ports=[22, 80, 443],
        total_hosts=254,
        scanned_hosts=100,
        found_hosts=5,
        created_by="admin",
        started_at=datetime.utcnow(),
        completed_at=None,
        error_message=None,
        config={"timeout": 2.0, "service_detection": True},
        created_at=datetime.utcnow(),
    )


@pytest.fixture
def sample_completed_job(sample_job_id: uuid.UUID) -> ScanJobSchema:
    """Sample completed scan job schema."""
    return ScanJobSchema(
        id=sample_job_id,
        status="completed",
        scan_type="python",
        progress=100,
        ip_range="10.0.0.0/24",
        ports=[22, 80],
        total_hosts=254,
        scanned_hosts=254,
        found_hosts=3,
        created_by="admin",
        started_at=datetime.utcnow() - timedelta(hours=1),
        completed_at=datetime.utcnow(),
        error_message=None,
        config={},
        created_at=datetime.utcnow() - timedelta(hours=1),
    )


@pytest.fixture
def sample_pending_job(sample_job_id: uuid.UUID) -> ScanJobSchema:
    """Sample pending scan job schema."""
    return ScanJobSchema(
        id=sample_job_id,
        status="pending",
        scan_type="fast",
        progress=0,
        ip_range="172.16.0.0/24",
        ports=[443],
        total_hosts=254,
        scanned_hosts=0,
        found_hosts=0,
        created_by="admin",
        started_at=datetime.utcnow(),
        completed_at=None,
        error_message=None,
        config={},
        created_at=datetime.utcnow(),
    )


@pytest.fixture
def sample_discovered_host(
    sample_discovered_host_id: uuid.UUID,
) -> DiscoveredHostSchema:
    """Sample discovered host schema."""
    return DiscoveredHostSchema(
        id=sample_discovered_host_id,
        ip_address="192.168.1.100",
        hostname="test-host",
        status="alive",
        response_time_ms=15,
        ports=[
            ScanPortSchema(
                port=22,
                status="open",
                service="ssh",
                service_version="OpenSSH_8.2",
                banner="SSH-2.0-OpenSSH_8.2",
                protocol="tcp",
            ),
            ScanPortSchema(
                port=80,
                status="open",
                service="http",
                service_version=None,
                banner=None,
                protocol="tcp",
            ),
        ],
        discovered_at=datetime.utcnow(),
    )


@pytest.fixture
def sample_managed_host(sample_host_id: uuid.UUID) -> ManagedHostSchema:
    """Sample managed host schema."""
    return ManagedHostSchema(
        id=sample_host_id,
        name="Test Server",
        ip_address="192.168.1.100",
        ports=[22, 80, 443],
        services=["ssh", "http", "https"],
        status="online",
        last_checked_at=datetime.utcnow(),
        first_discovered_at=datetime.utcnow() - timedelta(days=7),
        discovered_by_job_id=uuid.UUID("12345678-1234-5678-1234-567812345678"),
        added_at=datetime.utcnow() - timedelta(days=7),
        added_by="admin",
        notes="Test server for integration tests",
        metadata={"environment": "test"},
    )


# =============================================================================
# Database Model Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def create_scan_job(db_session: AsyncSession) -> AsyncGenerator:
    """Factory fixture to create scan jobs in database."""
    async def _create(
        status: str = "pending",
        scan_type: str = "python",
        ip_range: str = "192.168.1.0/24",
        ports: Optional[List[int]] = None,
        total_hosts: int = 254,
        created_by: str = "test-user",
    ) -> ScanJob:
        ports = ports or [22, 80, 443]
        job = ScanJob(
            status=status,
            scan_type=scan_type,
            ip_range=ip_range,
            ports=ports,
            total_hosts=total_hosts,
            created_by=created_by,
            config={"timeout": 2.0},
        )
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)
        return job
    
    yield _create


@pytest_asyncio.fixture
async def create_managed_host(db_session: AsyncSession) -> AsyncGenerator:
    """Factory fixture to create managed hosts in database."""
    async def _create(
        name: str = "Test Host",
        ip_address: str = "192.168.1.100",
        ports: Optional[List[int]] = None,
        services: Optional[List[str]] = None,
        status: str = "online",
        added_by: str = "test-user",
    ) -> ManagedHost:
        ports = ports or [22, 80, 443]
        services = services or ["ssh", "http"]
        host = ManagedHost(
            name=name,
            ip_address=ip_address,
            ports=ports,
            services=services,
            status=status,
            added_by=added_by,
        )
        db_session.add(host)
        await db_session.commit()
        await db_session.refresh(host)
        return host
    
    yield _create


@pytest_asyncio.fixture
async def create_discovered_host(db_session: AsyncSession) -> AsyncGenerator:
    """Factory fixture to create discovered hosts in database."""
    async def _create(
        job_id: uuid.UUID,
        ip_address: str = "192.168.1.100",
        hostname: str = "test-host",
        status: str = "alive",
        response_time_ms: int = 15,
    ) -> DiscoveredHost:
        host = DiscoveredHost(
            job_id=job_id,
            ip_address=ip_address,
            hostname=hostname,
            status=status,
            response_time_ms=response_time_ms,
        )
        db_session.add(host)
        await db_session.commit()
        await db_session.refresh(host)
        return host
    
    yield _create


@pytest_asyncio.fixture
async def create_discovered_port(db_session: AsyncSession) -> AsyncGenerator:
    """Factory fixture to create discovered ports in database."""
    async def _create(
        host_id: uuid.UUID,
        port: int = 22,
        status: str = "open",
        service: str = "ssh",
        service_version: Optional[str] = None,
        banner: Optional[str] = None,
        protocol: str = "tcp",
    ) -> DiscoveredPort:
        port_obj = DiscoveredPort(
            host_id=host_id,
            port=port,
            status=status,
            service=service,
            service_version=service_version,
            banner=banner,
            protocol=protocol,
        )
        db_session.add(port_obj)
        await db_session.commit()
        await db_session.refresh(port_obj)
        return port_obj
    
    yield _create


# =============================================================================
# Test Client Fixtures
# =============================================================================


@pytest.fixture
def test_client(
    postgres_url: str,
    redis_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    """Create test client with real database connections."""
    # Override database URL
    monkeypatch.setenv(
        "DATABASE_URL", 
        postgres_url.replace("postgresql+asyncpg://", "postgresql://")
    )
    monkeypatch.setenv("REDIS_URL", redis_url)
    monkeypatch.setenv("DEBUG", "true")
    
    # Create test client
    with TestClient(app) as client:
        yield client


@pytest.fixture
def client_with_db(
    db_engine,
    postgres_url: str,
    redis_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    """Create test client with database engine."""
    monkeypatch.setenv(
        "DATABASE_URL", 
        postgres_url.replace("postgresql+asyncpg://", "postgresql://")
    )
    monkeypatch.setenv("REDIS_URL", redis_url)
    monkeypatch.setenv("DEBUG", "true")
    
    with TestClient(app) as client:
        yield client


# =============================================================================
# Request Payload Fixtures
# =============================================================================


@pytest.fixture
def valid_scan_request():
    """Valid scan start request."""
    return {
        "ip_range": "192.168.1.0/24",
        "ports": [22, 80, 443],
        "scan_type": "python",
        "timeout": 2.0,
        "concurrent_limit": 50,
        "service_detection": True,
        "require_approval": False,
    }


@pytest.fixture
def invalid_scan_request():
    """Invalid scan start request (bad CIDR)."""
    return {
        "ip_range": "invalid-cidr",
        "ports": [22, 80],
        "scan_type": "python",
    }


@pytest.fixture
def large_network_request():
    """Scan request with network exceeding size limit."""
    return {
        "ip_range": "10.0.0.0/8",  # Too large
        "ports": [22, 80, 443],
        "scan_type": "python",
    }


@pytest.fixture
def create_host_request():
    """Valid create host request."""
    return {
        "name": "New Test Host",
        "ip_address": "192.168.1.50",
        "ports": [22, 80, 443],
        "services": ["ssh", "http", "https"],
        "notes": "Test host created via API",
    }


@pytest.fixture
def add_from_discovery_request(sample_discovered_host_id):
    """Valid add host from discovery request."""
    return {
        "discovered_host_id": str(sample_discovered_host_id),
        "name": "Discovered Host",
        "notes": "Added from discovery scan",
    }


@pytest.fixture
def update_host_request():
    """Valid update host request."""
    return {
        "name": "Updated Host Name",
        "notes": "Updated notes",
        "metadata": {"key": "value"},
    }


# =============================================================================
# Helper Functions
# =============================================================================


@pytest_asyncio.fixture
async def setup_test_data(
    db_session: AsyncSession,
    create_scan_job,
    create_managed_host,
    create_discovered_host,
    create_discovered_port,
):
    """Setup comprehensive test data for integration tests."""
    # Create a completed scan job
    job = await create_scan_job(
        status="completed",
        scan_type="python",
        ip_range="192.168.1.0/24",
        ports=[22, 80, 443],
        total_hosts=254,
    )
    
    # Create discovered hosts
    host1 = await create_discovered_host(
        job_id=job.id,
        ip_address="192.168.1.10",
        hostname="web-server",
        status="alive",
        response_time_ms=10,
    )
    
    await create_discovered_port(
        host_id=host1.id,
        port=80,
        status="open",
        service="http",
    )
    await create_discovered_port(
        host_id=host1.id,
        port=443,
        status="open",
        service="https",
    )
    
    host2 = await create_discovered_host(
        job_id=job.id,
        ip_address="192.168.1.20",
        hostname="db-server",
        status="alive",
        response_time_ms=20,
    )
    
    await create_discovered_port(
        host_id=host2.id,
        port=5432,
        status="open",
        service="postgresql",
    )
    
    # Create managed hosts from discovered hosts
    managed1 = await create_managed_host(
        name="Web Server",
        ip_address="192.168.1.10",
        ports=[80, 443],
        services=["http", "https"],
        status="online",
    )
    
    managed2 = await create_managed_host(
        name="Database Server",
        ip_address="192.168.1.20",
        ports=[5432],
        services=["postgresql"],
        status="online",
    )
    
    return {
        "job": job,
        "discovered_hosts": [host1, host2],
        "managed_hosts": [managed1, managed2],
    }
