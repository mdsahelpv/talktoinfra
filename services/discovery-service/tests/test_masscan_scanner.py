"""
Unit tests for MasscanScanner.
"""

import asyncio
import json
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, mock_open, patch

import pytest

from app.scanners.base import (
    DiscoveredHost,
    ScanCancelledError,
    ScanConfig,
    ScannerNotAvailableError,
)
from app.scanners.masscan import MasscanScanner


@pytest.fixture
def scanner_config() -> Dict[str, Any]:
    """Default masscan scanner configuration."""
    return {
        "masscan_path": "/usr/bin/masscan",
        "masscan_rate": 1000,
        "masscan_adapter": "eth0",
        "masscan_wait_time": 10,
    }


@pytest.fixture
def masscan_scanner(scanner_config: Dict[str, Any]) -> MasscanScanner:
    """Create a MasscanScanner instance."""
    return MasscanScanner(scanner_config)


@pytest.fixture
def sample_scan_config() -> ScanConfig:
    """Create a sample scan configuration."""
    return ScanConfig(
        ip_range="192.168.1.0/24",
        ports=[80, 443, 22],
        timeout=5.0,
        concurrent_limit=50,
        service_detection=False,
        extra_config={"timeout": 300},
    )


class TestMasscanScannerProperties:
    """Test scanner properties."""

    def test_name(self, masscan_scanner: MasscanScanner) -> None:
        """Test scanner name."""
        assert masscan_scanner.name == "masscan"

    def test_description(self, masscan_scanner: MasscanScanner) -> None:
        """Test scanner description."""
        assert "syn" in masscan_scanner.description.lower()
        assert "scanner" in masscan_scanner.description.lower()

    def test_requires_root(self, masscan_scanner: MasscanScanner) -> None:
        """Test that masscan requires root for SYN scanning."""
        assert masscan_scanner.requires_root is True

    def test_binary_path_configuration(
        self,
        scanner_config: Dict[str, Any],
    ) -> None:
        """Test custom binary path configuration."""
        scanner_config["masscan_path"] = "/custom/path/masscan"
        scanner = MasscanScanner(scanner_config)
        assert scanner.binary_path == "/custom/path/masscan"

    def test_default_rate_configuration(
        self,
        scanner_config: Dict[str, Any],
    ) -> None:
        """Test default rate configuration."""
        scanner = MasscanScanner(scanner_config)
        assert scanner.rate == 1000

    def test_adapter_configuration(
        self,
        scanner_config: Dict[str, Any],
    ) -> None:
        """Test adapter configuration."""
        scanner = MasscanScanner(scanner_config)
        assert scanner.adapter == "eth0"


class TestBinaryAvailability:
    """Test binary availability checking."""

    def test_available_when_binary_exists(
        self,
        masscan_scanner: MasscanScanner,
    ) -> None:
        """Test that scanner reports available when binary exists."""
        with patch(
            "app.scanners.masscan.shutil.which", return_value="/usr/bin/masscan"
        ):
            assert masscan_scanner.available is True

    def test_not_available_when_binary_missing(
        self,
        masscan_scanner: MasscanScanner,
    ) -> None:
        """Test that scanner reports unavailable when binary missing."""
        with patch("app.scanners.masscan.shutil.which", return_value=None):
            assert masscan_scanner.available is False

    def test_available_uses_configured_path(
        self,
        scanner_config: Dict[str, Any],
    ) -> None:
        """Test that availability check uses configured binary path."""
        scanner_config["masscan_path"] = "/opt/masscan"
        scanner = MasscanScanner(scanner_config)

        with patch("app.scanners.masscan.shutil.which") as mock_which:
            mock_which.return_value = "/opt/masscan"
            _ = scanner.available
            mock_which.assert_called_once_with("/opt/masscan")


