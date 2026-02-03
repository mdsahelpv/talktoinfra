"""
Async network scanner for infrastructure discovery.
"""

import asyncio
import ipaddress
import socket
import uuid
from datetime import datetime
from typing import List, Optional, Callable
import structlog

from models import DiscoveredHost, ScanPort, ScanRequest, ScanJob

logger = structlog.get_logger()


class AsyncPortScanner:
    """Async TCP port scanner with service detection."""

    def __init__(self):
        self.scan_jobs = {}  # job_id -> ScanJob
        self.discovered_hosts = {}  # job_id -> List[DiscoveredHost]
        self._stop_flags = {}  # job_id -> asyncio.Event

    async def start_scan(
        self,
        request: ScanRequest,
        created_by: str,
        progress_callback: Optional[Callable[[str, int, int, int], None]] = None,
    ) -> str:
        """Start a new scan job and return job ID."""
        job_id = str(uuid.uuid4())

        # Parse IP range
        network = ipaddress.ip_network(request.ip_range, strict=False)
        hosts = list(network.hosts())
        total_hosts = len(hosts)

        # Create scan job
        job = ScanJob(
            id=job_id,
            status="pending",
            progress=0,
            total_hosts=total_hosts,
            scanned_hosts=0,
            found_hosts=0,
            started_at=datetime.utcnow(),
            created_by=created_by,
        )

        self.scan_jobs[job_id] = job
        self.discovered_hosts[job_id] = []
        self._stop_flags[job_id] = asyncio.Event()

        # Start scan in background
        asyncio.create_task(self._run_scan(job_id, hosts, request, progress_callback))

        logger.info(
            "scan_started",
            job_id=job_id,
            ip_range=request.ip_range,
            ports=len(request.ports),
            total_hosts=total_hosts,
            created_by=created_by,
        )

        return job_id

    async def _run_scan(
        self,
        job_id: str,
        hosts: List[ipaddress.IPv4Address],
        request: ScanRequest,
        progress_callback: Optional[Callable[[str, int, int, int], None]],
    ):
        """Run the actual scan."""
        job = self.scan_jobs[job_id]
        job.status = "running"
        stop_event = self._stop_flags[job_id]

        semaphore = asyncio.Semaphore(request.concurrent_limit)
        scanned = 0
        found = 0

        async def scan_host_with_limit(host: ipaddress.IPv4Address):
            nonlocal scanned, found

            if stop_event.is_set():
                return

            async with semaphore:
                result = await self._scan_single_host(
                    str(host), request.ports, request.timeout, request.service_detection
                )

                scanned += 1

                if result and result.status == "alive":
                    found += 1
                    self.discovered_hosts[job_id].append(result)

                # Update progress
                progress = int((scanned / len(hosts)) * 100)
                job.progress = progress
                job.scanned_hosts = scanned
                job.found_hosts = found

                # Call progress callback if provided
                if progress_callback and scanned % 10 == 0:  # Update every 10 hosts
                    try:
                        progress_callback(job_id, progress, scanned, found)
                    except Exception as e:
                        logger.error("progress_callback_error", error=str(e))

                # Log progress periodically
                if scanned % 50 == 0 or scanned == len(hosts):
                    logger.info(
                        "scan_progress",
                        job_id=job_id,
                        progress=f"{progress}%",
                        scanned=scanned,
                        total=len(hosts),
                        found=found,
                    )

        try:
            # Run all scans concurrently with semaphore limit
            await asyncio.gather(*[scan_host_with_limit(host) for host in hosts])

            job.status = "completed"
            job.completed_at = datetime.utcnow()

            logger.info(
                "scan_completed",
                job_id=job_id,
                total_scanned=scanned,
                total_found=found,
                duration_seconds=(job.completed_at - job.started_at).total_seconds(),
            )

        except asyncio.CancelledError:
            job.status = "failed"
            job.error = "Scan cancelled by user"
            logger.warning("scan_cancelled", job_id=job_id)

        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            logger.error("scan_failed", job_id=job_id, error=str(e))

    async def _scan_single_host(
        self, ip: str, ports: List[int], timeout: float, service_detection: bool
    ) -> Optional[DiscoveredHost]:
        """Scan a single host for open ports."""
        open_ports = []
        is_alive = False
        response_time = None

        # Try to resolve hostname
        hostname = None
        try:
            hostname = socket.gethostbyaddr(ip)[0]
        except (socket.herror, socket.gaierror):
            pass

        # Scan ports concurrently
        async def check_port(port: int) -> Optional[ScanPort]:
            try:
                start_time = asyncio.get_event_loop().time()

                # Try to connect
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
                        reader, writer, port
                    )

                writer.close()
                await writer.wait_closed()

                return ScanPort(
                    port=port, status="open", service=service_name, banner=banner
                ), response_ms

            except asyncio.TimeoutError:
                return ScanPort(port=port, status="closed"), None
            except ConnectionRefusedError:
                return ScanPort(port=port, status="closed"), None
            except OSError:
                return ScanPort(port=port, status="filtered"), None
            except Exception:
                return ScanPort(port=port, status="closed"), None

        # Check all ports
        port_results = await asyncio.gather(*[check_port(port) for port in ports])

        for result, resp_time in port_results:
            if result.status == "open":
                open_ports.append(result)
                is_alive = True
                if resp_time:
                    response_time = resp_time

        if not is_alive:
            return DiscoveredHost(
                id=str(uuid.uuid4()),
                ip_address=ip,
                hostname=hostname,
                ports=[],
                status="unreachable",
                discovered_at=datetime.utcnow(),
            )

        return DiscoveredHost(
            id=str(uuid.uuid4()),
            ip_address=ip,
            hostname=hostname,
            ports=open_ports,
            status="alive",
            response_time_ms=response_time,
            discovered_at=datetime.utcnow(),
        )

    async def _detect_service(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, port: int
    ) -> tuple:
        """Detect service type and grab banner."""
        service_map = {
            22: "ssh",
            80: "http",
            443: "https",
            5432: "postgresql",
            3306: "mysql",
            6379: "redis",
            27017: "mongodb",
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

        # Try to grab banner for specific ports
        try:
            if port in [22, 25, 110, 143]:
                # Read banner directly
                data = await asyncio.wait_for(reader.read(1024), timeout=1.0)
                if data:
                    banner = data.decode("utf-8", errors="ignore").strip()[:100]

            elif port in [80, 443, 8000, 8001, 8002, 8003, 8004, 8005, 8006]:
                # Send HTTP request
                request = f"HEAD / HTTP/1.0\r\nHost: {port}\r\n\r\n"
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

    def get_job(self, job_id: str) -> Optional[ScanJob]:
        """Get scan job by ID."""
        return self.scan_jobs.get(job_id)

    def get_results(self, job_id: str) -> List[DiscoveredHost]:
        """Get discovered hosts for a job."""
        return self.discovered_hosts.get(job_id, [])

    def stop_scan(self, job_id: str) -> bool:
        """Stop a running scan."""
        if job_id in self._stop_flags:
            self._stop_flags[job_id].set()

            if job_id in self.scan_jobs:
                job = self.scan_jobs[job_id]
                if job.status == "running":
                    job.status = "failed"
                    job.error = "Stopped by user"

            logger.info("scan_stopped", job_id=job_id)
            return True
        return False

    def cleanup_job(self, job_id: str):
        """Clean up job data after retention period."""
        if job_id in self.scan_jobs:
            del self.scan_jobs[job_id]
        if job_id in self.discovered_hosts:
            del self.discovered_hosts[job_id]
        if job_id in self._stop_flags:
            del self._stop_flags[job_id]


# Global scanner instance
scanner = AsyncPortScanner()


# Port presets for common services
PORT_PRESETS = {
    "common": [22, 80, 443, 5432, 6379, 8000, 8001, 8002, 8003, 8004, 8005, 8006, 6443],
    "talkai": [8000, 8001, 8002, 8003, 8004, 8005, 8006],
    "databases": [5432, 3306, 27017, 6379, 9200, 5433, 3307],
    "kubernetes": [6443, 10250, 10251, 10252, 2379, 2380, 10255, 10256],
    "web": [80, 443, 8080, 8443, 3000, 3001, 8000, 9000],
    "ssh": [22, 2222, 8022],
}


def get_preset_ports(preset_name: str) -> List[int]:
    """Get port list for a preset."""
    return PORT_PRESETS.get(preset_name, PORT_PRESETS["common"])


def list_presets() -> List[str]:
    """List available port presets."""
    return list(PORT_PRESETS.keys())
