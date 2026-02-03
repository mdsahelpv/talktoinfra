"""
Unit tests for NmapScanner.
"""

import asyncio
import xml.etree.ElementTree as ET
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.scanners.base import (
    DiscoveredHost,
    ScanCancelledError,
    ScanConfig,
    ScannerNotAvailableError,
)
from app.scanners.nmap import NmapScanner


@pytest.fixture
def scanner_config() -> Dict[str, Any]:
    """Default nmap scanner configuration."""
    return {
        "nmap_path": "/usr/bin/nmap",
        "nmap_timing_template": "T4",
        "nmap_service_detection": True,
        "nmap_os_detection": False,
        "nmap_script_scan": False,
    }


@pytest.fixture
def nmap_scanner(scanner_config: Dict[str, Any]) -> NmapScanner:
    """Create an NmapScanner instance."""
    return NmapScanner(scanner_config)


@pytest.fixture
def sample_scan_config() -> ScanConfig:
    """Create a sample scan configuration."""
    return ScanConfig(
        ip_range="192.168.1.0/24",
        ports=[80, 443, 22],
        timeout=5.0,
        concurrent_limit=50,
        service_detection=True,
        extra_config={"timeout": 600},
    )


class TestNmapScannerProperties:
    """Test scanner properties."""

    def test_name(self, nmap_scanner: NmapScanner) -> None:
        """Test scanner name."""
        assert nmap_scanner.name == "nmap"

    def test_description(self, nmap_scanner: NmapScanner) -> None:
        """Test scanner description."""
        assert "scanner" in nmap_scanner.description.lower()
        assert "service" in nmap_scanner.description.lower()

    def test_requires_root_without_os_detection(
        self,
        scanner_config: Dict[str, Any],
    ) -> None:
        """Test that nmap doesn't require root without OS detection."""
        scanner_config["nmap_os_detection"] = False
        scanner = NmapScanner(scanner_config)
        assert scanner.requires_root is False

    def test_requires_root_with_os_detection(
        self,
        scanner_config: Dict[str, Any],
    ) -> None:
        """Test that nmap requires root with OS detection enabled."""
        scanner_config["nmap_os_detection"] = True
        scanner = NmapScanner(scanner_config)
        assert scanner.requires_root is True

    def test_binary_path_configuration(
        self,
        scanner_config: Dict[str, Any],
    ) -> None:
        """Test custom binary path configuration."""
        scanner_config["nmap_path"] = "/custom/path/nmap"
        scanner = NmapScanner(scanner_config)
        assert scanner.binary_path == "/custom/path/nmap"

    def test_timing_template_configuration(
        self,
        scanner_config: Dict[str, Any],
    ) -> None:
        """Test timing template configuration."""
        scanner_config["nmap_timing_template"] = "T5"
        scanner = NmapScanner(scanner_config)
        assert scanner.timing_template == "T5"

    def test_service_detection_configuration(
        self,
        scanner_config: Dict[str, Any],
    ) -> None:
        """Test service detection configuration."""
        scanner_config["nmap_service_detection"] = False
        scanner = NmapScanner(scanner_config)
        assert scanner.service_detection is False


class TestBinaryAvailability:
    """Test binary availability checking."""

    def test_available_when_binary_exists(
        self,
        nmap_scanner: NmapScanner,
    ) -> None:
        """Test that scanner reports available when binary exists."""
        with patch("app.scanners.nmap.shutil.which", return_value="/usr/bin/nmap"):
            assert nmap_scanner.available is True

    def test_not_available_when_binary_missing(
        self,
        nmap_scanner: NmapScanner,
    ) -> None:
        """Test that scanner reports unavailable when binary missing."""
        with patch("app.scanners.nmap.shutil.which", return_value=None):
            assert nmap_scanner.available is False

    def test_available_uses_configured_path(
        self,
        scanner_config: Dict[str, Any],
    ) -> None:
        """Test that availability check uses configured binary path."""
        scanner_config["nmap_path"] = "/usr/local/bin/nmap"
        scanner = NmapScanner(scanner_config)

        with patch("app.scanners.nmap.shutil.which") as mock_which:
            mock_which.return_value = "/usr/local/bin/nmap"
            _ = scanner.available
            mock_which.assert_called_once_with("/usr/local/bin/nmap")


