"""
Pure Python async port scanner.
Refactored from api-gateway/scanner.py for database integration.
"""

import asyncio
import ipaddress
import socket
from typing import Any, Callable, Dict, List, Optional, Union

import structlog

from app.scanners.base import (
    BaseScanner,
    DiscoveredHost,
    ScanCancelledError,
    ScanConfig,
    ScanError,
    ScanPort,
    ScanProgress,
)

logger = structlog.get_logger()


class PythonAsyncScanner(BaseScanner):
    """
    Pure Python async TCP port scanner.

    Pros:
    - No external dependencies
    - No root privileges required
    - Cross-platform

    Cons:
    - Slower than masscan/nmap
    - No SYN stealth scanning
    - Limited to TCP connect scans
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._active_scans: Dict[str, Dict[str, Any]] = {}

    @property
    def name(self) -> str:
        return "python"

    @property
    def description(self) -> str:
        return "Pure Python async TCP scanner - no external dependencies"

    @property
    def requires_root(self) -> bool:
        return False

    @property
    def available(self) -> bool:
        return True  # Always available

    async def start_scan(
        self,
        scan_config: ScanConfig,
        job_id: str,
        progress_callback: Optional[Callable[[ScanProgress], None]] = None,
    ) -> List[DiscoveredHost]:
        """Execute async port scan."""

        from app.utils.ip_range import get_hosts_from_range, IPRangeParseError

        self.logger.info(
            "python_scan_started",
            job_id=job_id,
            ip_range=scan_config.ip_range,
            ports=len(scan_config.ports),
        )

        # Parse network using utility that supports CIDR, range, and single IP
        try:
            hosts = get_hosts_from_range(scan_config.ip_range)
            total_hosts = len(hosts)
        except IPRangeParseError as e:
            raise ScanError(f"Invalid IP range: {e}")

        # Initialize scan tracking
        stop_event = asyncio.Event()
        self._active_scans[job_id] = {
            "stop_event": stop_event,
            "total_hosts": total_hosts,
            "scanned": 0,
            "found": 0,
            "hosts": [],
        }

        # Semaphore for concurrency control
        semaphore = asyncio.Semaphore(scan_config.concurrent_limit)
        discovered_hosts: List[DiscoveredHost] = []

        async def scan_host(
            host: Union[ipaddress.IPv4Address, ipaddress.IPv6Address],
        ) -> Optional[DiscoveredHost]:
            """Scan a single host."""
            if stop_event.is_set():
                return None

            async with semaphore:
                result = await self._scan_single_host(
                    str(host),
                    scan_config.ports,
                    scan_config.timeout,
                    scan_config.service_detection,
                )

                # Update progress
                scan_data = self._active_scans[job_id]
                scan_data["scanned"] += 1

                if result and result.status == "alive":
                    scan_data["found"] += 1
                    discovered_hosts.append(result)

                # Calculate and report progress
                progress_pct = int((scan_data["scanned"] / total_hosts) * 100)
                progress = ScanProgress(
                    job_id=job_id,
                    status="cancelled" if stop_event.is_set() else "running",
                    progress=progress_pct,
                    total_hosts=total_hosts,
                    scanned_hosts=scan_data["scanned"],
                    found_hosts=scan_data["found"],
                )

                # Notify every 10 hosts or on completion
                if (
                    scan_data["scanned"] % 10 == 0
                    or scan_data["scanned"] == total_hosts
                ):
                    self._notify_progress(progress_callback, progress)

                return result

        try:
            # Execute scans
            await asyncio.gather(*[scan_host(host) for host in hosts])

            if stop_event.is_set():
                raise ScanCancelledError(f"Scan {job_id} was cancelled")

            self.logger.info(
                "python_scan_completed",
                job_id=job_id,
                total_hosts=total_hosts,
                found_hosts=len(discovered_hosts),
            )

            return discovered_hosts

        finally:
            # Cleanup
            if job_id in self._active_scans:
                del self._active_scans[job_id]

    async def _scan_single_host(
        self, ip: str, ports: List[int], timeout: float, service_detection: bool
    ) -> Optional[DiscoveredHost]:
        """Scan a single host for open ports."""
        open_ports: List[ScanPort] = []
        is_alive = False
        response_time = None

        # Try to resolve hostname
        hostname = None
        try:
            hostname = socket.gethostbyaddr(ip)[0]
        except (socket.herror, socket.gaierror):
            pass

        # Scan ports concurrently
        port_results = await asyncio.gather(
            *[self._check_port(ip, port, timeout, service_detection) for port in ports]
        )

        for port_info, resp_time in port_results:
            if port_info.status == "open":
                open_ports.append(port_info)
                is_alive = True
                if resp_time and response_time is None:
                    response_time = resp_time

        if not is_alive:
            return DiscoveredHost(
                ip_address=ip, hostname=hostname, status="unreachable", ports=[]
            )

        return DiscoveredHost(
            ip_address=ip,
            hostname=hostname,
            status="alive",
            response_time_ms=response_time,
            ports=open_ports,
        )

    async def _check_port(
        self, ip: str, port: int, timeout: float, service_detection: bool
    ):
        """Check if a port is open."""
        try:
            start_time = asyncio.get_event_loop().time()

            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port), timeout=timeout
            )

            end_time = asyncio.get_event_loop().time()
            response_ms = int((end_time - start_time) * 1000)

            # Service detection
            service_name = None
            banner = None

            if service_detection:
                service_name, banner = await self._detect_service(
                    reader, writer, port, ip
                )

            writer.close()
            await writer.wait_closed()

            return (
                ScanPort(port=port, status="open", service=service_name, banner=banner),
                response_ms,
            )

        except asyncio.TimeoutError:
            return ScanPort(port=port, status="closed"), None
        except ConnectionRefusedError:
            return ScanPort(port=port, status="closed"), None
        except OSError:
            return ScanPort(port=port, status="filtered"), None
        except Exception:
            return ScanPort(port=port, status="closed"), None

    async def _detect_service(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        port: int,
        ip: str,
    ):
        """Detect service type and grab banner."""
        service_map = {
            22: "ssh",
            80: "http",
            443: "https",
            5432: "postgresql",
            3306: "mysql",
            6379: "redis",
            27017: "mongodb",
            9200: "elasticsearch",
            8000: "http-api",
            8001: "http-api",
            8002: "http-api",
            8003: "http-api",
            8004: "http-api",
            8005: "http-api",
            8006: "http-api",
            6443: "kubernetes-api",
        }

        service_name = service_map.get(port, "unknown")
        banner = None

        try:
            if port in [22, 25, 110, 143]:
                # Read banner directly
                data = await asyncio.wait_for(reader.read(1024), timeout=1.0)
                if data:
                    banner = data.decode("utf-8", errors="ignore").strip()[:100]

            elif port in [80, 443, 8000, 8001, 8002, 8003, 8004, 8005, 8006, 8080]:
                # Send HTTP request
                request = f"HEAD / HTTP/1.0\r\nHost: {ip}\r\n\r\n"
                writer.write(request.encode())
                await writer.drain()

                data = await asyncio.wait_for(reader.read(1024), timeout=1.0)
                if data:
                    banner = data.decode("utf-8", errors="ignore").split("\n")[0][:100]

            elif port == 6379:
                # Redis ping
                writer.write(b"PING\r\n")
                await writer.drain()
                data = await asyncio.wait_for(reader.read(100), timeout=1.0)
                if data and b"PONG" in data:
                    banner = "Redis"

        except Exception:
            pass

        return service_name, banner

    async def stop_scan(self, job_id: str) -> bool:
        """Stop a running scan."""
        if job_id in self._active_scans:
            self._active_scans[job_id]["stop_event"].set()
            self.logger.info("scan_stopped", job_id=job_id, scanner="python")
            return True
        return False

    async def get_status(self, job_id: str) -> Optional[ScanProgress]:
        """Get scan status."""
        if job_id not in self._active_scans:
            return None

        scan_data = self._active_scans[job_id]
        progress_pct = int((scan_data["scanned"] / scan_data["total_hosts"]) * 100)

        return ScanProgress(
            job_id=job_id,
            status="running",
            progress=progress_pct,
            total_hosts=scan_data["total_hosts"],
            scanned_hosts=scan_data["scanned"],
            found_hosts=scan_data["found"],
        )
