"""
Cloud Auto-Detection from Network Scans.

Detects cloud provider infrastructure (AWS, Azure, GCP) from network scan results,
identifying cloud resources based on metadata endpoints, IP patterns, and service banners.
"""

from dataclasses import dataclass, field
from datetime import datetime
from ipaddress import ip_address, ip_network, IPv4Address
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

import structlog

from app.models import DiscoveredHost, DiscoveredPort

logger = structlog.get_logger()


# Cloud provider metadata endpoints
CLOUD_METADATA_ENDPOINTS: Dict[str, Dict[str, Any]] = {
    "aws": {
        "endpoint": "169.254.169.254",
        "ports": [80, 443, 5000],
        "headers": ["x-aws-ec2-metadata", "amazon"],
        "paths": ["/latest/meta-data/", "/latest/dynamic/instance-identity/"],
    },
    "azure": {
        "endpoint": "169.254.169.254",
        "ports": [80, 443],
        "headers": ["x-azure", "metadata"],
        "paths": ["/metadata/instance", "/metadata/identity/"],
    },
    "gcp": {
        "endpoint": "169.254.169.254",
        "ports": [80, 443],
        "headers": ["x-google", "metadata"],
        "paths": ["/computeMetadata/v1/", "/"],
    },
}

# Cloud provider IP ranges (partial - for pattern matching)
AWS_IP_RANGES: List[str] = [
    "3.5.0.0/16", "13.52.0.0/16", "15.177.0.0/16", "18.34.0.0/16",
    "20.0.0.0/16", "23.0.0.0/16", "34.0.0.0/16", "35.0.0.0/16",
    "44.0.0.0/16", "47.0.0.0/16", "50.0.0.0/16", "52.0.0.0/16",
    "54.0.0.0/16", "63.0.0.0/16", "64.0.0.0/16", "65.0.0.0/16",
    "67.0.0.0/16", "68.0.0.0/16", "69.0.0.0/16", "70.0.0.0/16",
    "71.0.0.0/16", "72.0.0.0/16", "73.0.0.0/16", "74.0.0.0/16",
    "75.0.0.0/16", "76.0.0.0/16", "96.0.0.0/16", "99.0.0.0/16",
    "100.0.0.0/16", "101.0.0.0/16", "102.0.0.0/16", "104.0.0.0/16",
    "107.0.0.0/16", "108.0.0.0/16", "120.0.0.0/16", "130.0.0.0/16",
    "142.0.0.0/16", "143.0.0.0/16", "144.0.0.0/16", "146.0.0.0/16",
    "150.0.0.0/16", "152.0.0.0/16", "157.0.0.0/16", "158.0.0.0/16",
    "159.0.0.0/16", "160.0.0.0/16", "161.0.0.0/16", "162.0.0.0/16",
    "167.0.0.0/16", "168.0.0.0/16", "172.0.0.0/16", "173.0.0.0/16",
    "174.0.0.0/16", "175.0.0.0/16", "176.0.0.0/16", "177.0.0.0/16",
    "178.0.0.0/16", "184.0.0.0/16", "185.0.0.0/16", "198.0.0.0/16",
    "199.0.0.0/16", "204.0.0.0/16", "205.0.0.0/16", "207.0.0.0/16",
    "208.0.0.0/16", "216.0.0.0/16",
]

