"""
Test fixtures and configuration for discovery service API tests.
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import (
    DiscoveredHostSchema,
    ManagedHostSchema,
    ScanJobSchema,
    ScanPortSchema,
)


# ============== Test Data Fixtures ==============


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


@pytest.fixture
def sample_scan_jobs_list(sample_job_id: uuid.UUID) -> List[ScanJobSchema]:
    """Sample list of scan jobs."""
    return [
        ScanJobSchema(
            id=sample_job_id,
            status="completed",
            scan_type="hybrid",
            progress=100,
            ip_range="192.168.1.0/24",
            ports=[22, 80, 443],
            total_hosts=254,
            scanned_hosts=254,
            found_hosts=10,
            created_by="admin",
            started_at=datetime.utcnow() - timedelta(hours=2),
            completed_at=datetime.utcnow() - timedelta(hours=1),
            error_message=None,
            config={},
            created_at=datetime.utcnow() - timedelta(hours=2),
        ),
        ScanJobSchema(
            id=uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"),
            status="running",
            scan_type="python",
            progress=50,
            ip_range="10.0.0.0/24",
            ports=[22, 443],
            total_hosts=254,
            scanned_hosts=127,
            found_hosts=3,
            created_by="admin",
            started_at=datetime.utcnow() - timedelta(minutes=30),
            completed_at=None,
            error_message=None,
            config={},
            created_at=datetime.utcnow() - timedelta(minutes=30),
        ),
    ]


@pytest.fixture
def sample_managed_hosts_list(sample_host_id: uuid.UUID) -> List[ManagedHostSchema]:
    """Sample list of managed hosts."""
    return [
        ManagedHostSchema(
            id=sample_host_id,
            name="Web Server 1",
            ip_address="192.168.1.10",
            ports=[80, 443],
            services=["http", "https"],
            status="online",
            last_checked_at=datetime.utcnow(),
            first_discovered_at=datetime.utcnow() - timedelta(days=30),
            discovered_by_job_id=uuid.UUID("12345678-1234-5678-1234-567812345678"),
            added_at=datetime.utcnow() - timedelta(days=30),
            added_by="admin",
            notes=None,
            metadata={},
        ),
        ManagedHostSchema(
            id=uuid.UUID("bbbbbbbb-cccc-dddd-eeee-ffffffffffff"),
            name="Database Server",
            ip_address="192.168.1.20",
            ports=[5432],
            services=["postgresql"],
            status="online",
            last_checked_at=datetime.utcnow() - timedelta(minutes=5),
            first_discovered_at=datetime.utcnow() - timedelta(days=30),
            discovered_by_job_id=uuid.UUID("12345678-1234-5678-1234-567812345678"),
            added_at=datetime.utcnow() - timedelta(days=30),
            added_by="admin",
            notes="Primary database",
            metadata={"priority": "high"},
        ),
    ]


# ============== Mock Service Fixtures ==============


@pytest.fixture
def mock_job_manager():
    """Mock job manager."""
    manager = MagicMock()
    manager.get_job = AsyncMock()
    manager.list_jobs = AsyncMock()
    manager.get_job_results = AsyncMock()
    manager.delete_job = AsyncMock()
    manager.create_job = AsyncMock()
    manager.update_job_status = AsyncMock()
    manager.cancel_job = AsyncMock()
    return manager


@pytest.fixture
def mock_host_manager():
    """Mock host manager."""
    manager = MagicMock()
    manager.get_host = AsyncMock()
    manager.list_hosts = AsyncMock()
    manager.create_host = AsyncMock()
    manager.add_host_from_discovery = AsyncMock()
    manager.update_host = AsyncMock()
    manager.delete_host = AsyncMock()
    manager.get_host_count_by_status = AsyncMock()
    return manager


@pytest.fixture
def mock_orchestrator(mock_job_manager):
    """Mock scan orchestrator."""
    orchestrator = MagicMock()
    orchestrator.execute_scan = AsyncMock()
    orchestrator.stop_scan = AsyncMock()
    orchestrator.job_manager = mock_job_manager
    return orchestrator


@pytest.fixture
def mock_scanner_factory():
    """Mock scanner factory."""
    factory = MagicMock()
    factory.get_available_scanners = MagicMock(
        return_value=[
            {
                "name": "python",
                "description": "Pure Python async scanner",
                "available": True,
                "requires_root": False,
                "recommended_for": "small networks",
                "average_speed": "50 hosts/sec",
            },
            {
                "name": "fast",
                "description": "Masscan-based fast scanner",
                "available": False,
                "requires_root": True,
                "recommended_for": "large networks",
                "average_speed": "1000 hosts/sec",
            },
            {
                "name": "detailed",
                "description": "Nmap-based detailed scanner",
                "available": False,
                "requires_root": True,
                "recommended_for": "service detection",
                "average_speed": "10 hosts/sec",
            },
            {
                "name": "hybrid",
                "description": "Masscan + Nmap hybrid",
                "available": False,
                "requires_root": True,
                "recommended_for": "comprehensive scans",
                "average_speed": "500 hosts/sec",
            },
        ]
    )
    return factory


# ============== Test Client Fixtures ==============


@pytest.fixture
def test_client(mock_job_manager, mock_host_manager, mock_orchestrator):
    """Create test client with mocked services."""
    # Store original state
    original_job_manager = getattr(app.state, "job_manager", None)
    original_host_manager = getattr(app.state, "host_manager", None)
    original_orchestrator = getattr(app.state, "orchestrator", None)

    # Set mock services
    app.state.job_manager = mock_job_manager
    app.state.host_manager = mock_host_manager
    app.state.orchestrator = mock_orchestrator

    # Create test client
    client = TestClient(app)

    yield client

    # Restore original state
    if original_job_manager:
        app.state.job_manager = original_job_manager
    if original_host_manager:
        app.state.host_manager = original_host_manager
    if original_orchestrator:
        app.state.orchestrator = original_orchestrator


@pytest.fixture
def client_with_scanner_mock(
    mock_job_manager, mock_host_manager, mock_orchestrator, mock_scanner_factory
):
    """Create test client with mocked scanner factory."""
    # Store original state
    original_job_manager = getattr(app.state, "job_manager", None)
    original_host_manager = getattr(app.state, "host_manager", None)
    original_orchestrator = getattr(app.state, "orchestrator", None)

    # Set mock services
    app.state.job_manager = mock_job_manager
    app.state.host_manager = mock_host_manager
    app.state.orchestrator = mock_orchestrator

    # Patch scanner factory
    with patch("app.api.v1.scans.ScannerFactory", mock_scanner_factory):
        client = TestClient(app)
        yield client

    # Restore original state
    if original_job_manager:
        app.state.job_manager = original_job_manager
    if original_host_manager:
        app.state.host_manager = original_host_manager
    if original_orchestrator:
        app.state.orchestrator = original_orchestrator


# ============== Helper Fixtures ==============


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