class TestCommandBuilding:
    """Test nmap command building."""

    @pytest.mark.asyncio
    async def test_basic_command_structure(
        self,
        nmap_scanner: NmapScanner,
        sample_scan_config: ScanConfig,
    ) -> None:
        """Test basic command structure."""
        with patch("app.scanners.nmap.shutil.which", return_value="/usr/bin/nmap"):
            with patch("tempfile.NamedTemporaryFile") as mock_temp:
                mock_temp.return_value.__enter__.return_value.name = "/tmp/output.xml"

                with patch("asyncio.create_subprocess_exec") as mock_proc:
                    mock_process = AsyncMock()
                    mock_process.communicate.return_value = (b"", b"")
                    mock_proc.return_value = mock_process

                    with patch.object(
                        nmap_scanner, "_parse_xml_results", return_value=[]
                    ):
                        await nmap_scanner.start_scan(
                            sample_scan_config,
                            job_id="test-job",
                            progress_callback=None,
                        )

                    cmd = mock_proc.call_args[0]

                    assert "/usr/bin/nmap" in cmd
                    assert "-p" in cmd
                    assert "80,443,22" in cmd
                    assert "-T4" in cmd
                    assert "-oX" in cmd
                    assert "/tmp/output.xml" in cmd
                    assert "--open" in cmd
                    assert "-sT" in cmd
                    assert "192.168.1.0/24" in cmd

    @pytest.mark.asyncio
    async def test_command_with_service_detection(
        self,
        nmap_scanner: NmapScanner,
        sample_scan_config: ScanConfig,
    ) -> None:
        """Test command includes service detection option."""
        with patch("app.scanners.nmap.shutil.which", return_value="/usr/bin/nmap"):
            with patch("tempfile.NamedTemporaryFile") as mock_temp:
                mock_temp.return_value.__enter__.return_value.name = "/tmp/output.xml"

                with patch("asyncio.create_subprocess_exec") as mock_proc:
                    mock_process = AsyncMock()
                    mock_process.communicate.return_value = (b"", b"")
                    mock_proc.return_value = mock_process

                    with patch.object(
                        nmap_scanner, "_parse_xml_results", return_value=[]
                    ):
                        await nmap_scanner.start_scan(
                            sample_scan_config,
                            job_id="test-job",
                            progress_callback=None,
                        )

                    cmd = mock_proc.call_args[0]
                    assert "-sV" in cmd

    @pytest.mark.asyncio
    async def test_command_without_service_detection(
        self,
        scanner_config: Dict[str, Any],
        sample_scan_config: ScanConfig,
    ) -> None:
        """Test command without service detection."""
        scanner_config["nmap_service_detection"] = False
        scanner = NmapScanner(scanner_config)

        with patch("app.scanners.nmap.shutil.which", return_value="/usr/bin/nmap"):
            with patch("tempfile.NamedTemporaryFile") as mock_temp:
                mock_temp.return_value.__enter__.return_value.name = "/tmp/output.xml"

                with patch("asyncio.create_subprocess_exec") as mock_proc:
                    mock_process = AsyncMock()
                    mock_process.communicate.return_value = (b"", b"")
                    mock_proc.return_value = mock_process

                    with patch.object(scanner, "_parse_xml_results", return_value=[]):
                        await scanner.start_scan(
                            sample_scan_config,
                            job_id="test-job",
                            progress_callback=None,
                        )

                    cmd = mock_proc.call_args[0]
                    assert "-sV" not in cmd

    @pytest.mark.asyncio
    async def test_command_with_os_detection(
        self,
        scanner_config: Dict[str, Any],
        sample_scan_config: ScanConfig,
    ) -> None:
        """Test command includes OS detection option."""
        scanner_config["nmap_os_detection"] = True
        scanner = NmapScanner(scanner_config)

        with patch("app.scanners.nmap.shutil.which", return_value="/usr/bin/nmap"):
            with patch("tempfile.NamedTemporaryFile") as mock_temp:
                mock_temp.return_value.__enter__.return_value.name = "/tmp/output.xml"

                with patch("asyncio.create_subprocess_exec") as mock_proc:
                    mock_process = AsyncMock()
                    mock_process.communicate.return_value = (b"", b"")
                    mock_proc.return_value = mock_process

                    with patch.object(scanner, "_parse_xml_results", return_value=[]):
                        await scanner.start_scan(
                            sample_scan_config,
                            job_id="test-job",
                            progress_callback=None,
                        )

                    cmd = mock_proc.call_args[0]
                    assert "-O" in cmd

    @pytest.mark.asyncio
    async def test_command_with_script_scan(
        self,
        scanner_config: Dict[str, Any],
        sample_scan_config: ScanConfig,
    ) -> None:
        """Test command includes script scan option."""
        scanner_config["nmap_script_scan"] = True
        scanner = NmapScanner(scanner_config)

        with patch("app.scanners.nmap.shutil.which", return_value="/usr/bin/nmap"):
            with patch("tempfile.NamedTemporaryFile") as mock_temp:
                mock_temp.return_value.__enter__.return_value.name = "/tmp/output.xml"

                with patch("asyncio.create_subprocess_exec") as mock_proc:
                    mock_process = AsyncMock()
                    mock_process.communicate.return_value = (b"", b"")
                    mock_proc.return_value = mock_process

                    with patch.object(scanner, "_parse_xml_results", return_value=[]):
                        await scanner.start_scan(
                            sample_scan_config,
                            job_id="test-job",
                            progress_callback=None,
                        )

                    cmd = mock_proc.call_args[0]
                    assert "-sC" in cmd

    @pytest.mark.asyncio
    async def test_custom_timing_template(
        self,
        scanner_config: Dict[str, Any],
        sample_scan_config: ScanConfig,
    ) -> None:
        """Test command uses custom timing template."""
        scanner_config["nmap_timing_template"] = "T5"
        scanner = NmapScanner(scanner_config)

        with patch("app.scanners.nmap.shutil.which", return_value="/usr/bin/nmap"):
            with patch("tempfile.NamedTemporaryFile") as mock_temp:
                mock_temp.return_value.__enter__.return_value.name = "/tmp/output.xml"

                with patch("asyncio.create_subprocess_exec") as mock_proc:
                    mock_process = AsyncMock()
                    mock_process.communicate.return_value = (b"", b"")
                    mock_proc.return_value = mock_process

                    with patch.object(scanner, "_parse_xml_results", return_value=[]):
                        await scanner.start_scan(
                            sample_scan_config,
                            job_id="test-job",
                            progress_callback=None,
                        )

                    cmd = mock_proc.call_args[0]
                    assert "-T5" in cmd
                    assert "-T4" not in cmd