class TestCommandBuilding:
    """Test masscan command building."""

    @pytest.mark.asyncio
    async def test_basic_command_structure(
        self,
        masscan_scanner: MasscanScanner,
        sample_scan_config: ScanConfig,
    ) -> None:
        """Test basic command structure."""
        job_id = "test-job-123"

        with patch(
            "app.scanners.masscan.shutil.which", return_value="/usr/bin/masscan"
        ):
            with patch("tempfile.NamedTemporaryFile") as mock_temp:
                mock_temp.return_value.__enter__.return_value.name = "/tmp/output.json"

                with patch("asyncio.create_subprocess_exec") as mock_proc:
                    mock_process = AsyncMock()
                    mock_process.communicate.return_value = (b"", b"")
                    mock_proc.return_value = mock_process

                    with patch.object(
                        masscan_scanner, "_parse_results", return_value=[]
                    ):
                        await masscan_scanner.start_scan(
                            sample_scan_config,
                            job_id=job_id,
                            progress_callback=None,
                        )

                    # Verify command was created
                    call_args = mock_proc.call_args
                    cmd = call_args[0]

                    assert "/usr/bin/masscan" in cmd
                    assert "192.168.1.0/24" in cmd
                    assert "-p" in cmd
                    assert "80,443,22" in cmd
                    assert "--rate" in cmd
                    assert "1000" in cmd
                    assert "-oJ" in cmd
                    assert "/tmp/output.json" in cmd
                    assert "--wait" in cmd
                    assert "10" in cmd

    @pytest.mark.asyncio
    async def test_command_with_adapter(
        self,
        masscan_scanner: MasscanScanner,
        sample_scan_config: ScanConfig,
    ) -> None:
        """Test command includes adapter option."""
        with patch(
            "app.scanners.masscan.shutil.which", return_value="/usr/bin/masscan"
        ):
            with patch("tempfile.NamedTemporaryFile") as mock_temp:
                mock_temp.return_value.__enter__.return_value.name = "/tmp/output.json"

                with patch("asyncio.create_subprocess_exec") as mock_proc:
                    mock_process = AsyncMock()
                    mock_process.communicate.return_value = (b"", b"")
                    mock_proc.return_value = mock_process

                    with patch.object(
                        masscan_scanner, "_parse_results", return_value=[]
                    ):
                        with patch("app.scanners.masscan.metrics") as mock_metrics:
                            await masscan_scanner.start_scan(
                                sample_scan_config,
                                job_id=job_id,
                                progress_callback=None,
                            )

                    cmd = mock_proc.call_args[0]
                    assert "--adapter" in cmd
                    assert "eth0" in cmd

    @pytest.mark.asyncio
    async def test_command_without_adapter(
        self,
        scanner_config: Dict[str, Any],
        sample_scan_config: ScanConfig,
    ) -> None:
        """Test command without adapter option."""
        scanner_config["masscan_adapter"] = None
        scanner = MasscanScanner(scanner_config)

        with patch(
            "app.scanners.masscan.shutil.which", return_value="/usr/bin/masscan"
        ):
            with patch("tempfile.NamedTemporaryFile") as mock_temp:
                mock_temp.return_value.__enter__.return_value.name = "/tmp/output.json"

                with patch("asyncio.create_subprocess_exec") as mock_proc:
                    mock_process = AsyncMock()
                    mock_process.communicate.return_value = (b"", b"")
                    mock_proc.return_value = mock_process

                    with patch.object(scanner, "_parse_results", return_value=[]):
                        await scanner.start_scan(
                            sample_scan_config,
                            job_id="test-job",
                            progress_callback=None,
                        )

                    cmd = mock_proc.call_args[0]
                    assert "--adapter" not in cmd


