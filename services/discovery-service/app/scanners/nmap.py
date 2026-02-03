"""
Nmap scanner wrapper - Industry standard with rich features.
"""

import asyncio
import shutil
import tempfile
import xml.etree.ElementTree as ET
from typing import Any, Callable, Dict, List, Optional

import structlog

from app.scanners.base import (
    BaseScanner,
    DiscoveredHost,
    ScanCancelledError,
    ScanConfig,
    ScanPort,
    ScanProgress,
    ScannerNotAvailableError,
)

logger = structlog.get_logger()


class NmapScanner(BaseScanner):
    """
    Nmap wrapper - Industry standard network scanner.

    Pros:
    - Excellent service detection
    - OS fingerprinting
    - Scripting engine (NSE)
    - Version detection
    - Well-documented and trusted

    Cons:
    - Slower than masscan
    - Requires root for some features
    - Higher resource usage

    Installation:
        apt-get install nmap
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.binary_path = config.get("nmap_path", "/usr/bin/nmap")
        self.timing_template = config.get("nmap_timing_template", "T4")
        self.service_detection = config.get("nmap_service_detection", True)
        self.os_detection = config.get("nmap_os_detection", False)
        self.script_scan = config.get("nmap_script_scan", False)
        self._active_processes: Dict[str, asyncio.subprocess.Process] = {}

    @property
    def name(self) -> str:
        return "nmap"

    @property
    def description(self) -> str:
        return "Industry standard scanner with excellent service detection"

    @property
    def requires_root(self) -> bool:
        # SYN scan and OS detection require root
        return self.os_detection

    @property
    def available(self) -> bool:
        """Check if nmap binary exists."""
        return shutil.which(self.binary_path) is not None

    async def start_scan(
        self,
        scan_config: ScanConfig,
        job_id: str,
        progress_callback: Optional[Callable[[ScanProgress], None]] = None,
    ) -> List[DiscoveredHost]:
        """Execute nmap scan."""

        if not self.available:
            raise ScannerNotAvailableError(
                f"Nmap binary not found at {self.binary_path}. "
                "Install with: apt-get install nmap"
            )

        self.logger.info(
            "nmap_scan_started",
            job_id=job_id,
            ip_range=scan_config.ip_range,
            ports=len(scan_config.ports),
            timing=self.timing_template,
        )

        # Create temporary output file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            output_file = f.name

        try:
            # Build nmap command
            from app.utils.ip_range import format_ip_range_for_scanner

            ports_str = ",".join(map(str, scan_config.ports))

            # Format IP range for nmap (nmap supports CIDR, ranges, and comma-separated)
            formatted_range = format_ip_range_for_scanner(scan_config.ip_range, "nmap")

            cmd = [
                self.binary_path,
                "-p",
                ports_str,
                f"-{self.timing_template}",
                "-oX",
                output_file,  # XML output
                "--open",  # Only show open ports
            ]

            # Add service detection
            if self.service_detection and scan_config.service_detection:
                cmd.append("-sV")  # Version detection

            # Add OS detection (requires root)
            if self.os_detection:
                cmd.append("-O")

            # Add script scan
            if self.script_scan:
                cmd.append("-sC")

            # Use TCP connect if not root
            # (SYN scan requires root)
            cmd.append("-sT")

            # Add target
            cmd.append(formatted_range)

            # Start nmap process
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            self._active_processes[job_id] = process

            # Report initial progress
            self._notify_progress(
                progress_callback,
                ScanProgress(
                    job_id=job_id,
                    status="running",
                    progress=0,
                    current_phase="nmap_scan",
                    message="Starting nmap...",
                ),
            )

            # Wait for completion with timeout
            timeout = scan_config.extra_config.get("timeout", 600)

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                raise ScanCancelledError(
                    f"Nmap scan {job_id} timed out after {timeout}s"
                )

            # Check if cancelled
            if job_id not in self._active_processes:
                raise ScanCancelledError(f"Scan {job_id} was cancelled")

            # Parse results
            discovered_hosts = self._parse_xml_results(output_file)

            # Count total ports and open ports for metrics
            total_ports = sum(len(h.ports) for h in discovered_hosts)
            open_ports = total_ports  # Nmap only returns open ports with --open flag

            # Record port metrics
            from app.monitoring import metrics

            metrics.record_ports_scanned("nmap", total_ports, open_ports)

            self.logger.info(
                "nmap_scan_completed", job_id=job_id, found_hosts=len(discovered_hosts)
            )

            # Report completion
            self._notify_progress(
                progress_callback,
                ScanProgress(
                    job_id=job_id,
                    status="completed",
                    progress=100,
                    found_hosts=len(discovered_hosts),
                    message="Nmap completed",
                ),
            )

            return discovered_hosts

        finally:
            # Cleanup
            if job_id in self._active_processes:
                del self._active_processes[job_id]

            import os

            try:
                os.unlink(output_file)
            except OSError:
                pass

    def _parse_xml_results(self, output_file: str) -> List[DiscoveredHost]:
        """Parse nmap XML output."""
        hosts: List[DiscoveredHost] = []

        try:
            tree = ET.parse(output_file)
            root = tree.getroot()
        except (ET.ParseError, FileNotFoundError):
            return []

        for host_elem in root.findall(".//host"):
            # Get host status
            status_elem = host_elem.find("status")
            if status_elem is None or status_elem.get("state") != "up":
                continue

            # Get IP address
            address_elem = host_elem.find("address[@addrtype='ipv4']")
            if address_elem is None:
                continue

            ip = address_elem.get("addr", "")
            if not ip:
                continue

            # Get hostname
            hostname = None
            hostnames_elem = host_elem.find("hostnames")
            if hostnames_elem is not None:
                hostname_elem = hostnames_elem.find("hostname")
                if hostname_elem is not None:
                    hostname = hostname_elem.get("name")

            # Parse ports
            ports: List[ScanPort] = []
            ports_elem = host_elem.find("ports")
            if ports_elem is not None:
                for port_elem in ports_elem.findall("port"):
                    portid = port_elem.get("portid", "0")
                    protocol = port_elem.get("protocol", "tcp")

                    state_elem = port_elem.find("state")
                    if state_elem is None:
                        continue

                    state = state_elem.get("state", "")
                    if state != "open":
                        continue

                    # Get service info
                    service_elem = port_elem.find("service")
                    service_name = None
                    service_version = None
                    banner = None

                    if service_elem is not None:
                        service_name = service_elem.get("name")
                        product = service_elem.get("product", "")
                        version = service_elem.get("version", "")
                        extrainfo = service_elem.get("extrainfo", "")

                        if product:
                            service_version = f"{product}"
                            if version:
                                service_version += f" {version}"
                            if extrainfo:
                                service_version += f" ({extrainfo})"

                        banner = service_elem.get("banner")

                    ports.append(
                        ScanPort(
                            port=int(portid),
                            status="open",
                            service=service_name,
                            service_version=service_version,
                            banner=banner,
                            protocol=protocol,
                        )
                    )

            if ports:  # Only include hosts with open ports
                hosts.append(
                    DiscoveredHost(
                        ip_address=ip, hostname=hostname, status="alive", ports=ports
                    )
                )

        return hosts

    async def stop_scan(self, job_id: str) -> bool:
        """Stop a running nmap scan."""
        if job_id in self._active_processes:
            process = self._active_processes[job_id]
            process.kill()
            del self._active_processes[job_id]
            self.logger.info("nmap_stopped", job_id=job_id)
            return True
        return False

    async def get_status(self, job_id: str) -> Optional[ScanProgress]:
        """Get scan status."""
        if job_id not in self._active_processes:
            return None

        process = self._active_processes[job_id]

        return ScanProgress(
            job_id=job_id,
            status="running" if process.returncode is None else "completed",
            progress=50,  # Nmap doesn't provide easy progress
            current_phase="nmap_scan",
            message="Scanning with nmap...",
        )