class TestXMLOutputParsing:
    """Test XML output parsing."""

    def create_nmap_xml(
        self,
        hosts: List[Dict[str, Any]],
    ) -> str:
        """Create nmap XML output for testing."""
        root = ET.Element("nmaprun")

        for host_data in hosts:
            host_elem = ET.SubElement(root, "host")

            status_elem = ET.SubElement(host_elem, "status")
            status_elem.set("state", host_data.get("status", "up"))

            address_elem = ET.SubElement(host_elem, "address")
            address_elem.set("addr", host_data["ip"])
            address_elem.set("addrtype", "ipv4")

            if host_data.get("hostname"):
                hostnames_elem = ET.SubElement(host_elem, "hostnames")
                hostname_elem = ET.SubElement(hostnames_elem, "hostname")
                hostname_elem.set("name", host_data["hostname"])

            if host_data.get("ports"):
                ports_elem = ET.SubElement(host_elem, "ports")
                for port_data in host_data["ports"]:
                    port_elem = ET.SubElement(ports_elem, "port")
                    port_elem.set("portid", str(port_data["port"]))
                    port_elem.set("protocol", port_data.get("protocol", "tcp"))

                    state_elem = ET.SubElement(port_elem, "state")
                    state_elem.set("state", port_data.get("state", "open"))

                    if port_data.get("service"):
                        service_elem = ET.SubElement(port_elem, "service")
                        service_elem.set("name", port_data["service"])
                        if port_data.get("product"):
                            service_elem.set("product", port_data["product"])
                        if port_data.get("version"):
                            service_elem.set("version", port_data["version"])
                        if port_data.get("extrainfo"):
                            service_elem.set("extrainfo", port_data["extrainfo"])

        return ET.tostring(root, encoding="unicode")

    def test_parse_empty_xml(self, nmap_scanner: NmapScanner) -> None:
        """Test parsing empty XML results."""
        xml_content = '<?xml version="1.0"?><nmaprun></nmaprun>'

        with patch("xml.etree.ElementTree.parse") as mock_parse:
            mock_tree = Mock()
            mock_tree.getroot.return_value = ET.fromstring(xml_content)
            mock_parse.return_value = mock_tree

            result = nmap_scanner._parse_xml_results("/tmp/empty.xml")

        assert result == []

    def test_parse_single_host_with_ports(
        self,
        nmap_scanner: NmapScanner,
    ) -> None:
        """Test parsing results with single host and ports."""
        hosts = [
            {
                "ip": "192.168.1.1",
                "status": "up",
                "hostname": "test.example.com",
                "ports": [
                    {"port": 80, "protocol": "tcp", "state": "open", "service": "http"},
                    {
                        "port": 443,
                        "protocol": "tcp",
                        "state": "open",
                        "service": "https",
                    },
                ],
            }
        ]

        xml_content = self.create_nmap_xml(hosts)

        with patch("xml.etree.ElementTree.parse") as mock_parse:
            mock_tree = Mock()
            mock_tree.getroot.return_value = ET.fromstring(xml_content)
            mock_parse.return_value = mock_tree

            result = nmap_scanner._parse_xml_results("/tmp/results.xml")

        assert len(result) == 1
        host = result[0]
        assert host.ip_address == "192.168.1.1"
        assert host.hostname == "test.example.com"
        assert host.status == "alive"
        assert len(host.ports) == 2
        assert {p.port for p in host.ports} == {80, 443}

    def test_parse_skips_down_hosts(
        self,
        nmap_scanner: NmapScanner,
    ) -> None:
        """Test that down hosts are not included."""
        hosts = [
            {"ip": "192.168.1.1", "status": "down", "ports": []},
            {
                "ip": "192.168.1.2",
                "status": "up",
                "ports": [{"port": 22, "state": "open", "service": "ssh"}],
            },
        ]

        xml_content = self.create_nmap_xml(hosts)

        with patch("xml.etree.ElementTree.parse") as mock_parse:
            mock_tree = Mock()
            mock_tree.getroot.return_value = ET.fromstring(xml_content)
            mock_parse.return_value = mock_tree

            result = nmap_scanner._parse_xml_results("/tmp/results.xml")

        assert len(result) == 1
        assert result[0].ip_address == "192.168.1.2"

    def test_parse_skips_closed_ports(
        self,
        nmap_scanner: NmapScanner,
    ) -> None:
        """Test that closed ports are not included."""
        hosts = [
            {
                "ip": "192.168.1.1",
                "status": "up",
                "ports": [
                    {"port": 80, "state": "open", "service": "http"},
                    {"port": 443, "state": "closed", "service": "https"},
                ],
            }
        ]

        xml_content = self.create_nmap_xml(hosts)

        with patch("xml.etree.ElementTree.parse") as mock_parse:
            mock_tree = Mock()
            mock_tree.getroot.return_value = ET.fromstring(xml_content)
            mock_parse.return_value = mock_tree

            result = nmap_scanner._parse_xml_results("/tmp/results.xml")

        assert len(result[0].ports) == 1
        assert result[0].ports[0].port == 80

    def test_parse_service_version_info(
        self,
        nmap_scanner: NmapScanner,
    ) -> None:
        """Test parsing service version information."""
        hosts = [
            {
                "ip": "192.168.1.1",
                "status": "up",
                "ports": [
                    {
                        "port": 22,
                        "state": "open",
                        "service": "ssh",
                        "product": "OpenSSH",
                        "version": "8.2p1",
                        "extrainfo": "Ubuntu 4ubuntu0.5",
                    },
                ],
            }
        ]

        xml_content = self.create_nmap_xml(hosts)

        with patch("xml.etree.ElementTree.parse") as mock_parse:
            mock_tree = Mock()
            mock_tree.getroot.return_value = ET.fromstring(xml_content)
            mock_parse.return_value = mock_tree

            result = nmap_scanner._parse_xml_results("/tmp/results.xml")

        port = result[0].ports[0]
        assert port.service == "ssh"
        assert port.service_version is not None

    def test_parse_hosts_without_open_ports(
        self,
        nmap_scanner: NmapScanner,
    ) -> None:
        """Test that hosts without open ports are not included."""
        hosts = [
            {"ip": "192.168.1.1", "status": "up", "ports": []},
        ]

        xml_content = self.create_nmap_xml(hosts)

        with patch("xml.etree.ElementTree.parse") as mock_parse:
            mock_tree = Mock()
            mock_tree.getroot.return_value = ET.fromstring(xml_content)
            mock_parse.return_value = mock_tree

            result = nmap_scanner._parse_xml_results("/tmp/results.xml")

        assert result == []

    def test_parse_xml_parse_error(
        self,
        nmap_scanner: NmapScanner,
    ) -> None:
        """Test handling of XML parse errors."""
        with patch(
            "xml.etree.ElementTree.parse", side_effect=ET.ParseError("Invalid XML")
        ):
            result = nmap_scanner._parse_xml_results("/tmp/invalid.xml")

        assert result == []

    def test_parse_file_not_found(
        self,
        nmap_scanner: NmapScanner,
    ) -> None:
        """Test handling of missing XML file."""
        with patch("xml.etree.ElementTree.parse", side_effect=FileNotFoundError()):
            result = nmap_scanner._parse_xml_results("/tmp/nonexistent.xml")

        assert result == []


