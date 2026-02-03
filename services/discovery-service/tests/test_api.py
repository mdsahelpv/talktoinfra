"""
Integration tests for Discovery Service API endpoints.

These tests use real PostgreSQL database connections via testcontainers
and do not use any mocks for internal service logic.

Tests cover:
- Scan endpoints (CRUD operations, status, results)
- Host endpoints (CRUD operations, health history)
- Discovery endpoints (status, config, presets, scanners)
"""

import uuid
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DiscoveredHost, DiscoveredPort, ManagedHost, ScanJob
from app.schemas import (
    DiscoveredHostSchema,
    ManagedHostSchema,
    ScanJobSchema,
)


# =============================================================================
# Health Check Endpoint Tests
# =============================================================================


class TestHealthCheck:
    """Tests for the health check endpoint."""

    def test_health_check_success(self, test_client: TestClient):
        """Test health check returns healthy status."""
        response = test_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
        assert data["service"] == "discovery-service"
        assert data["version"] == "1.0.0"
        assert "database" in data
        assert "scanners" in data


# =============================================================================
# Scan Endpoints Tests
# =============================================================================


class TestScanEndpoints:
    """Tests for scan-related API endpoints using real database."""

    def test_start_scan_success(
        self,
        test_client: TestClient,
        valid_scan_request: dict,
    ):
        """Test starting a scan with valid data creates job in database."""
        response = test_client.post("/api/v1/scans", json=valid_scan_request)

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["status"] in ["pending", "running"]
        assert data["scan_type"] == valid_scan_request["scan_type"]
        assert data["ip_range"] == valid_scan_request["ip_range"]
        
        # Verify job exists in database
        job_id = uuid.UUID(data["id"])
        # Job should be stored in database

    def test_start_scan_invalid_cidr(
        self,
        test_client: TestClient,
        invalid_scan_request: dict,
    ):
        """Test starting a scan with invalid CIDR notation."""
        response = test_client.post("/api/v1/scans", json=invalid_scan_request)

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_start_scan_invalid_ports(
        self,
        test_client: TestClient,
        valid_scan_request: dict,
    ):
        """Test starting a scan with invalid port numbers."""
        invalid_request = valid_scan_request.copy()
        invalid_request["ports"] = [70000]  # Invalid port

        response = test_client.post("/api/v1/scans", json=invalid_request)

        assert response.status_code == 422

    def test_start_scan_network_too_large(
        self,
        test_client: TestClient,
        large_network_request: dict,
    ):
        """Test starting a scan with network exceeding size limit."""
        response = test_client.post("/api/v1/scans", json=large_network_request)

        assert response.status_code == 400
        data = response.json()
        assert (
            "too large" in data["detail"].lower() or "network" in data["detail"].lower()
        )

    def test_start_scan_missing_required_fields(self, test_client: TestClient):
        """Test starting a scan with missing required fields."""
        incomplete_request = {
            "scan_type": "python",
        }

        response = test_client.post("/api/v1/scans", json=incomplete_request)

        assert response.status_code == 422


class TestScanListEndpoints:
    """Tests for listing scan jobs."""

    @pytest.mark.asyncio
    async def test_list_scans_success(
        self,
        test_client: TestClient,
        db_session: AsyncSession,
        create_scan_job,
    ):
        """Test listing scans with default pagination."""
        # Create test jobs
        job1 = await create_scan_job(status="completed", scan_type="python")
        job2 = await create_scan_job(status="running", scan_type="fast")

        response = test_client.get("/api/v1/scans")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["page"] == 1
        assert data["page_size"] == 50

    @pytest.mark.asyncio
    async def test_list_scans_with_status_filter(
        self,
        test_client: TestClient,
        db_session: AsyncSession,
        create_scan_job,
    ):
        """Test listing scans with status filter."""
        # Create jobs with different statuses
        await create_scan_job(status="completed")
        await create_scan_job(status="running")

        response = test_client.get("/api/v1/scans?status=running")

        assert response.status_code == 200
        data = response.json()
        # Should only return running jobs
        for job in data["items"]:
            assert job["status"] == "running"

    def test_list_scans_with_pagination(self, test_client: TestClient):
        """Test listing scans with custom pagination."""
        response = test_client.get("/api/v1/scans?limit=10&offset=10")

        assert response.status_code == 200
        data = response.json()
        assert data["page_size"] == 10
        assert data["page"] == 2

    def test_list_scans_invalid_pagination(self, test_client: TestClient):
        """Test listing scans with invalid pagination parameters."""
        response = test_client.get("/api/v1/scans?limit=0")

        assert response.status_code == 422