class TestJSONOutputParsing:
    """Test JSON output parsing."""

    def test_parse_empty_results(self, masscan_scanner: MasscanScanner) -> None:
        """Test parsing empty results file."""
        with patch(
            "builtins.open",
            mock_open(read_data=""),
        ):
            with patch("json.load", side_effect=json.JSONDecodeError("", "", 0)):
                result = masscan_scanner._parse_results("/tmp/empty.json")

        assert result == []

    def test_parse_single_host_single_port(
        self,
        masscan_scanner: MasscanScanner,
    ) -> None:
        """Test parsing results with single host and port."""
        json_data = [
            {
                "ip": "192.168.1.1",
                "ports": [{"port": 80, "proto": "tcp", "status": "open"}],
            }
        ]

        with patch("builtins.open", mock_open(read_data=json.dumps(json_data))):
            with patch("json.load", return_value=json_data):
                result = masscan_scanner._parse_results("/tmp/results.json")

        assert len(result) == 1
        host = result[0]
        assert host.ip_address == "192.168.1.1"
        assert host.status == "alive"
        assert len(host.ports) == 1
        assert host.ports[0].port == 80
        assert host.ports[0].status == "open"
        assert host.ports[0].protocol == "tcp"

    def test_parse_multiple_hosts_multiple_ports(
        self,
        masscan_scanner: MasscanScanner,
    ) -> None:
        """Test parsing results with multiple hosts and ports."""
        json_data = [
            {
                "ip": "192.168.1.1",
                "ports": [
                    {"port": 80, "proto": "tcp", "status": "open"},
                    {"port": 443, "proto": "tcp", "status": "open"},
                ],
            },
            {
                "ip": "192.168.1.2",
                "ports": [{"port": 22, "proto": "tcp", "status": "open"}],
            },
        ]

        with patch("builtins.open", mock_open(read_data=json.dumps(json_data))):
            with patch("json.load", return_value=json_data):
                result = masscan_scanner._parse_results("/tmp/results.json")

        assert len(result) == 2

        host1 = next(h for h in result if h.ip_address == "192.168.1.1")
        assert len(host1.ports) == 2
        assert {p.port for p in host1.ports} == {80, 443}

        host2 = next(h for h in result if h.ip_address == "192.168.1.2")
        assert len(host2.ports) == 1
        assert host2.ports[0].port == 22

    def test_parse_skips_closed_ports(
        self,
        masscan_scanner: MasscanScanner,
    ) -> None:
        """Test that closed ports are not included in results."""
        json_data = [
            {
                "ip": "192.168.1.1",
                "ports": [
                    {"port": 80, "proto": "tcp", "status": "open"},
                    {"port": 443, "proto": "tcp", "status": "closed"},
                ],
            }
        ]

        with patch("builtins.open", mock_open(read_data=json.dumps(json_data))):
            with patch("json.load", return_value=json_data):
                result = masscan_scanner._parse_results("/tmp/results.json")

        assert len(result) == 1
        assert len(result[0].ports) == 1
        assert result[0].ports[0].port == 80

    def test_parse_skips_invalid_entries(
        self,
        masscan_scanner: MasscanScanner,
    ) -> None:
        """Test that entries without IP are skipped."""
        json_data = [
            {"ip": "", "ports": [{"port": 80, "proto": "tcp", "status": "open"}]},
            {
                "ip": "192.168.1.1",
                "ports": [{"port": 22, "proto": "tcp", "status": "open"}],
            },
        ]

        with patch("builtins.open", mock_open(read_data=json.dumps(json_data))):
            with patch("json.load", return_value=json_data):
                result = masscan_scanner._parse_results("/tmp/results.json")

        assert len(result) == 1
        assert result[0].ip_address == "192.168.1.1"

    def test_parse_file_not_found(
        self,
        masscan_scanner: MasscanScanner,
    ) -> None:
        """Test handling of missing results file."""
        with patch("builtins.open", side_effect=FileNotFoundError()):
            result = masscan_scanner._parse_results("/tmp/nonexistent.json")

        assert result == []


