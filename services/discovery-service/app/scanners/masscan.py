"""
Masscan scanner wrapper - Ultra-fast SYN scanner.
"""

import asyncio
import ipaddress
import json
import os
import shutil
import tempfile
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


class MasscanScanner(BaseScanner):
    """
    Masscan wrapper - The fastest port scanner.

    Pros:
    - 1000x faster than traditional scanners
    - SYN stealth scanning (requires root)
    - Can scan entire internet in minutes

    Cons:
    - Requires compiled binary
    - Requires root for SYN scans
    - Limited service detection

    Installation:
        apt-get install masscan
        # or build from source
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.binary_path = config.get("masscan_path", "/usr/bin/masscan")
        self.rate = config.get("masscan_rate", 1000)
        self.adapter = config.get("masscan_adapter")
        self.wait_time = config.get("masscan_wait_time", 10)
        self._active_processes: Dict[str, asyncio.subprocess.Process] = {}

    @property
    def name(self) -> str:
        return "masscan"

    @property
    def description(self) -> str:
        return "Ultra-fast SYN scanner - 1000x faster than traditional scanners"

    @property
    def requires_root(self) -> bool:
        return True  # SYN scanning requires root

    @property
    def available(self) -> bool:
        """Check if masscan binary exists."""
        return shutil.which(self.binary_path) is not None

    async def start_scan(
        self,
        scan_config: ScanConfig,
        job_id: str,
        progress_callback: Optional[Callable[[ScanProgress], None]] = None,
    ) -> List[DiscoveredHost]:
        """Execute masscan."""

        if not self.available:
            raise ScannerNotAvailableError(
                f"Masscan binary not found at {self.binary_path}. "
                "Install with: apt-get install masscan"
            )

        self.logger.info(
            "masscan_scan_started",
            job_id=job_id,
            ip_range=scan_config.ip_range,
            ports=len(scan_config.ports),
            rate=self.rate,
        )

        # Create temporary output file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            output_file = f.name

        try:
            # Build masscan command
            from app.utils.ip_range import format_ip_range_for_scanner

            ports_str = ",".join(map(str, scan_config.ports))

            # Format IP range for masscan compatibility
            formatted_range = format_ip_range_for_scanner(
                scan_config.ip_range, "masscan"
            )

            cmd = [
                self.binary_path,
                formatted_range,
                "-p",
                ports_str,
                "--rate",
                str(self.rate),
                "-oJ",
                output_file,  # JSON output
                "--wait",
                str(self.wait_time),
            ]

            # Add adapter if specified
            if self.adapter:
                cmd.extend(["--adapter", self.adapter])

            # Run as user if not root (will use TCP connect instead of SYN)
            if os.geteuid() != 0:
                self.logger.warning(
                    "masscan_not_root",
                    job_id=job_id,
                    message="Running without root - will use TCP connect instead of SYN",
                )

            # Start masscan process
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
                    current_phase="masscan_discovery",
                    message="Starting masscan...",
                ),
            )

            # Wait for completion with timeout
            timeout = scan_config.extra_config.get("timeout", 300)

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                raise ScanCancelledError(
                    f"Masscan scan {job_id} timed out after {timeout}s"
                )

            # Check if cancelled
            if job_id not in self._active_processes:
                raise ScanCancelledError(f"Scan {job_id} was cancelled")

            # Parse results
            discovered_hosts = self._parse_results(output_file)

            # Count total ports and open ports for metrics
            total_ports = sum(len(h.ports) for h in discovered_hosts)
            open_ports = total_ports  # Masscan only returns open ports

            # Record port metrics
            from app.monitoring import metrics

            metrics.record_ports_scanned("masscan", total_ports, open_ports)

            self.logger.info(
                "masscan_scan_completed",
                job_id=job_id,
                found_hosts=len(discovered_hosts),
            )

            # Report completion
            self._notify_progress(
                progress_callback,
                ScanProgress(
                    job_id=job_id,
                    status="completed",
                    progress=100,
                    found_hosts=len(discovered_hosts),
                    message="Masscan completed",
                ),
            )

            return discovered_hosts

        finally:
            # Cleanup
            if job_id in self._active_processes:
                del self._active_processes[job_id]

            try:
                os.unlink(output_file)
            except OSError:
                pass

    def _parse_results(self, output_file: str) -> List[DiscoveredHost]:
        """Parse masscan JSON output."""
        hosts: Dict[str, DiscoveredHost] = {}

        try:
            with open(output_file, "r") as f:
                data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

        # Masscan output format:
        # [{ "ip": "192.168.1.1", "ports": [{ "port": 80, "proto": "tcp", "status": "open" }] }]

        for entry in data:
            ip = entry.get("ip", "")
            if not ip:
                continue

            if ip not in hosts:
                hosts[ip] = DiscoveredHost(ip_address=ip, status="alive", ports=[])

            for port_entry in entry.get("ports", []):
                port_num = port_entry.get("port", 0)
                status = port_entry.get("status", "closed")
                proto = port_entry.get("proto", "tcp")

                if status == "open":
                    hosts[ip].ports.append(
                        ScanPort(port=port_num, status="open", protocol=proto)
                    )

        return list(hosts.values())

    async def stop_scan(self, job_id: str) -> bool:
        """Stop a running masscan scan."""
        if job_id in self._active_processes:
            process = self._active_processes[job_id]
            process.kill()
            del self._active_processes[job_id]
            self.logger.info("masscan_stopped", job_id=job_id)
            return True
        return False

    async def get_status(self, job_id: str) -> Optional[ScanProgress]:
        """Get scan status."""
        if job_id not in self._active_processes:
            return None

        process = self._active_processes[job_id]

        # Masscan doesn't provide progress, so we estimate
        return ScanProgress(
            job_id=job_id,
            status="running" if process.returncode is None else "completed",
            progress=50,  # Unknown, show 50%
            current_phase="masscan_discovery",
            message="Scanning with masscan...",
        )