class TestServiceDetectionParsing:
    """Test service detection parsing in XML output."""

    def test_parse_service_without_version(
        self,
        nmap_scanner: NmapScanner,
    ) -> None:
        """Test parsing service without version info."""
        hosts = [
            {
                "ip": "192.168.1.1",
                "status": "up",
                "ports": [
                    {"port": 80, "state": "open", "service": "http"},
                ],
            }
        ]

        xml_content = self._create_minimal_xml(hosts)

        with patch("xml.etree.ElementTree.parse") as mock_parse:
            mock_tree = Mock()
            mock_tree.getroot.return_value = ET.fromstring(xml_content)
            mock_parse.return_value = mock_tree

            result = nmap_scanner._parse_xml_results("/tmp/results.xml")

        port = result[0].ports[0]
        assert port.service == "http"
        assert port.service_version is None

    def test_parse_multiple_services(
        self,
        nmap_scanner: NmapScanner,
    ) -> None:
        """Test parsing multiple services on same host."""
        hosts = [
            {
                "ip": "192.168.1.1",
                "status": "up",
                "ports": [
                    {
                        "port": 22,
                        "state": "open",
                        "service": "ssh",
                        "product": "OpenSSH",
                    },
                    {
                        "port": 80,
                        "state": "open",
                        "service": "http",
                        "product": "nginx",
                    },
                    {
                        "port": 443,
                        "state": "open",
                        "service": "https",
                        "product": "nginx",
                    },
                    {
                        "port": 3306,
                        "state": "open",
                        "service": "mysql",
                        "product": "MySQL",
                    },
                ],
            }
        ]

        xml_content = self._create_minimal_xml(hosts)

        with patch("xml.etree.ElementTree.parse") as mock_parse:
            mock_tree = Mock()
            mock_tree.getroot.return_value = ET.fromstring(xml_content)
            mock_parse.return_value = mock_tree

            result = nmap_scanner._parse_xml_results("/tmp/results.xml")

        assert len(result[0].ports) == 4
        services = {p.service for p in result[0].ports}
        assert services == {"ssh", "http", "https", "mysql"}

    def _create_minimal_xml(self, hosts: List[Dict[str, Any]]) -> str:
        """Create minimal nmap XML for testing."""
        root = ET.Element("nmaprun")

        for host_data in hosts:
            host_elem = ET.SubElement(root, "host")

            status_elem = ET.SubElement(host_elem, "status")
            status_elem.set("state", "up")

            address_elem = ET.SubElement(host_elem, "address")
            address_elem.set("addr", host_data["ip"])
            address_elem.set("addrtype", "ipv4")

            if host_data.get("ports"):
                ports_elem = ET.SubElement(host_elem, "ports")
                for port_data in host_data["ports"]:
                    port_elem = ET.SubElement(ports_elem, "port")
                    port_elem.set("portid", str(port_data["port"]))
                    port_elem.set("protocol", "tcp")

                    state_elem = ET.SubElement(port_elem, "state")
                    state_elem.set("state", "open")

                    service_elem = ET.SubElement(port_elem, "service")
                    service_elem.set("name", port_data["service"])
                    if port_data.get("product"):
                        service_elem.set("product", port_data["product"])
                    if port_data.get("version"):
                        service_elem.set("version", port_data["version"])

        return ET.tostring(root, encoding="unicode")