class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_raises_error_when_binary_not_found(
        self,
        masscan_scanner: MasscanScanner,
        sample_scan_config: ScanConfig,
    ) -> None:
        """Test that scan raises error when binary not found."""
        with patch("app.scanners.masscan.shutil.which", return_value=None):
            with pytest.raises(ScannerNotAvailableError) as exc_info:
                await masscan_scanner.start_scan(
                    sample_scan_config,
                    job_id="test-job",
                    progress_callback=None,
                )

        assert "Masscan binary not found" in str(exc_info.value)
        assert "/usr/bin/masscan" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_timeout_handling(
        self,
        masscan_scanner: MasscanScanner,
        sample_scan_config: ScanConfig,
    ) -> None:
        """Test handling of scan timeout."""
        with patch(
            "app.scanners.masscan.shutil.which", return_value="/usr/bin/masscan"
        ):
            with patch("tempfile.NamedTemporaryFile") as mock_temp:
                mock_temp.return_value.__enter__.return_value.name = "/tmp/output.json"

                with patch("asyncio.create_subprocess_exec") as mock_proc:
                    mock_process = AsyncMock()
                    mock_process.communicate.side_effect = asyncio.TimeoutError()
                    mock_process.kill = Mock()
                    mock_proc.return_value = mock_process

                    with pytest.raises(ScanCancelledError) as exc_info:
                        await masscan_scanner.start_scan(
                            sample_scan_config,
                            job_id="test-timeout-job",
                            progress_callback=None,
                        )

                    mock_process.kill.assert_called_once()
                    assert "timed out" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_cancellation_during_scan(
        self,
        masscan_scanner: MasscanScanner,
        sample_scan_config: ScanConfig,
    ) -> None:
        """Test cancellation during scan execution."""
        job_id = "test-cancel-job"

        with patch(
            "app.scanners.masscan.shutil.which", return_value="/usr/bin/masscan"
        ):
            with patch("tempfile.NamedTemporaryFile") as mock_temp:
                mock_temp.return_value.__enter__.return_value.name = "/tmp/output.json"

                with patch("asyncio.create_subprocess_exec") as mock_proc:
                    mock_process = AsyncMock()

                    async def slow_communicate():
                        await asyncio.sleep(0.1)
                        return (b"", b"")

                    mock_process.communicate = slow_communicate
                    mock_proc.return_value = mock_process

                    # Start scan in background
                    scan_task = asyncio.create_task(
                        masscan_scanner.start_scan(
                            sample_scan_config,
                            job_id=job_id,
                            progress_callback=None,
                        )
                    )

                    # Small delay to ensure process is registered
                    await asyncio.sleep(0.01)

                    # Simulate cancellation
                    await masscan_scanner.stop_scan(job_id)

                    with pytest.raises(ScanCancelledError):
                        await scan_task


class TestScanCancellation:
    """Test scan cancellation functionality."""

    @pytest.mark.asyncio
    async def test_stop_scan_kills_process(
        self,
        masscan_scanner: MasscanScanner,
    ) -> None:
        """Test that stop_scan kills the process."""
        job_id = "test-stop-job"
        mock_process = AsyncMock()
        mock_process.kill = Mock()

        masscan_scanner._active_processes[job_id] = mock_process

        result = await masscan_scanner.stop_scan(job_id)

        assert result is True
        mock_process.kill.assert_called_once()
        assert job_id not in masscan_scanner._active_processes

    @pytest.mark.asyncio
    async def test_stop_scan_unknown_job(
        self,
        masscan_scanner: MasscanScanner,
    ) -> None:
        """Test stopping an unknown scan job."""
        result = await masscan_scanner.stop_scan("unknown-job-id")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_status_running(
        self,
        masscan_scanner: MasscanScanner,
    ) -> None:
        """Test getting status of running scan."""
        job_id = "test-status-job"
        mock_process = AsyncMock()
        mock_process.returncode = None  # Still running

        masscan_scanner._active_processes[job_id] = mock_process

        status = await masscan_scanner.get_status(job_id)

        assert status is not None
        assert status.job_id == job_id
        assert status.status == "running"
        assert status.progress == 50
        assert status.current_phase == "masscan_discovery"

    @pytest.mark.asyncio
    async def test_get_status_completed(
        self,
        masscan_scanner: MasscanScanner,
    ) -> None:
        """Test getting status of completed scan."""
        job_id = "test-status-completed"
        mock_process = AsyncMock()
        mock_process.returncode = 0  # Completed

        masscan_scanner._active_processes[job_id] = mock_process

        status = await masscan_scanner.get_status(job_id)

        assert status is not None
        assert status.status == "completed"

    @pytest.mark.asyncio
    async def test_get_status_unknown_job(
        self,
        masscan_scanner: MasscanScanner,
    ) -> None:
        """Test getting status of unknown job."""
        status = await masscan_scanner.get_status("unknown-job")
        assert status is None