AZURE_IP_RANGES: List[str] = [
    "13.64.0.0/16", "13.65.0.0/16", "13.66.0.0/16", "13.67.0.0/16",
    "13.68.0.0/16", "13.69.0.0/16", "13.70.0.0/16", "13.71.0.0/16",
    "13.72.0.0/16", "13.73.0.0/16", "13.74.0.0/16", "13.75.0.0/16",
    "13.76.0.0/16", "13.77.0.0/16", "13.78.0.0/16", "13.79.0.0/16",
    "13.80.0.0/16", "13.81.0.0/16", "13.82.0.0/16", "13.83.0.0/16",
    "20.0.0.0/16", "23.0.0.0/16", "40.0.0.0/16", "42.0.0.0/16",
    "51.0.0.0/16", "52.0.0.0/16", "64.0.0.0/16", "65.0.0.0/16",
    "66.0.0.0/16", "104.0.0.0/16", "137.0.0.0/16", "138.0.0.0/16",
    "139.0.0.0/16", "140.0.0.0/16", "143.0.0.0/16", "147.0.0.0/16",
    "157.0.0.0/16", "168.0.0.0/16", "191.0.0.0/16", "198.0.0.0/16",
    "199.0.0.0/16", "201.0.0.0/16", "207.0.0.0/16", "208.0.0.0/16",
]

GCP_IP_RANGES: List[str] = [
    "8.34.0.0/16", "8.35.0.0/16", "23.0.0.0/16", "34.0.0.0/16",
    "35.0.0.0/16", "104.0.0.0/16", "107.0.0.0/16", "130.0.0.0/16",
    "132.0.0.0/16", "138.0.0.0/16", "142.0.0.0/16", "146.0.0.0/16",
    "173.0.0.0/16", "192.0.0.0/16", "199.0.0.0/16", "208.0.0.0/16",
]

# Common cloud service ports
AWS_COMMON_PORTS: Set[int] = {22, 80, 443, 4433, 7222, 8000, 8080, 8443, 9000}
AZURE_COMMON_PORTS: Set[int] = {
    22, 80, 443, 3389, 8080, 8443, 9000, 1433, 5432}
GCP_COMMON_PORTS: Set[int] = {22, 80, 443, 3389, 8080, 8443, 9000, 50051}


@dataclass
class CloudHostInfo:
    """Information about a detected cloud host."""

    host_id: UUID
    ip_address: str
    cloud_provider: Optional[str] = None
    is_metadata_endpoint: bool = False
    metadata_service: Optional[str] = None
    detected_services: List[str] = field(default_factory=list)
    confidence_score: float = 0.0
    region_hint: Optional[str] = None
    instance_id_hint: Optional[str] = None


@dataclass
class CloudAccountInfo:
    """Information about a detected cloud account/environment."""

    provider: str
    account_id: Optional[str] = None
    region: Optional[str] = None
    hosts: List[str] = field(default_factory=list)
    confidence_score: float = 0.0
    detected_services: List[str] = field(default_factory=list)
    metadata_endpoints_found: List[str] = field(default_factory=list)
    scan_id: Optional[UUID] = None
    detected_at: datetime = field(default_factory=datetime.utcnow)


