"""
Integration tests for Discovery Service API endpoints.

Tests cover:
- Scan endpoints (CRUD operations, status, results)
- Host endpoints (CRUD operations, health history)
- Discovery endpoints (status, config, presets, scanners)
"""

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.schemas import (
    DiscoveredHostSchema,
    ManagedHostSchema,
    ScanJobSchema,
    ScanPortSchema,
)


# ============== Test Health Check Endpoint ==============


class TestHealthCheck:
    """Tests for the health check endpoint."""

    def test_health_check_success(self, test_client: TestClient):
        """Test health check returns healthy status."""
        response = test_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "discovery-service"
        assert data["version"] == "1.0.0"


# ============== Test Scan Endpoints ==============


class TestScanEndpoints:
    """Tests for scan-related API endpoints."""

    # POST /scans tests

    def test_start_scan_success(
        self,
        test_client: TestClient,
        mock_orchestrator: MagicMock,
        mock_job_manager: MagicMock,
        sample_job_id: uuid.UUID,
        sample_scan_job: ScanJobSchema,
        valid_scan_request: dict,
    ):
        """Test starting a scan with valid data."""
        mock_orchestrator.execute_scan.return_value = sample_job_id
        mock_job_manager.get_job.return_value = sample_scan_job

        response = test_client.post("/api/v1/scans", json=valid_scan_request)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_job_id)
        assert data["status"] == "running"
        assert data["scan_type"] == "hybrid"
        mock_orchestrator.execute_scan.assert_called_once()

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

    # GET /scans tests

    def test_list_scans_success(
        self,
        test_client: TestClient,
        mock_job_manager: MagicMock,
        sample_scan_jobs_list: list,
    ):
        """Test listing scans with default pagination."""
        mock_job_manager.list_jobs.return_value = {
            "items": sample_scan_jobs_list,
            "total": 2,
            "page": 1,
            "page_size": 50,
            "pages": 1,
        }

        response = test_client.get("/api/v1/scans")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 2
        assert data["page"] == 1
        mock_job_manager.list_jobs.assert_called_once()

    def test_list_scans_with_status_filter(
        self,
        test_client: TestClient,
        mock_job_manager: MagicMock,
    ):
        """Test listing scans with status filter."""
        mock_job_manager.list_jobs.return_value = {
            "items": [],
            "total": 0,
            "page": 1,
            "page_size": 50,
            "pages": 0,
        }

        response = test_client.get("/api/v1/scans?status=running")

        assert response.status_code == 200
        mock_job_manager.list_jobs.assert_called_once_with(
            status="running", created_by="admin", limit=50, offset=0
        )

    def test_list_scans_with_pagination(
        self,
        test_client: TestClient,
        mock_job_manager: MagicMock,
    ):
        """Test listing scans with custom pagination."""
        mock_job_manager.list_jobs.return_value = {
            "items": [],
            "total": 100,
            "page": 2,
            "page_size": 10,
            "pages": 10,
        }

        response = test_client.get("/api/v1/scans?limit=10&offset=10")

        assert response.status_code == 200
        data = response.json()
        assert data["page_size"] == 10
        assert data["page"] == 2

    def test_list_scans_invalid_pagination(self, test_client: TestClient):
        """Test listing scans with invalid pagination parameters."""
        response = test_client.get("/api/v1/scans?limit=0")

        assert response.status_code == 422

    # GET /scans/{id} tests

    def test_get_scan_success(
        self,
        test_client: TestClient,
        mock_job_manager: MagicMock,
        sample_job_id: uuid.UUID,
        sample_scan_job: ScanJobSchema,
    ):
        """Test getting scan details."""
        mock_job_manager.get_job.return_value = sample_scan_job

        response = test_client.get(f"/api/v1/scans/{sample_job_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_job_id)
        assert data["status"] == "running"
        mock_job_manager.get_job.assert_called_once_with(sample_job_id)

    def test_get_scan_not_found(
        self,
        test_client: TestClient,
        mock_job_manager: MagicMock,
    ):
        """Test getting non-existent scan."""
        mock_job_manager.get_job.return_value = None
        non_existent_id = uuid.UUID("00000000-0000-0000-0000-000000000000")

        response = test_client.get(f"/api/v1/scans/{non_existent_id}")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_get_scan_invalid_uuid(self, test_client: TestClient):
        """Test getting scan with invalid UUID."""
        response = test_client.get("/api/v1/scans/invalid-uuid")

        assert response.status_code == 422

    # GET /scans/{id}/status tests

    def test_get_scan_status_success(
        self,
        test_client: TestClient,
        mock_orchestrator: MagicMock,
        mock_job_manager: MagicMock,
        sample_job_id: uuid.UUID,
        sample_scan_job: ScanJobSchema,
    ):
        """Test getting scan status."""
        mock_job_manager.get_job.return_value = sample_scan_job

        response = test_client.get(f"/api/v1/scans/{sample_job_id}/status")

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == str(sample_job_id)
        assert data["status"] == "running"
        assert data["progress"] == 45
        assert data["scanned_hosts"] == 100
        assert data["found_hosts"] == 5

    def test_get_scan_status_not_found(
        self,
        test_client: TestClient,
        mock_orchestrator: MagicMock,
        mock_job_manager: MagicMock,
    ):
        """Test getting status of non-existent scan."""
        mock_job_manager.get_job.return_value = None
        non_existent_id = uuid.UUID("00000000-0000-0000-0000-000000000000")

        response = test_client.get(f"/api/v1/scans/{non_existent_id}/status")

        assert response.status_code == 404

    # GET /scans/{id}/results tests

    def test_get_scan_results_success(
        self,
        test_client: TestClient,
        mock_job_manager: MagicMock,
        sample_job_id: uuid.UUID,
        sample_completed_job: ScanJobSchema,
        sample_discovered_host: DiscoveredHostSchema,
    ):
        """Test getting scan results."""
        mock_job_manager.get_job.return_value = sample_completed_job
        mock_job_manager.get_job_results.return_value = [
            MagicMock(
                id=sample_discovered_host.id,
                ip_address=sample_discovered_host.ip_address,
                hostname=sample_discovered_host.hostname,
                status=sample_discovered_host.status,
                response_time_ms=sample_discovered_host.response_time_ms,
                discovered_at=sample_discovered_host.discovered_at,
                ports=[
                    MagicMock(
                        port=22,
                        status="open",
                        service="ssh",
                        service_version="OpenSSH_8.2",
                        banner="SSH-2.0-OpenSSH_8.2",
                        protocol="tcp",
                    ),
                    MagicMock(
                        port=80,
                        status="open",
                        service="http",
                        service_version=None,
                        banner=None,
                        protocol="tcp",
                    ),
                ],
            )
        ]

        response = test_client.get(f"/api/v1/scans/{sample_job_id}/results")

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == str(sample_job_id)
        assert data["status"] == "completed"
        assert len(data["hosts"]) == 1
        assert data["hosts"][0]["ip_address"] == "192.168.1.100"
        assert len(data["hosts"][0]["ports"]) == 2

    def test_get_scan_results_not_complete(
        self,
        test_client: TestClient,
        mock_job_manager: MagicMock,
        sample_job_id: uuid.UUID,
        sample_scan_job: ScanJobSchema,
    ):
        """Test getting results of scan that is not complete."""
        mock_job_manager.get_job.return_value = sample_scan_job

        response = test_client.get(f"/api/v1/scans/{sample_job_id}/results")

        assert response.status_code == 400
        data = response.json()
        assert (
            "still" in data["detail"].lower()
            or "not available" in data["detail"].lower()
        )

    def test_get_scan_results_not_found(
        self,
        test_client: TestClient,
        mock_job_manager: MagicMock,
    ):
        """Test getting results of non-existent scan."""
        mock_job_manager.get_job.return_value = None
        non_existent_id = uuid.UUID("00000000-0000-0000-0000-000000000000")

        response = test_client.get(f"/api/v1/scans/{non_existent_id}/results")

        assert response.status_code == 404

    def test_get_scan_results_alive_only_filter(
        self,
        test_client: TestClient,
        mock_job_manager: MagicMock,
        sample_job_id: uuid.UUID,
        sample_completed_job: ScanJobSchema,
    ):
        """Test getting scan results with alive_only filter."""
        mock_job_manager.get_job.return_value = sample_completed_job
        mock_job_manager.get_job_results.return_value = []

        response = test_client.get(
            f"/api/v1/scans/{sample_job_id}/results?alive_only=false"
        )

        assert response.status_code == 200
        mock_job_manager.get_job_results.assert_called_once_with(
            sample_job_id, alive_only=False
        )

    # POST /scans/{id}/stop tests

    def test_stop_scan_success(
        self,
        test_client: TestClient,
        mock_orchestrator: MagicMock,
        sample_job_id: uuid.UUID,
    ):
        """Test stopping a running scan."""
        mock_orchestrator.stop_scan.return_value = True

        response = test_client.post(f"/api/v1/scans/{sample_job_id}/stop")

        assert response.status_code == 200
        data = response.json()
        assert "stopped successfully" in data["message"].lower()
        mock_orchestrator.stop_scan.assert_called_once_with(sample_job_id)

    def test_stop_scan_not_found(
        self,
        test_client: TestClient,
        mock_orchestrator: MagicMock,
    ):
        """Test stopping non-existent scan."""
        mock_orchestrator.stop_scan.return_value = False
        non_existent_id = uuid.UUID("00000000-0000-0000-0000-000000000000")

        response = test_client.post(f"/api/v1/scans/{non_existent_id}/stop")

        assert response.status_code == 400
        data = response.json()
        assert (
            "not found" in data["detail"].lower()
            or "already completed" in data["detail"].lower()
        )

    # DELETE /scans/{id} tests

    def test_delete_scan_success(
        self,
        test_client: TestClient,
        mock_orchestrator: MagicMock,
        sample_job_id: uuid.UUID,
    ):
        """Test deleting a scan."""
        mock_orchestrator.stop_scan.return_value = True
        mock_orchestrator.job_manager.delete_job.return_value = True

        response = test_client.delete(f"/api/v1/scans/{sample_job_id}")

        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data["message"].lower()

    def test_delete_scan_not_found(
        self,
        test_client: TestClient,
        mock_orchestrator: MagicMock,
    ):
        """Test deleting non-existent scan."""
        mock_orchestrator.stop_scan.return_value = True
        mock_orchestrator.job_manager.delete_job.return_value = False
        non_existent_id = uuid.UUID("00000000-0000-0000-0000-000000000000")

        response = test_client.delete(f"/api/v1/scans/{non_existent_id}")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()


# ============== Test Host Endpoints ==============


class TestHostEndpoints:
    """Tests for host management API endpoints."""

    # GET /hosts tests

    def test_list_hosts_success(
        self,
        test_client: TestClient,
        mock_host_manager: MagicMock,
        sample_managed_hosts_list: list,
    ):
        """Test listing managed hosts."""
        mock_host_manager.list_hosts.return_value = {
            "items": sample_managed_hosts_list,
            "total": 2,
            "page": 1,
            "page_size": 50,
            "pages": 1,
        }

        response = test_client.get("/api/v1/hosts")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 2
        assert data["items"][0]["name"] == "Web Server 1"

    def test_list_hosts_with_status_filter(
        self,
        test_client: TestClient,
        mock_host_manager: MagicMock,
    ):
        """Test listing hosts with status filter."""
        mock_host_manager.list_hosts.return_value = {
            "items": [],
            "total": 0,
            "page": 1,
            "page_size": 50,
            "pages": 0,
        }

        response = test_client.get("/api/v1/hosts?status=online")

        assert response.status_code == 200
        mock_host_manager.list_hosts.assert_called_once_with(
            status="online", added_by="admin", limit=50, offset=0
        )

    def test_list_hosts_with_pagination(
        self,
        test_client: TestClient,
        mock_host_manager: MagicMock,
    ):
        """Test listing hosts with custom pagination."""
        mock_host_manager.list_hosts.return_value = {
            "items": [],
            "total": 100,
            "page": 3,
            "page_size": 25,
            "pages": 4,
        }

        response = test_client.get("/api/v1/hosts?limit=25&offset=50")

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 3
        assert data["page_size"] == 25

    # POST /hosts tests

    def test_create_host_success(
        self,
        test_client: TestClient,
        mock_host_manager: MagicMock,
        sample_host_id: uuid.UUID,
        sample_managed_host: ManagedHostSchema,
        create_host_request: dict,
    ):
        """Test creating a managed host."""
        mock_host_manager.create_host.return_value = sample_managed_host

        response = test_client.post("/api/v1/hosts", json=create_host_request)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_host_id)
        assert data["name"] == sample_managed_host.name
        assert data["ip_address"] == sample_managed_host.ip_address
        mock_host_manager.create_host.assert_called_once()

    def test_create_host_duplicate_ip(
        self,
        test_client: TestClient,
        mock_host_manager: MagicMock,
        create_host_request: dict,
    ):
        """Test creating a host with duplicate IP."""
        mock_host_manager.create_host.side_effect = ValueError(
            "Host with IP 192.168.1.50 already exists"
        )

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

    # POST /hosts/from-discovery tests

    def test_add_host_from_discovery_success(
        self,
        test_client: TestClient,
        mock_host_manager: MagicMock,
        sample_host_id: uuid.UUID,
        sample_managed_host: ManagedHostSchema,
        add_from_discovery_request: dict,
    ):
        """Test adding host from discovery."""
        mock_host_manager.add_host_from_discovery.return_value = sample_managed_host

        response = test_client.post(
            "/api/v1/hosts/from-discovery", json=add_from_discovery_request
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_host_id)
        mock_host_manager.add_host_from_discovery.assert_called_once()

    def test_add_host_from_discovery_not_found(
        self,
        test_client: TestClient,
        mock_host_manager: MagicMock,
        add_from_discovery_request: dict,
    ):
        """Test adding non-existent discovered host."""
        mock_host_manager.add_host_from_discovery.side_effect = ValueError(
            "Discovered host 11111111-2222-3333-4444-555555555555 not found"
        )

        response = test_client.post(
            "/api/v1/hosts/from-discovery", json=add_from_discovery_request
        )

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_add_host_from_discovery_duplicate(
        self,
        test_client: TestClient,
        mock_host_manager: MagicMock,
        add_from_discovery_request: dict,
    ):
        """Test adding already managed host from discovery."""
        mock_host_manager.add_host_from_discovery.side_effect = ValueError(
            "Host with IP 192.168.1.100 already managed"
        )

        response = test_client.post(
            "/api/v1/hosts/from-discovery", json=add_from_discovery_request
        )

        assert response.status_code == 409
        data = response.json()
        assert "already managed" in data["detail"].lower()

    def test_add_host_from_discovery_invalid_uuid(self, test_client: TestClient):
        """Test adding host with invalid discovered host UUID."""
        invalid_request = {
            "discovered_host_id": "invalid-uuid",
        }

        response = test_client.post(
            "/api/v1/hosts/from-discovery", json=invalid_request
        )

        assert response.status_code == 422

    # GET /hosts/{id} tests

    def test_get_host_success(
        self,
        test_client: TestClient,
        mock_host_manager: MagicMock,
        sample_host_id: uuid.UUID,
        sample_managed_host: ManagedHostSchema,
    ):
        """Test getting host details."""
        mock_host_manager.get_host.return_value = sample_managed_host

        response = test_client.get(f"/api/v1/hosts/{sample_host_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_host_id)
        assert data["name"] == sample_managed_host.name
        mock_host_manager.get_host.assert_called_once_with(sample_host_id)

    def test_get_host_not_found(
        self,
        test_client: TestClient,
        mock_host_manager: MagicMock,
    ):
        """Test getting non-existent host."""
        mock_host_manager.get_host.return_value = None
        non_existent_id = uuid.UUID("00000000-0000-0000-0000-000000000000")

        response = test_client.get(f"/api/v1/hosts/{non_existent_id}")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    # PUT /hosts/{id} tests

    def test_update_host_success(
        self,
        test_client: TestClient,
        mock_host_manager: MagicMock,
        sample_host_id: uuid.UUID,
        sample_managed_host: ManagedHostSchema,
        update_host_request: dict,
    ):
        """Test updating a managed host."""
        mock_host_manager.update_host.return_value = True
        mock_host_manager.get_host.return_value = sample_managed_host

        response = test_client.put(
            f"/api/v1/hosts/{sample_host_id}", json=update_host_request
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_host_id)
        mock_host_manager.update_host.assert_called_once()

    def test_update_host_not_found(
        self,
        test_client: TestClient,
        mock_host_manager: MagicMock,
        update_host_request: dict,
    ):
        """Test updating non-existent host."""
        mock_host_manager.update_host.return_value = False
        non_existent_id = uuid.UUID("00000000-0000-0000-0000-000000000000")

        response = test_client.put(
            f"/api/v1/hosts/{non_existent_id}", json=update_host_request
        )

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_update_host_partial_fields(
        self,
        test_client: TestClient,
        mock_host_manager: MagicMock,
        sample_host_id: uuid.UUID,
        sample_managed_host: ManagedHostSchema,
    ):
        """Test updating host with partial fields."""
        mock_host_manager.update_host.return_value = True
        mock_host_manager.get_host.return_value = sample_managed_host

        partial_update = {"notes": "Only updating notes"}
        response = test_client.put(
            f"/api/v1/hosts/{sample_host_id}", json=partial_update
        )

        assert response.status_code == 200

    # DELETE /hosts/{id} tests

    def test_delete_host_success(
        self,
        test_client: TestClient,
        mock_host_manager: MagicMock,
        sample_host_id: uuid.UUID,
    ):
        """Test deleting a managed host."""
        mock_host_manager.delete_host.return_value = True

        response = test_client.delete(f"/api/v1/hosts/{sample_host_id}")

        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data["message"].lower()
        mock_host_manager.delete_host.assert_called_once_with(sample_host_id)

    def test_delete_host_not_found(
        self,
        test_client: TestClient,
        mock_host_manager: MagicMock,
    ):
        """Test deleting non-existent host."""
        mock_host_manager.delete_host.return_value = False
        non_existent_id = uuid.UUID("00000000-0000-0000-0000-000000000000")

        response = test_client.delete(f"/api/v1/hosts/{non_existent_id}")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    # GET /hosts/{id}/health tests

    def test_get_host_health_success(
        self,
        test_client: TestClient,
        mock_host_manager: MagicMock,
        sample_host_id: uuid.UUID,
        sample_managed_host: ManagedHostSchema,
    ):
        """Test getting host health history."""
        mock_host_manager.get_host.return_value = sample_managed_host

        response = test_client.get(f"/api/v1/hosts/{sample_host_id}/health")

        assert response.status_code == 200
        data = response.json()
        assert data["host_id"] == str(sample_host_id)
        assert "checks" in data
        assert "uptime_percentage" in data

    def test_get_host_health_not_found(
        self,
        test_client: TestClient,
        mock_host_manager: MagicMock,
    ):
        """Test getting health of non-existent host."""
        mock_host_manager.get_host.return_value = None
        non_existent_id = uuid.UUID("00000000-0000-0000-0000-000000000000")

        response = test_client.get(f"/api/v1/hosts/{non_existent_id}/health")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_get_host_health_with_limit(
        self,
        test_client: TestClient,
        mock_host_manager: MagicMock,
        sample_host_id: uuid.UUID,
        sample_managed_host: ManagedHostSchema,
    ):
        """Test getting host health with custom limit."""
        mock_host_manager.get_host.return_value = sample_managed_host

        response = test_client.get(f"/api/v1/hosts/{sample_host_id}/health?limit=50")

        assert response.status_code == 200


# ============== Test Discovery Endpoints ==============


class TestDiscoveryEndpoints:
    """Tests for discovery service status and configuration endpoints."""

    # GET /discovery/status tests

    def test_get_discovery_status_success(
        self,
        test_client: TestClient,
        mock_job_manager: MagicMock,
        mock_host_manager: MagicMock,
        sample_scan_jobs_list: list,
    ):
        """Test getting discovery service status."""
        mock_job_manager.list_jobs.return_value = {
            "items": sample_scan_jobs_list,
            "total": 2,
            "page": 1,
            "page_size": 50,
            "pages": 1,
        }
        mock_host_manager.get_host_count_by_status.return_value = {
            "total": 10,
            "online": 8,
            "offline": 1,
            "unknown": 1,
            "degraded": 0,
        }

        response = test_client.get("/api/v1/discovery/status")

        assert response.status_code == 200
        data = response.json()
        assert "total_scans" in data
        assert "active_scans" in data
        assert "total_managed_hosts" in data
        assert "online_hosts" in data
        assert "offline_hosts" in data
        assert "health_check_enabled" in data

    def test_get_discovery_status_empty(
        self,
        test_client: TestClient,
        mock_job_manager: MagicMock,
        mock_host_manager: MagicMock,
    ):
        """Test getting status with no data."""
        mock_job_manager.list_jobs.return_value = {
            "items": [],
            "total": 0,
            "page": 1,
            "page_size": 50,
            "pages": 0,
        }
        mock_host_manager.get_host_count_by_status.return_value = {
            "total": 0,
            "online": 0,
            "offline": 0,
            "unknown": 0,
            "degraded": 0,
        }

        response = test_client.get("/api/v1/discovery/status")

        assert response.status_code == 200
        data = response.json()
        assert data["total_scans"] == 0
        assert data["total_managed_hosts"] == 0

    # GET /discovery/config tests

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

    # GET /scan/presets tests

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
        assert "talkai" in preset_names
        assert "web" in preset_names

    def test_port_presets_structure(self, test_client: TestClient):
        """Test port presets have correct structure."""
        response = test_client.get("/api/v1/scan/presets")

        assert response.status_code == 200
        data = response.json()

        for preset in data["presets"]:
            assert "name" in preset
            assert "description" in preset
            assert "ports" in preset
            assert isinstance(preset["ports"], list)
            assert all(isinstance(p, int) for p in preset["ports"])

    # GET /scan/scanners tests

    def test_get_available_scanners_success(
        self,
        client_with_scanner_mock: TestClient,
        mock_scanner_factory: MagicMock,
    ):
        """Test getting available scanners."""
        response = client_with_scanner_mock.get("/api/v1/scan/scanners")

        assert response.status_code == 200
        data = response.json()
        assert "scanners" in data
        assert "recommended" in data
        assert len(data["scanners"]) > 0

    def test_scanners_structure(
        self,
        client_with_scanner_mock: TestClient,
    ):
        """Test scanners list has correct structure."""
        response = client_with_scanner_mock.get("/api/v1/scan/scanners")

        assert response.status_code == 200
        data = response.json()

        for scanner in data["scanners"]:
            assert "name" in scanner
            assert "description" in scanner
            assert "available" in scanner
            assert "requires_root" in scanner
            assert "recommended_for" in scanner
            assert "average_speed" in scanner


# ============== Test Edge Cases and Error Handling ==============


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

    def test_very_long_scan_range(
        self,
        test_client: TestClient,
    ):
        """Test scan request with very large network."""
        request = {
            "ip_range": "10.0.0.0/8",  # 16 million addresses
            "ports": [22],
            "scan_type": "python",
        }

        response = test_client.post("/api/v1/scans", json=request)

        assert response.status_code == 400

    def test_too_many_ports(
        self,
        test_client: TestClient,
    ):
        """Test scan request with too many ports."""
        request = {
            "ip_range": "192.168.1.0/24",
            "ports": list(range(1, 1002)),  # 1001 ports
            "scan_type": "python",
        }

        response = test_client.post("/api/v1/scans", json=request)

        assert response.status_code == 422

    def test_host_with_special_characters_in_name(
        self,
        test_client: TestClient,
        mock_host_manager: MagicMock,
        sample_host_id: uuid.UUID,
    ):
        """Test creating host with special characters in name."""
        request = {
            "name": "Test-Host_123 (Production)",
            "ip_address": "192.168.1.100",
            "ports": [22],
            "services": ["ssh"],
        }

        mock_host_manager.create_host.return_value = ManagedHostSchema(
            id=sample_host_id,
            name=request["name"],
            ip_address=request["ip_address"],
            ports=request["ports"],
            services=request["services"],
            status="unknown",
            last_checked_at=None,
            first_discovered_at=datetime.utcnow(),
            discovered_by_job_id=None,
            added_at=datetime.utcnow(),
            added_by="admin",
            notes=None,
            metadata={},
        )

        response = test_client.post("/api/v1/hosts", json=request)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == request["name"]


# ============== Test Authentication Placeholder ==============


class TestAuthenticationPlaceholder:
    """
    Placeholder tests for authentication (when JWT is implemented).

    These tests document expected behavior once authentication is added.
    """

    @pytest.mark.skip(reason="Authentication not yet implemented")
    def test_scan_with_invalid_token(self, test_client: TestClient):
        """Test scan request with invalid JWT token."""
        # TODO: Implement when JWT auth is added
        pass

    @pytest.mark.skip(reason="Authentication not yet implemented")
    def test_scan_without_token(self, test_client: TestClient):
        """Test scan request without JWT token."""
        # TODO: Implement when JWT auth is added
        pass

    @pytest.mark.skip(reason="Authorization not yet implemented")
    def test_admin_only_operations(self, test_client: TestClient):
        """Test admin-only operations require admin role."""
        # TODO: Implement when RBAC is added
        pass