class TestProgressCallback:
    """Test progress callback functionality."""

    @pytest.mark.asyncio
    async def test_progress_callback_on_start(
        self,
        masscan_scanner: MasscanScanner,
        sample_scan_config: ScanConfig,
    ) -> None:
        """Test that progress callback is called on scan start."""
        progress_updates = []

        def progress_callback(progress):
            progress_updates.append(progress)

        with patch(
            "app.scanners.masscan.shutil.which", return_value="/usr/bin/masscan"
        ):
            with patch("tempfile.NamedTemporaryFile") as mock_temp:
                mock_temp.return_value.__enter__.return_value.name = "/tmp/output.json"

                with patch("asyncio.create_subprocess_exec") as mock_proc:
                    mock_process = AsyncMock()
                    mock_process.communicate.return_value = (b"", b"")
                    mock_proc.return_value = mock_process

                    with patch.object(
                        masscan_scanner, "_parse_results", return_value=[]
                    ):
                        await masscan_scanner.start_scan(
                            sample_scan_config,
                            job_id="test-job",
                            progress_callback=progress_callback,
                        )

        assert len(progress_updates) >= 1
        assert progress_updates[0].job_id == "test-job"
        assert progress_updates[0].status == "running"
        assert progress_updates[0].progress == 0
        assert progress_updates[0].current_phase == "masscan_discovery"

    @pytest.mark.asyncio
    async def test_progress_callback_on_completion(
        self,
        masscan_scanner: MasscanScanner,
        sample_scan_config: ScanConfig,
    ) -> None:
        """Test that progress callback is called on completion."""
        progress_updates = []

        def progress_callback(progress):
            progress_updates.append(progress)

        mock_hosts = [
            DiscoveredHost(ip_address="192.168.1.1", status="alive", ports=[])
        ]

        with patch(
            "app.scanners.masscan.shutil.which", return_value="/usr/bin/masscan"
        ):
            with patch("tempfile.NamedTemporaryFile") as mock_temp:
                mock_temp.return_value.__enter__.return_value.name = "/tmp/output.json"

                with patch("asyncio.create_subprocess_exec") as mock_proc:
                    mock_process = AsyncMock()
                    mock_process.communicate.return_value = (b"", b"")
                    mock_proc.return_value = mock_process

                    with patch.object(
                        masscan_scanner, "_parse_results", return_value=mock_hosts
                    ):
                        await masscan_scanner.start_scan(
                            sample_scan_config,
                            job_id="test-job",
                            progress_callback=progress_callback,
                        )

        # Should have at least start and completion callbacks
        assert len(progress_updates) >= 2

        # Find completion callback
        completion_updates = [p for p in progress_updates if p.status == "completed"]
        assert len(completion_updates) == 1
        assert completion_updates[0].progress == 100
        assert completion_updates[0].found_hosts == 1


class TestCleanup:
    """Test cleanup functionality."""

    @pytest.mark.asyncio
    async def test_output_file_cleanup(
        self,
        masscan_scanner: MasscanScanner,
        sample_scan_config: ScanConfig,
    ) -> None:
        """Test that output file is cleaned up after scan."""
        output_file = "/tmp/masscan_output.json"

        with patch(
            "app.scanners.masscan.shutil.which", return_value="/usr/bin/masscan"
        ):
            with patch("tempfile.NamedTemporaryFile") as mock_temp:
                mock_temp.return_value.__enter__.return_value.name = output_file

                with patch("asyncio.create_subprocess_exec") as mock_proc:
                    mock_process = AsyncMock()
                    mock_process.communicate.return_value = (b"", b"")
                    mock_proc.return_value = mock_process

                    with patch.object(
                        masscan_scanner, "_parse_results", return_value=[]
                    ):
                        with patch("os.unlink") as mock_unlink:
                            await masscan_scanner.start_scan(
                                sample_scan_config,
                                job_id="test-job",
                                progress_callback=None,
                            )

                            mock_unlink.assert_called_once_with(output_file)

    @pytest.mark.asyncio
    async def test_process_cleanup(
        self,
        masscan_scanner: MasscanScanner,
        sample_scan_config: ScanConfig,
    ) -> None:
        """Test that process is removed from active processes after scan."""
        job_id = "test-cleanup-job"

        with patch(
            "app.scanners.masscan.shutil.which", return_value="/usr/bin/masscan"
        ):
            with patch("tempfile.NamedTemporaryFile") as mock_temp:
                mock_temp.return_value.__enter__.return_value.name = "/tmp/output.json"

                with patch("asyncio.create_subprocess_exec") as mock_proc:
                    mock_process = AsyncMock()
                    mock_process.communicate.return_value = (b"", b"")
                    mock_proc.return_value = mock_process

                    with patch.object(
                        masscan_scanner, "_parse_results", return_value=[]
                    ):
                        await masscan_scanner.start_scan(
                            sample_scan_config,
                            job_id=job_id,
                            progress_callback=None,
                        )

        assert job_id not in masscan_scanner._active_processes
