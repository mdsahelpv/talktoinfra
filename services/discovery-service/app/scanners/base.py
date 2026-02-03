"""
Base scanner interface and common functionality.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable

import structlog

logger = structlog.get_logger()


@dataclass
class ScanPort:
    """Port scan result."""

    port: int
    status: str  # "open", "closed", "filtered"
    service: Optional[str] = None
    service_version: Optional[str] = None
    banner: Optional[str] = None
    protocol: str = "tcp"


@dataclass
class DiscoveredHost:
    """Discovered host result."""

    ip_address: str
    hostname: Optional[str] = None
    status: str = "alive"  # "alive", "unreachable", "filtered"
    response_time_ms: Optional[int] = None
    ports: List[ScanPort] = field(default_factory=list)
    discovered_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScanConfig:
    """Scan configuration."""

    ip_range: str
    ports: List[int]
    timeout: float = 2.0
    concurrent_limit: int = 50
    service_detection: bool = True
    extra_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScanProgress:
    """Scan progress information."""

    job_id: str
    status: str  # "pending", "running", "completed", "failed", "cancelled"
    progress: int  # 0-100
    total_hosts: int = 0
    scanned_hosts: int = 0
    found_hosts: int = 0
    current_phase: Optional[str] = None
    message: Optional[str] = None


class BaseScanner(ABC):
    """Abstract base class for all scanners."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logger.bind(scanner=self.__class__.__name__)

    @property
    @abstractmethod
    def name(self) -> str:
        """Scanner name."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Scanner description."""
        pass

    @property
    @abstractmethod
    def requires_root(self) -> bool:
        """Whether scanner requires root privileges."""
        pass

    @property
    @abstractmethod
    def available(self) -> bool:
        """Whether scanner binary/tool is available."""
        pass

    @abstractmethod
    async def start_scan(
        self,
        scan_config: ScanConfig,
        job_id: str,
        progress_callback: Optional[Callable[[ScanProgress], None]] = None,
    ) -> List[DiscoveredHost]:
        """
        Start a scan and return discovered hosts.

        Args:
            scan_config: Scan configuration
            job_id: Unique job identifier
            progress_callback: Optional callback for progress updates

        Returns:
            List of discovered hosts
        """
        pass

    @abstractmethod
    async def stop_scan(self, job_id: str) -> bool:
        """
        Stop a running scan.

        Args:
            job_id: Job to stop

        Returns:
            True if scan was stopped, False otherwise
        """
        pass

    @abstractmethod
    async def get_status(self, job_id: str) -> Optional[ScanProgress]:
        """
        Get status of a scan job.

        Args:
            job_id: Job ID

        Returns:
            Scan progress or None if job not found
        """
        pass

    def _notify_progress(
        self, callback: Optional[Callable[[ScanProgress], None]], progress: ScanProgress
    ):
        """Notify progress callback if provided."""
        if callback:
            try:
                callback(progress)
            except Exception as e:
                self.logger.error(
                    "progress_callback_error", error=str(e), job_id=progress.job_id
                )


class ScanError(Exception):
    """Scan operation error."""

    pass


class ScannerNotAvailableError(ScanError):
    """Scanner binary not available."""

    pass


class ScanCancelledError(ScanError):
    """Scan was cancelled."""

    pass
