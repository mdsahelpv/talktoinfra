"""
Scanner factory - Creates appropriate scanner instances.
"""

from typing import Any, Dict, List

from app.config import get_settings
from app.scanners.base import BaseScanner
from app.scanners.masscan import MasscanScanner
from app.scanners.nmap import NmapScanner
from app.scanners.python_async import PythonAsyncScanner


class ScannerFactory:
    """Factory for creating scanner instances."""

    _scanners: Dict[str, Any] = {}

    @classmethod
    def create_scanner(cls, scan_type: str) -> BaseScanner:
        """
        Create a scanner instance by type.

        Args:
            scan_type: One of "fast", "detailed", "hybrid", "python"

        Returns:
            Scanner instance

        Raises:
            ValueError: If scanner type is unknown
        """
        settings = get_settings()

        config = {
            "masscan_path": settings.masscan_path,
            "masscan_rate": settings.masscan_rate,
            "masscan_adapter": settings.masscan_adapter,
            "masscan_wait_time": settings.masscan_wait_time,
            "nmap_path": settings.nmap_path,
            "nmap_timing_template": settings.nmap_timing_template,
            "nmap_service_detection": settings.nmap_service_detection,
            "nmap_os_detection": settings.nmap_os_detection,
            "nmap_script_scan": settings.nmap_script_scan,
            "python_scan_timeout": settings.python_scan_timeout,
            "python_scan_concurrent": settings.python_scan_concurrent,
        }

        if scan_type == "python":
            return PythonAsyncScanner(config)
        elif scan_type == "fast":
            return MasscanScanner(config)
        elif scan_type == "detailed":
            return NmapScanner(config)
        elif scan_type == "hybrid":
            # Hybrid uses masscan first, then nmap for details
            # This is handled by the orchestrator, but we return masscan as primary
            return MasscanScanner(config)
        else:
            raise ValueError(f"Unknown scanner type: {scan_type}")

    @classmethod
    def get_available_scanners(cls) -> List[Dict[str, Any]]:
        """
        Get list of available scanners with their status.

        Returns:
            List of scanner information dictionaries
        """
        settings = get_settings()

        scanners = []

        # Check Python scanner (always available)
        python_scanner = PythonAsyncScanner({})
        scanners.append(
            {
                "name": "python",
                "description": python_scanner.description,
                "available": True,
                "requires_root": False,
                "recommended_for": "Small networks (< 100 hosts) or when no external tools available",
                "average_speed": "50-100 hosts/sec",
            }
        )

        # Check Masscan
        masscan_scanner = MasscanScanner({"masscan_path": settings.masscan_path})
        scanners.append(
            {
                "name": "fast",
                "description": masscan_scanner.description,
                "available": masscan_scanner.available,
                "requires_root": masscan_scanner.requires_root,
                "recommended_for": "Large networks (100+ hosts), fast discovery",
                "average_speed": "1000-10000 hosts/sec",
            }
        )

        # Check Nmap
        nmap_scanner = NmapScanner({"nmap_path": settings.nmap_path})
        scanners.append(
            {
                "name": "detailed",
                "description": nmap_scanner.description,
                "available": nmap_scanner.available,
                "requires_root": nmap_scanner.requires_root,
                "recommended_for": "Detailed service detection and OS fingerprinting",
                "average_speed": "10-50 hosts/sec with full detection",
            }
        )

        # Hybrid option
        scanners.append(
            {
                "name": "hybrid",
                "description": "Best of both worlds: Masscan for discovery + Nmap for details",
                "available": masscan_scanner.available and nmap_scanner.available,
                "requires_root": masscan_scanner.requires_root,
                "recommended_for": "Production use - recommended default",
                "average_speed": "Fast discovery + detailed follow-up",
            }
        )

        return scanners

    @classmethod
    def recommend_scanner(cls, host_count: int, need_details: bool = True) -> str:
        """
        Recommend best scanner for the job.

        Args:
            host_count: Number of hosts to scan
            need_details: Whether detailed service detection is needed

        Returns:
            Scanner type name
        """
        settings = get_settings()

        # Check available tools
        masscan_available = shutil.which(settings.masscan_path) is not None
        nmap_available = shutil.which(settings.nmap_path) is not None

        # Large networks need fast scanning
        if host_count > 1000:
            if masscan_available:
                return "fast"
            else:
                return "python"

        # Medium networks - use hybrid if available
        if host_count > 100:
            if masscan_available and nmap_available and need_details:
                return "hybrid"
            elif masscan_available:
                return "fast"
            else:
                return "python"

        # Small networks - detailed scanning
        if nmap_available and need_details:
            return "detailed"

        # Fallback to Python
        return "python"


import shutil