class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_raises_error_when_binary_not_found(
        self,
        nmap_scanner: NmapScanner,
        sample_scan_config: ScanConfig,
    ) -> None:
        """Test that scan raises error when binary not found."""
        with patch("app.scanners.nmap.shutil.which", return_value=None):
            with pytest.raises(ScannerNotAvailableError) as exc_info:
                await nmap_scanner.start_scan(
                    sample_scan_config,
                    job_id="test-job",
                    progress_callback=None,
                )

        assert "Nmap binary not found" in str(exc_info.value)
        assert "/usr/bin/nmap" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_timeout_handling(
        self,
        nmap_scanner: NmapScanner,
        sample_scan_config: ScanConfig,
    ) -> None:
        """Test handling of scan timeout."""
        with patch("app.scanners.nmap.shutil.which", return_value="/usr/bin/nmap"):
            with patch("tempfile.NamedTemporaryFile") as mock_temp:
                mock_temp.return_value.__enter__.return_value.name = "/tmp/output.xml"

                with patch("asyncio.create_subprocess_exec") as mock_proc:
                    mock_process = AsyncMock()
                    mock_process.communicate.side_effect = asyncio.TimeoutError()
                    mock_process.kill = Mock()
                    mock_proc.return_value = mock_process

                    with pytest.raises(ScanCancelledError) as exc_info:
                        await nmap_scanner.start_scan(
                            sample_scan_config,
                            job_id="test-timeout-job",
                            progress_callback=None,
                        )

                    mock_process.kill.assert_called_once()
                    assert "timed out" in str(exc_info.value)