class CloudDetector:
    """Detects cloud provider infrastructure from network scan results."""

    def __init__(self):
        """Initialize cloud detector."""
        self._host_cache: Dict[UUID, CloudHostInfo] = {}

    def detect_cloud_host(
        self, host: DiscoveredHost, ports: List[DiscoveredPort]
    ) -> Optional[CloudHostInfo]:
        """Detect if a host is a cloud resource.

        Args:
            host: Discovered host information
            ports: List of discovered ports on the host

        Returns:
            CloudHostInfo if cloud detected, None otherwise
        """
        host_info = CloudHostInfo(
            host_id=host.id,
            ip_address=str(host.ip_address),
        )

        # Check for metadata endpoint
        host_ip = ip_address(host.ip_address)
        for provider, config in CLOUD_METADATA_ENDPOINTS.items():
            if str(host_ip) == config["endpoint"]:
                # Check if metadata ports are open
                for port in ports:
                    if port.status != "open":
                        continue
                    if port.port in config["ports"]:
                        host_info.is_metadata_endpoint = True
                        host_info.metadata_service = provider
                        host_info.cloud_provider = provider
                        host_info.confidence_score = 0.95
                        logger.debug(
                            "cloud_metadata_detected",
                            ip_address=host_info.ip_address,
                            provider=provider,
                        )
                        break

        # Check for metadata endpoint in port banners
        for port in ports:
            if port.status != "open":
                continue
            banner = port.banner or ""
            banner_lower = banner.lower()

            # Check for AWS metadata in banner
            if "169.254.169.254" in banner_lower or "aws" in banner_lower:
                if not host_info.cloud_provider:
                    host_info.cloud_provider = "aws"
                    host_info.confidence_score = max(
                        host_info.confidence_score, 0.6)

            # Check for Azure metadata in banner
            if "x-azure" in banner_lower or "azure" in banner_lower:
                if not host_info.cloud_provider:
                    host_info.cloud_provider = "azure"
                    host_info.confidence_score = max(
                        host_info.confidence_score, 0.6)

            # Check for GCP metadata in banner
            if "google" in banner_lower or "gcp" in banner_lower:
                if not host_info.cloud_provider:
                    host_info.cloud_provider = "gcp"
                    host_info.confidence_score = max(
                        host_info.confidence_score, 0.6)

            # Extract region hints from banners
            if "us-east-1" in banner_lower or "us-east-2" in banner_lower:
                host_info.region_hint = "us-east"
            elif "us-west-1" in banner_lower or "us-west-2" in banner_lower:
                host_info.region_hint = "us-west"
            elif "eu-west-1" in banner_lower or "eu-central-1" in banner_lower:
                host_info.region_hint = "eu"
            elif "ap-southeast" in banner_lower or "ap-northeast" in banner_lower:
                host_info.region_hint = "apac"

            # Extract instance ID hints
            if "i-" in banner_lower:
                host_info.instance_id_hint = "aws"
            elif "/subscriptions/" in banner_lower:
                host_info.instance_id_hint = "azure"
            elif "projects/" in banner_lower:
                host_info.instance_id_hint = "gcp"

        # Check IP range patterns if no metadata detection
        if not host_info.cloud_provider:
            cloud_provider = self._check_ip_ranges(host_ip)
            if cloud_provider:
                host_info.cloud_provider = cloud_provider
                host_info.confidence_score = max(
                    host_info.confidence_score, 0.5)
                logger.debug(
                    "cloud_ip_detected",
                    ip_address=host_info.ip_address,
                    provider=cloud_provider,
                )

        # Detect common cloud services
        open_ports = [p.port for p in ports if p.status == "open"]
        host_info.detected_services = self._detect_cloud_services(
            host_info.cloud_provider, open_ports)

        if host_info.cloud_provider:
            self._host_cache[host.id] = host_info
            return host_info

        return None

    def _check_ip_ranges(self, ip: IPv4Address) -> Optional[str]:
        """Check if IP falls within known cloud provider ranges.

        Args:
            ip: IP address to check

        Returns:
            Cloud provider name or None
        """
        ip_str = str(ip)

        # Check AWS ranges
        for cidr in AWS_IP_RANGES:
            try:
                if ip in ip_network(cidr):
                    return "aws"
            except ValueError:
                continue

        # Check Azure ranges
        for cidr in AZURE_IP_RANGES:
            try:
                if ip in ip_network(cidr):
                    return "azure"
            except ValueError:
                continue

        # Check GCP ranges
        for cidr in GCP_IP_RANGES:
            try:
                if ip in ip_network(cidr):
                    return "gcp"
            except ValueError:
                continue

        return None

    def _detect_cloud_services(
        self, provider: Optional[str], open_ports: List[int]
    ) -> List[str]:
        """Detect cloud services from open ports.

        Args:
            provider: Cloud provider
            open_ports: List of open ports

        Returns:
            List of detected services
        """
        services: List[str] = []

        if provider == "aws":
            common_ports = AWS_COMMON_PORTS
        elif provider == "azure":
            common_ports = AZURE_COMMON_PORTS
        elif provider == "gcp":
            common_ports = GCP_COMMON_PORTS
        else:
            common_ports = set()

        for port in open_ports:
            if port == 22:
                services.append("ssh")
            elif port == 80:
                services.append("http")
            elif port == 443:
                services.append("https")
            elif port == 3389:
                services.append("rdp")
            elif port == 5432:
                services.append("postgresql")
            elif port == 3306:
                services.append("mysql")
            elif port == 27017:
                services.append("mongodb")
            elif port == 6379:
                services.append("redis")
            elif port == 9200:
                services.append("elasticsearch")
            elif port == 8080 or port == 8443:
                services.append("web-console")

        return services

    def detect_cloud_accounts(
        self, hosts: List[DiscoveredHost], scan_id: Optional[UUID] = None
    ) -> List[CloudAccountInfo]:
        """Detect cloud accounts/environments from discovered hosts.

        Args:
            hosts: List of discovered hosts
            scan_id: Optional scan job ID

        Returns:
            List of detected cloud account information
        """
        cloud_hosts: List[CloudHostInfo] = []

        for host in hosts:
            port_list = getattr(host, "ports", []) or []
            host_info = self.detect_cloud_host(host, port_list)
            if host_info:
                cloud_hosts.append(host_info)

        # Group hosts by provider
        accounts_by_provider: Dict[str, CloudAccountInfo] = {}

        for host in cloud_hosts:
            provider = host.cloud_provider
            if not provider:
                continue

            if provider not in accounts_by_provider:
                accounts_by_provider[provider] = CloudAccountInfo(
                    provider=provider,
                    scan_id=scan_id,
                )

            account = accounts_by_provider[provider]
            account.hosts.append(host.ip_address)
            account.confidence_score = max(
                account.confidence_score, host.confidence_score)

            if host.metadata_service:
                account.metadata_endpoints_found.append(host.ip_address)

            # Merge detected services
            for service in host.detected_services:
                if service not in account.detected_services:
                    account.detected_services.append(service)

            # Set region from first host
            if not account.region and host.region_hint:
                account.region = host.region_hint

        logger.info(
            "cloud_detection_complete",
            total_hosts=len(hosts),
            cloud_hosts=len(cloud_hosts),
            accounts_detected=len(accounts_by_provider),
        )

        return list(accounts_by_provider.values())

    def get_detection_metadata(self, account: CloudAccountInfo) -> Dict[str, Any]:
        """Get detection metadata for a cloud account.

        Args:
            account: Cloud account information

        Returns:
            Dictionary containing detection metadata
        """
        return {
            "provider": account.provider,
            "account_id": account.account_id,
            "region": account.region,
            "host_count": len(account.hosts),
            "confidence_score": account.confidence_score,
            "detection_type": "cloud_auto_detected",
            "detected_services": account.detected_services,
            "metadata_endpoints_found": account.metadata_endpoints_found,
            "scan_id": str(account.scan_id) if account.scan_id else None,
            "detected_at": account.detected_at.isoformat(),
            "recommendation": self._get_recommendation(account),
        }

    def _get_recommendation(self, account: CloudAccountInfo) -> str:
        """Get onboarding recommendation for a cloud account.

        Args:
            account: Cloud account information

        Returns:
            Recommendation string
        """
        provider = account.provider.upper()

        if account.metadata_endpoints_found:
            return (
                f"{provider} cloud account detected with {len(account.hosts)} hosts. "
                f"Metadata endpoint found at {account.metadata_endpoints_found[0]}. "
                f"Ready for cloud account onboarding."
            )

        return (
            f"Possible {provider} infrastructure detected ({len(account.hosts)} hosts). "
            f"Verify cloud account credentials for full discovery."
        )


# Module-level singleton
_cloud_detector: Optional[CloudDetector] = None


def get_cloud_detector() -> CloudDetector:
    """Get the cloud detector singleton instance."""
    global _cloud_detector
    if _cloud_detector is None:
        _cloud_detector = CloudDetector()
    return _cloud_detector
