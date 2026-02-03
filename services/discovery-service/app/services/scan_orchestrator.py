"""
Scan orchestrator - Coordinates multi-stage scans (Masscan -> Nmap).
"""

import asyncio
import ipaddress
from typing import Callable, List, Optional
from uuid import UUID

import structlog

from app.config import get_settings
from app.monitoring import metrics
from app.scanners.base import (
    BaseScanner,
    DiscoveredHost,
    ScanCancelledError,
    ScanConfig,
    ScanProgress,
)
from app.scanners.factory import ScannerFactory
from app.services.job_manager import JobManager

logger = structlog.get_logger()


class ScanOrchestrator:
    """
    Orchestrates complex scan workflows.

    Supports hybrid scanning:
    1. Fast phase (Masscan): Quick discovery of alive hosts
    2. Detailed phase (Nmap): Service detection on discovered hosts
    """

    def __init__(self, job_manager: JobManager):
        self.job_manager = job_manager
        self.settings = get_settings()
        self.logger = logger
        self._active_orchestrations: dict = {}

    async def execute_scan(
        self,
        scan_type: str,
        ip_range: str,
        ports: List[int],
        timeout: Optional[float] = None,
        concurrent_limit: Optional[int] = None,
        service_detection: bool = True,
        created_by: str = "unknown",
    ) -> UUID:
        """
        Execute a scan with orchestration.

        Args:
            scan_type: "python", "fast", "detailed", or "hybrid"
            ip_range: CIDR notation
            ports: Ports to scan
            timeout: Timeout per host
            concurrent_limit: Max concurrent connections
            service_detection: Enable service detection
            created_by: Username who initiated scan

        Returns:
            Job ID
        """
        # Determine host count
        network = ipaddress.ip_network(ip_range, strict=False)
        host_count = network.num_addresses - 2

        # Auto-select scanner if hybrid
        if scan_type == "hybrid":
            scan_type = ScannerFactory.recommend_scanner(
                host_count, need_details=service_detection
            )
            self.logger.info(
                "auto_selected_scanner", host_count=host_count, selected=scan_type
            )

        # Create job
        job = await self.job_manager.create_job(
            scan_type=scan_type,
            ip_range=ip_range,
            ports=ports,
            total_hosts=host_count,
            created_by=created_by,
            config={
                "timeout": timeout or self.settings.python_scan_timeout,
                "concurrent_limit": concurrent_limit
                or self.settings.python_scan_concurrent,
                "service_detection": service_detection,
            },
        )

        # Record job creation metric
        metrics.record_job_created(scan_type)

        # Start scan in background with metrics tracking
        asyncio.create_task(
            self._run_scan_flow(
                job.id, scan_type, ip_range, ports, timeout, service_detection
            )
        )

        return job.id

    async def _run_scan_flow(
        self,
        job_id: UUID,
        scan_type: str,
        ip_range: str,
        ports: List[int],
        timeout: Optional[float],
        service_detection: bool,
    ):
        """Execute the scan workflow with metrics tracking."""
        start_time = asyncio.get_event_loop().time()
        metrics.active_scans.labels(scan_type=scan_type).inc()

        try:
            # Update job status
            await self.job_manager.update_job_status(job_id, "running")
            metrics.record_job_status_change("pending", "running")

            discovered_hosts = []
            if scan_type == "hybrid":
                discovered_hosts = await self._execute_hybrid_scan(
                    job_id, ip_range, ports, timeout, service_detection
                )
            else:
                discovered_hosts = await self._execute_single_scan(
                    job_id, scan_type, ip_range, ports, timeout, service_detection
                )

            # Mark completed
            await self.job_manager.update_job_status(job_id, "completed")
            metrics.record_job_status_change("running", "completed")

            # Record scan completion metrics
            duration = asyncio.get_event_loop().time() - start_time
            metrics.scan_duration_histogram.labels(scan_type=scan_type).observe(
                duration
            )
            metrics.record_scan_completion(
                scan_type, "completed", len(discovered_hosts)
            )

        except ScanCancelledError:
            await self.job_manager.update_job_status(job_id, "cancelled")
            metrics.record_job_status_change("running", "cancelled")
            metrics.record_scan_completion(scan_type, "cancelled")
            self.logger.info("scan_cancelled", job_id=str(job_id))

        except Exception as e:
            await self.job_manager.update_job_status(job_id, "failed", error=str(e))
            metrics.record_job_status_change("running", "failed")
            metrics.record_error("scan_failure", "scan_orchestrator")
            metrics.record_scan_completion(scan_type, "failed")
            self.logger.error("scan_failed", job_id=str(job_id), error=str(e))

        finally:
            metrics.active_scans.labels(scan_type=scan_type).dec()

    async def _execute_single_scan(
        self,
        job_id: UUID,
        scan_type: str,
        ip_range: str,
        ports: List[int],
        timeout: Optional[float],
        service_detection: bool,
    ):
        """Execute a single-phase scan."""
        scanner = ScannerFactory.create_scanner(scan_type)

        scan_config = ScanConfig(
            ip_range=ip_range,
            ports=ports,
            timeout=timeout or self.settings.python_scan_timeout,
            service_detection=service_detection,
            extra_config={"job_id": str(job_id)},
        )

        # Progress callback to update DB
        async def progress_callback(progress: ScanProgress):
            await self.job_manager.update_job_progress(
                job_id, progress.progress, progress.scanned_hosts, progress.found_hosts
            )

        # Run scan
        discovered_hosts = await scanner.start_scan(
            scan_config=scan_config,
            job_id=str(job_id),
            progress_callback=progress_callback,
        )

        # Store results
        await self.job_manager.store_discovered_hosts(job_id, discovered_hosts)

        self.logger.info(
            "single_scan_completed",
            job_id=str(job_id),
            scan_type=scan_type,
            found_hosts=len(discovered_hosts),
        )

    async def _execute_hybrid_scan(
        self,
        job_id: UUID,
        ip_range: str,
        ports: List[int],
        timeout: Optional[float],
        service_detection: bool,
    ):
        """
        Execute two-phase hybrid scan.

        Phase 1: Masscan for fast host discovery
        Phase 2: Nmap for detailed service detection on found hosts
        """
        settings = get_settings()

        # Phase 1: Fast discovery with Masscan
        self.logger.info("hybrid_phase_1_start", job_id=str(job_id))
        await self.job_manager.update_job_progress(
            job_id, 10, 0, 0, current_phase="masscan_discovery"
        )

        masscan = ScannerFactory.create_scanner("fast")
        masscan_config = ScanConfig(
            ip_range=ip_range,
            ports=ports,
            timeout=settings.hybrid_masscan_timeout,
            service_detection=False,  # Skip in masscan phase
            extra_config={"timeout": settings.hybrid_masscan_timeout},
        )

        # Quick progress updates
        async def masscan_progress(progress: ScanProgress):
            # Scale to 0-40% range
            scaled_progress = int(progress.progress * 0.4)
            await self.job_manager.update_job_progress(
                job_id,
                scaled_progress,
                0,
                progress.found_hosts,
                current_phase="masscan_discovery",
            )

        masscan_hosts = await masscan.start_scan(
            scan_config=masscan_config,
            job_id=f"{job_id}_masscan",
            progress_callback=masscan_progress,
        )

        found_count = len(masscan_hosts)
        self.logger.info(
            "hybrid_phase_1_complete", job_id=str(job_id), found_hosts=found_count
        )

        # If too many hosts, skip detailed scan
        if found_count > settings.hybrid_max_hosts_for_nmap:
            self.logger.warning(
                "hybrid_too_many_hosts",
                job_id=str(job_id),
                count=found_count,
                max=settings.hybrid_max_hosts_for_nmap,
            )
            await self.job_manager.store_discovered_hosts(job_id, masscan_hosts)
            await self.job_manager.update_job_progress(
                job_id,
                100,
                found_count,
                found_count,
                current_phase="skipped_detailed",
                message=f"Too many hosts ({found_count}), skipping detailed scan",
            )
            return

        # If no hosts found, we're done
        if found_count == 0:
            self.logger.info("hybrid_no_hosts_found", job_id=str(job_id))
            await self.job_manager.update_job_progress(
                job_id,
                100,
                0,
                0,
                current_phase="complete",
                message="No alive hosts found",
            )
            return

        # Phase 2: Detailed scan with Nmap on found hosts only
        self.logger.info("hybrid_phase_2_start", job_id=str(job_id))
        await self.job_manager.update_job_progress(
            job_id, 45, found_count, 0, current_phase="nmap_detailed"
        )

        nmap = ScannerFactory.create_scanner("detailed")

        # Build target list from discovered hosts
        target_ips = [host.ip_address for host in masscan_hosts]

        # Create temporary network string for Nmap
        if len(target_ips) == 1:
            nmap_target = target_ips[0]
        else:
            # Use comma-separated IPs
            nmap_target = ",".join(target_ips)

        nmap_config = ScanConfig(
            ip_range=nmap_target,
            ports=ports,
            timeout=settings.hybrid_nmap_timeout,
            service_detection=service_detection,
            extra_config={"timeout": settings.hybrid_nmap_timeout},
        )

        async def nmap_progress(progress: ScanProgress):
            # Scale to 45-90% range
            scaled_progress = 45 + int(progress.progress * 0.45)
            await self.job_manager.update_job_progress(
                job_id,
                scaled_progress,
                found_count,
                progress.found_hosts,
                current_phase="nmap_detailed",
            )

        detailed_hosts = await nmap.start_scan(
            scan_config=nmap_config,
            job_id=f"{job_id}_nmap",
            progress_callback=nmap_progress,
        )

        # Store final results
        await self.job_manager.store_discovered_hosts(job_id, detailed_hosts)

        await self.job_manager.update_job_progress(
            job_id, 100, found_count, len(detailed_hosts), current_phase="complete"
        )

        self.logger.info(
            "hybrid_scan_completed",
            job_id=str(job_id),
            phase1_found=found_count,
            phase2_found=len(detailed_hosts),
        )

    async def stop_scan(self, job_id: UUID) -> bool:
        """Stop an active orchestrated scan."""
        # Stop through job manager
        return await self.job_manager.cancel_job(job_id)

    async def get_status(self, job_id: UUID) -> Optional[dict]:
        """Get current status of orchestrated scan."""
        return await self.job_manager.get_job_status(job_id)