class TestScanCancellation:
    """Test scan cancellation functionality."""

    @pytest.mark.asyncio
    async def test_stop_scan_kills_process(
        self,
        nmap_scanner: NmapScanner,
    ) -> None:
        """Test that stop_scan kills the process."""
        job_id = "test-stop-job"
        mock_process = AsyncMock()
        mock_process.kill = Mock()

        nmap_scanner._active_processes[job_id] = mock_process

        result = await nmap_scanner.stop_scan(job_id)

        assert result is True
        mock_process.kill.assert_called_once()
        assert job_id not in nmap_scanner._active_processes

    @pytest.mark.asyncio
    async def test_stop_scan_unknown_job(
        self,
        nmap_scanner: NmapScanner,
    ) -> None:
        """Test stopping an unknown scan job."""
        result = await nmap_scanner.stop_scan("unknown-job-id")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_status_running(
        self,
        nmap_scanner: NmapScanner,
    ) -> None:
        """Test getting status of running scan."""
        job_id = "test-status-job"
        mock_process = AsyncMock()
        mock_process.returncode = None  # Still running

        nmap_scanner._active_processes[job_id] = mock_process

        status = await nmap_scanner.get_status(job_id)

        assert status is not None
        assert status.job_id == job_id
        assert status.status == "running"
        assert status.progress == 50
        assert status.current_phase == "nmap_scan"

    @pytest.mark.asyncio
    async def test_get_status_completed(
        self,
        nmap_scanner: NmapScanner,
    ) -> None:
        """Test getting status of completed scan."""
        job_id = "test-status-completed"
        mock_process = AsyncMock()
        mock_process.returncode = 0  # Completed

        nmap_scanner._active_processes[job_id] = mock_process

        status = await nmap_scanner.get_status(job_id)

        assert status is not None
        assert status.status == "completed"

    @pytest.mark.asyncio
    async def test_get_status_unknown_job(
        self,
        nmap_scanner: NmapScanner,
    ) -> None:
        """Test getting status of unknown job."""
        status = await nmap_scanner.get_status("unknown-job")
        assert status is None