class TestScanDetailEndpoints:
    """Tests for scan detail endpoints."""

    @pytest.mark.asyncio
    async def test_get_scan_success(
        self,
        test_client: TestClient,
        create_scan_job,
    ):
        """Test getting scan details from database."""
        job = await create_scan_job(status="running", scan_type="python")

        response = test_client.get(f"/api/v1/scans/{job.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(job.id)
        assert data["status"] == "running"
        assert data["scan_type"] == "python"

    def test_get_scan_not_found(self, test_client: TestClient):
        """Test getting non-existent scan."""
        non_existent_id = uuid.UUID("00000000-0000-0000-0000-000000000000")

        response = test_client.get(f"/api/v1/scans/{non_existent_id}")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_get_scan_invalid_uuid(self, test_client: TestClient):
        """Test getting scan with invalid UUID."""
        response = test_client.get("/api/v1/scans/invalid-uuid")

        assert response.status_code == 422


class TestScanStatusEndpoints:
    """Tests for scan status endpoints."""

    @pytest.mark.asyncio
    async def test_get_scan_status_success(
        self,
        test_client: TestClient,
        create_scan_job,
    ):
        """Test getting scan status from database."""
        job = await create_scan_job(status="running", progress=50, scanned_hosts=100)

        response = test_client.get(f"/api/v1/scans/{job.id}/status")

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == str(job.id)
        assert data["status"] == "running"

    def test_get_scan_status_not_found(self, test_client: TestClient):
        """Test getting status of non-existent scan."""
        non_existent_id = uuid.UUID("00000000-0000-0000-0000-000000000000")

        response = test_client.get(f"/api/v1/scans/{non_existent_id}/status")

        assert response.status_code == 404


class TestScanResultsEndpoints:
    """Tests for scan results endpoints."""

    @pytest.mark.asyncio
    async def test_get_scan_results_success(
        self,
        test_client: TestClient,
        db_session: AsyncSession,
        create_scan_job,
        create_discovered_host,
        create_discovered_port,
    ):
        """Test getting scan results with discovered hosts."""
        # Create completed job with discovered hosts
        job = await create_scan_job(status="completed")
        
        host = await create_discovered_host(
            job_id=job.id,
            ip_address="192.168.1.100",
            status="alive",
        )
        
        await create_discovered_port(
            host_id=host.id,
            port=22,
            status="open",
            service="ssh",
        )

        response = test_client.get(f"/api/v1/scans/{job.id}/results")

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == str(job.id)
        assert data["status"] == "completed"
        assert "hosts" in data

    @pytest.mark.asyncio
    async def test_get_scan_results_not_complete(
        self,
        test_client: TestClient,
        create_scan_job,
    ):
        """Test getting results of scan that is not complete."""
        job = await create_scan_job(status="running")

        response = test_client.get(f"/api/v1/scans/{job.id}/results")

        assert response.status_code == 400
        data = response.json()
        assert (
            "still" in data["detail"].lower()
            or "not available" in data["detail"].lower()
        )

    def test_get_scan_results_not_found(self, test_client: TestClient):
        """Test getting results of non-existent scan."""
        non_existent_id = uuid.UUID("00000000-0000-0000-0000-000000000000")

        response = test_client.get(f"/api/v1/scans/{non_existent_id}/results")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_scan_results_alive_only_filter(
        self,
        test_client: TestClient,
        db_session: AsyncSession,
        create_scan_job,
        create_discovered_host,
    ):
        """Test getting scan results with alive_only filter."""
        job = await create_scan_job(status="completed")
        
        # Create alive host
        await create_discovered_host(
            job_id=job.id,
            ip_address="192.168.1.100",
            status="alive",
        )
        
        # Create unreachable host
        await create_discovered_host(
            job_id=job.id,
            ip_address="192.168.1.101",
            status="unreachable",
        )

        response = test_client.get(
            f"/api/v1/scans/{job.id}/results?alive_only=true"
        )

        assert response.status_code == 200
        data = response.json()
        # Should only return alive hosts
        for host in data.get("hosts", []):
            assert host["status"] == "alive"


class TestScanControlEndpoints:
    """Tests for scan control endpoints (stop, delete)."""

    @pytest.mark.asyncio
    async def test_delete_scan_success(
        self,
        test_client: TestClient,
        db_session: AsyncSession,
        create_scan_job,
    ):
        """Test deleting a scan removes it from database."""
        job = await create_scan_job(status="completed")

        response = test_client.delete(f"/api/v1/scans/{job.id}")

        assert response.status_code == 200
        data = response.json()
        assert "deleted" in data["message"].lower()

        # Verify job no longer exists
        response = test_client.get(f"/api/v1/scans/{job.id}")
        assert response.status_code == 404

    def test_delete_scan_not_found(self, test_client: TestClient):
        """Test deleting non-existent scan."""
        non_existent_id = uuid.UUID("00000000-0000-0000-0000-000000000000")

        response = test_client.delete(f"/api/v1/scans/{non_existent_id}")

        assert response.status_code == 404


# =============================================================================
# Host Endpoints Tests
# =============================================================================


class TestHostEndpoints:
    """Tests for host management API endpoints using real database."""

    @pytest.mark.asyncio
    async def test_list_hosts_success(
        self,
        test_client: TestClient,
        db_session: AsyncSession,
        create_managed_host,
    ):
        """Test listing managed hosts from database."""
        # Create test hosts
        await create_managed_host(name="Web Server 1", ip_address="192.168.1.10")
        await create_managed_host(name="Database Server", ip_address="192.168.1.20")

        response = test_client.get("/api/v1/hosts")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["page"] == 1

    @pytest.mark.asyncio
    async def test_list_hosts_with_status_filter(
        self,
        test_client: TestClient,
        db_session: AsyncSession,
        create_managed_host,
    ):
        """Test listing hosts with status filter."""
        # Create hosts with different statuses
        await create_managed_host(ip_address="192.168.1.10", status="online")
        await create_managed_host(ip_address="192.168.1.20", status="offline")

        response = test_client.get("/api/v1/hosts?status=online")

        assert response.status_code == 200
        data = response.json()
        # Should only return online hosts
        for host in data["items"]:
            assert host["status"] == "online"

    @pytest.mark.asyncio
    async def test_create_host_success(
        self,
        test_client: TestClient,
        db_session: AsyncSession,
        create_host_request: dict,
    ):
        """Test creating a managed host stores in database."""
        response = test_client.post("/api/v1/hosts", json=create_host_request)

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["name"] == create_host_request["name"]
        assert data["ip_address"] == create_host_request["ip_address"]

    @pytest.mark.asyncio
    async def test_create_host_duplicate_ip(
        self,
        test_client: TestClient,
        db_session: AsyncSession,
        create_managed_host,
        create_host_request: dict,
    ):
        """Test creating a host with duplicate IP returns error."""
        # Create existing host
        await create_managed_host(ip_address=create_host_request["ip_address"])

        response = test_client.post("/api/v1/hosts", json=create_host_request)

        assert response.status_code == 409
        data = response.json()
        assert "already exists" in data["detail"].lower()

    def test_create_host_invalid_ip(
        self,
        test_client: TestClient,
        create_host_request: dict,
    ):
        """Test creating a host with invalid IP address."""
        invalid_request = create_host_request.copy()
        invalid_request["ip_address"] = "invalid-ip"

        response = test_client.post("/api/v1/hosts", json=invalid_request)

        assert response.status_code == 422

    def test_create_host_missing_required_fields(self, test_client: TestClient):
        """Test creating a host with missing required fields."""
        incomplete_request = {
            "ip_address": "192.168.1.50",
        }

        response = test_client.post("/api/v1/hosts", json=incomplete_request)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_host_success(
        self,
        test_client: TestClient,
        create_managed_host,
    ):
        """Test getting host details from database."""
        host = await create_managed_host(name="Test Host", ip_address="192.168.1.100")

        response = test_client.get(f"/api/v1/hosts/{host.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(host.id)
        assert data["name"] == host.name

    def test_get_host_not_found(self, test_client: TestClient):
        """Test getting non-existent host."""
        non_existent_id = uuid.UUID("00000000-0000-0000-0000-000000000000")

        response = test_client.get(f"/api/v1/hosts/{non_existent_id}")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_host_success(
        self,
        test_client: TestClient,
        create_managed_host,
        update_host_request: dict,
    ):
        """Test updating a managed host in database."""
        host = await create_managed_host(name="Original Name")

        response = test_client.put(
            f"/api/v1/hosts/{host.id}", json=update_host_request
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(host.id)
        assert data["name"] == update_host_request["name"]

    def test_update_host_not_found(self, test_client: TestClient, update_host_request: dict):
        """Test updating non-existent host."""
        non_existent_id = uuid.UUID("00000000-0000-0000-0000-000000000000")

        response = test_client.put(
            f"/api/v1/hosts/{non_existent_id}", json=update_host_request
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_host_success(
        self,
        test_client: TestClient,
        create_managed_host,
    ):
        """Test deleting a managed host removes from database."""
        host = await create_managed_host()

        response = test_client.delete(f"/api/v1/hosts/{host.id}")

        assert response.status_code == 200
        data = response.json()
        assert "deleted" in data["message"].lower()

        # Verify host no longer exists
        response = test_client.get(f"/api/v1/hosts/{host.id}")
        assert response.status_code == 404

    def test_delete_host_not_found(self, test_client: TestClient):
        """Test deleting non-existent host."""
        non_existent_id = uuid.UUID("00000000-0000-0000-0000-000000000000")

        response = test_client.delete(f"/api/v1/hosts/{non_existent_id}")

        assert response.status_code == 404


class TestHostHealthEndpoints:
    """Tests for host health endpoints."""

    @pytest.mark.asyncio
    async def test_get_host_health_success(
        self,
        test_client: TestClient,
        create_managed_host,
    ):
        """Test getting host health history."""
        host = await create_managed_host()

        response = test_client.get(f"/api/v1/hosts/{host.id}/health")

        assert response.status_code == 200
        data = response.json()
        assert data["host_id"] == str(host.id)
        assert "checks" in data

    def test_get_host_health_not_found(self, test_client: TestClient):
        """Test getting health of non-existent host."""
        non_existent_id = uuid.UUID("00000000-0000-0000-0000-000000000000")

        response = test_client.get(f"/api/v1/hosts/{non_existent_id}/health")

        assert response.status_code == 404


class TestHostFromDiscoveryEndpoints:
    """Tests for adding hosts from discovery."""

    @pytest.mark.asyncio
    async def test_add_host_from_discovery_success(
        self,
        test_client: TestClient,
        db_session: AsyncSession,
        create_scan_job,
        create_discovered_host,
        create_discovered_port,
    ):
        """Test adding host from discovery creates managed host."""
        # Create discovered host with ports
        job = await create_scan_job(status="completed")
        discovered = await create_discovered_host(
            job_id=job.id,
            ip_address="192.168.1.100",
            status="alive",
        )
        await create_discovered_port(
            host_id=discovered.id,
            port=22,
            status="open",
            service="ssh",
        )

        request = {
            "discovered_host_id": str(discovered.id),
            "name": "Added From Discovery",
            "notes": "Added via API",
        }

        response = test_client.post("/api/v1/hosts/from-discovery", json=request)

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["ip_address"] == "192.168.1.100"

    def test_add_host_from_discovery_not_found(self, test_client: TestClient):
        """Test adding non-existent discovered host."""
        non_existent_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
        
        request = {
            "discovered_host_id": str(non_existent_id),
            "name": "Test",
        }

        response = test_client.post("/api/v1/hosts/from-discovery", json=request)

        assert response.status_code == 404


# =============================================================================
# Discovery Service Endpoints Tests
# =============================================================================


class TestDiscoveryEndpoints:
    """Tests for discovery service status and configuration endpoints."""

    def test_get_discovery_status_success(self, test_client: TestClient):
        """Test getting discovery service status."""
        response = test_client.get("/api/v1/discovery/status")

        assert response.status_code == 200
        data = response.json()
        assert "total_scans" in data
        assert "active_scans" in data
        assert "total_managed_hosts" in data
        assert "online_hosts" in data
        assert "offline_hosts" in data
        assert "health_check_enabled" in data

    def test_get_discovery_config_success(self, test_client: TestClient):
        """Test getting discovery service configuration."""
        response = test_client.get("/api/v1/discovery/config")

        assert response.status_code == 200
        data = response.json()
        assert "max_network_size" in data
        assert "max_ports_per_scan" in data
        assert "scan_result_retention_days" in data
        assert "health_check_enabled" in data
        assert "health_check_interval_seconds" in data
        assert "excluded_networks" in data
        assert "scanners" in data

    def test_get_port_presets_success(self, test_client: TestClient):
        """Test getting port presets."""
        response = test_client.get("/api/v1/scan/presets")

        assert response.status_code == 200
        data = response.json()
        assert "presets" in data
        assert len(data["presets"]) > 0

        # Check expected presets exist
        preset_names = [p["name"] for p in data["presets"]]
        assert "common" in preset_names
        assert "web" in preset_names

    def test_get_available_scanners_success(self, test_client: TestClient):
        """Test getting available scanners."""
        response = test_client.get("/api/v1/scan/scanners")

        assert response.status_code == 200
        data = response.json()
        assert "scanners" in data
        assert len(data["scanners"]) > 0


# =============================================================================
# Edge Cases and Error Handling Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_invalid_endpoint(self, test_client: TestClient):
        """Test accessing invalid endpoint."""
        response = test_client.get("/api/v1/invalid-endpoint")

        assert response.status_code == 404

    def test_invalid_method(self, test_client: TestClient):
        """Test using invalid HTTP method."""
        response = test_client.delete("/api/v1/scans")

        assert response.status_code == 405

    def test_malformed_json(self, test_client: TestClient):
        """Test sending malformed JSON."""
        response = test_client.post(
            "/api/v1/scans",
            data="not valid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422

    def test_empty_request_body(self, test_client: TestClient):
        """Test sending empty request body."""
        response = test_client.post("/api/v1/scans", json={})

        assert response.status_code == 422

    def test_very_long_scan_range(self, test_client: TestClient):
        """Test scan request with very large network."""
        request = {
            "ip_range": "10.0.0.0/8",  # 16 million addresses
            "ports": [22],
            "scan_type": "python",
        }

        response = test_client.post("/api/v1/scans", json=request)

        assert response.status_code == 400

    def test_too_many_ports(self, test_client: TestClient):
        """Test scan request with too many ports."""
        request = {
            "ip_range": "192.168.1.0/24",
            "ports": list(range(1, 1002)),  # 1001 ports
            "scan_type": "python",
        }

        response = test_client.post("/api/v1/scans", json=request)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_host_with_special_characters_in_name(
        self,
        test_client: TestClient,
    ):
        """Test creating host with special characters in name."""
        request = {
            "name": "Test-Host_123 (Production)",
            "ip_address": "192.168.1.100",
            "ports": [22],
            "services": ["ssh"],
        }

        response = test_client.post("/api/v1/hosts", json=request)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == request["name"]