class TestProgressCallback:
    """Test progress callback functionality."""

    @pytest.mark.asyncio
    async def test_progress_callback_on_start(
        self,
        nmap_scanner: NmapScanner,
        sample_scan_config: ScanConfig,
    ) -> None:
        """Test that progress callback is called on scan start."""
        progress_updates = []

        def progress_callback(progress):
            progress_updates.append(progress)

        with patch("app.scanners.nmap.shutil.which", return_value="/usr/bin/nmap"):
            with patch("tempfile.NamedTemporaryFile") as mock_temp:
                mock_temp.return_value.__enter__.return_value.name = "/tmp/output.xml"

                with patch("asyncio.create_subprocess_exec") as mock_proc:
                    mock_process = AsyncMock()
                    mock_process.communicate.return_value = (b"", b"")
                    mock_proc.return_value = mock_process

                    with patch.object(
                        nmap_scanner, "_parse_xml_results", return_value=[]
                    ):
                        await nmap_scanner.start_scan(
                            sample_scan_config,
                            job_id="test-job",
                            progress_callback=progress_callback,
                        )

        assert len(progress_updates) >= 1
        assert progress_updates[0].job_id == "test-job"
        assert progress_updates[0].status == "running"
        assert progress_updates[0].progress == 0
        assert progress_updates[0].current_phase == "nmap_scan"

    @pytest.mark.asyncio
    async def test_progress_callback_on_completion(
        self,
        nmap_scanner: NmapScanner,
        sample_scan_config: ScanConfig,
    ) -> None:
        """Test that progress callback is called on completion."""
        progress_updates = []

        def progress_callback(progress):
            progress_updates.append(progress)

        mock_hosts = [
            DiscoveredHost(ip_address="192.168.1.1", status="alive", ports=[])
        ]

        with patch("app.scanners.nmap.shutil.which", return_value="/usr/bin/nmap"):
            with patch("tempfile.NamedTemporaryFile") as mock_temp:
                mock_temp.return_value.__enter__.return_value.name = "/tmp/output.xml"

                with patch("asyncio.create_subprocess_exec") as mock_proc:
                    mock_process = AsyncMock()
                    mock_process.communicate.return_value = (b"", b"")
                    mock_proc.return_value = mock_process

                    with patch.object(
                        nmap_scanner, "_parse_xml_results", return_value=mock_hosts
                    ):
                        await nmap_scanner.start_scan(
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
        nmap_scanner: NmapScanner,
        sample_scan_config: ScanConfig,
    ) -> None:
        """Test that output file is cleaned up after scan."""
        output_file = "/tmp/nmap_output.xml"

        with patch("app.scanners.nmap.shutil.which", return_value="/usr/bin/nmap"):
            with patch("tempfile.NamedTemporaryFile") as mock_temp:
                mock_temp.return_value.__enter__.return_value.name = output_file

                with patch("asyncio.create_subprocess_exec") as mock_proc:
                    mock_process = AsyncMock()
                    mock_process.communicate.return_value = (b"", b"")
                    mock_proc.return_value = mock_process

                    with patch.object(
                        nmap_scanner, "_parse_xml_results", return_value=[]
                    ):
                        with patch("os.unlink") as mock_unlink:
                            await nmap_scanner.start_scan(
                                sample_scan_config,
                                job_id="test-job",
                                progress_callback=None,
                            )

                            mock_unlink.assert_called_once_with(output_file)

    @pytest.mark.asyncio
    async def test_process_cleanup(
        self,
        nmap_scanner: NmapScanner,
        sample_scan_config: ScanConfig,
    ) -> None:
        """Test that process is removed from active processes after scan."""
        job_id = "test-cleanup-job"

        with patch("app.scanners.nmap.shutil.which", return_value="/usr/bin/nmap"):
            with patch("tempfile.NamedTemporaryFile") as mock_temp:
                mock_temp.return_value.__enter__.return_value.name = "/tmp/output.xml"

                with patch("asyncio.create_subprocess_exec") as mock_proc:
                    mock_process = AsyncMock()
                    mock_process.communicate.return_value = (b"", b"")
                    mock_proc.return_value = mock_process

                    with patch.object(
                        nmap_scanner, "_parse_xml_results", return_value=[]
                    ):
                        await nmap_scanner.start_scan(
                            sample_scan_config,
                            job_id=job_id,
                            progress_callback=None,
                        )

        assert job_id not in nmap_scanner._active_processes
