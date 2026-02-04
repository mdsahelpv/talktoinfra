"""
K8s Auto-Detection from Network Scans.

Detects Kubernetes clusters and nodes from port scan results,
identifying potential K8s infrastructure based on characteristic ports and service banners.
"""

from dataclasses import dataclass, field
from datetime import datetime
from ipaddress import ip_network
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

import structlog

from app.models import DiscoveredHost, DiscoveredPort

logger = structlog.get_logger()


# Kubernetes characteristic ports
K8S_API_PORTS: Set[int] = {6443, 8443, 443}
K8S_NODE_PORTS: Set[int] = {10250, 10251,
                            10252, 10255, 10256, 2379, 2380, 8472}
K8S_INGRESS_PORTS: Set[int] = {80, 443, 8080, 8443}
K8S_SERVICE_PORTS: Set[int] = {30000, 30001, 30002, 30080, 30100, 30200}

# Minimum ports to consider for K8s detection
K8S_API_MIN_PORTS: Set[int] = {6443}
K8S_NODE_MIN_PORTS: Set[int] = {10250, 10251, 10252}

# Service detection patterns
K8S_SERVICE_PATTERNS: Dict[str, List[str]] = {
    "k8s_api": ["kubernetes", "k8s", "kube-api"],
    "kubelet": ["kubelet", "k8s-agent", "k8s node"],
    "etcd": ["etcd", "etcd-client"],
    "kube_proxy": ["kube-proxy", "k8s-proxy"],
    "kube_scheduler": ["kube-scheduler", "k8s-scheduler"],
    "kube_controller": ["kube-controller", "k8s-controller"],
}


@dataclass
class K8sHostInfo:
    """Information about a detected K8s host."""

    host_id: UUID
    ip_address: str
    is_k8s_api: bool = False
    is_k8s_node: bool = False
    is_k8s_ingress: bool = False
    detected_ports: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    confidence_score: float = 0.0
    service_banners: List[str] = field(default_factory=list)
    detected_roles: List[str] = field(default_factory=list)


@dataclass
class K8sClusterInfo:
    """Information about a detected K8s cluster."""

    cluster_id: str
    api_endpoints: List[str] = field(default_factory=list)
    node_ips: List[str] = field(default_factory=list)
    master_ips: List[str] = field(default_factory=list)
    etcd_ips: List[str] = field(default_factory=list)
    confidence_score: float = 0.0
    detected_roles: Dict[str, List[str]] = field(default_factory=dict)
    estimated_node_count: int = 0
    estimated_master_count: int = 0
    scan_id: Optional[UUID] = None
    detected_at: datetime = field(default_factory=datetime.utcnow)


class K8sDetector:
    """Detects Kubernetes infrastructure from network scan results."""

    def __init__(self):
        """Initialize K8s detector."""
        self._host_cache: Dict[UUID, K8sHostInfo] = {}

    def detect_k8s_host(self, host: DiscoveredHost, ports: List[DiscoveredPort]) -> Optional[K8sHostInfo]:
        """Detect if a host is part of Kubernetes infrastructure.

        Args:
            host: Discovered host information
            ports: List of discovered ports on the host

        Returns:
            K8sHostInfo if K8s detected, None otherwise
        """
        host_info = K8sHostInfo(
            host_id=host.id,
            ip_address=str(host.ip_address),
        )

        detected_ports: Dict[int, Dict[str, Any]] = {}
        service_banners: List[str] = []

        for port in ports:
            if port.status != "open":
                continue

            port_info: Dict[str, Any] = {
                "port": port.port,
                "service": port.service,
                "banner": port.banner,
            }
            detected_ports[port.port] = port_info

            if port.banner:
                service_banners.append(port.banner)

        # Check for K8s API server
        if any(p in detected_ports for p in K8S_API_PORTS):
            host_info.is_k8s_api = True
            host_info.detected_roles.append("api-server")
            logger.debug("k8s_api_detected", ip_address=host_info.ip_address)

        # Check for K8s node ports (kubelet, etcd, etc.)
        node_port_matches = sum(
            1 for p in K8S_NODE_PORTS if p in detected_ports)
        if node_port_matches >= 2:
            host_info.is_k8s_node = True
            host_info.detected_roles.append("node")

            # Identify specific node roles
            if 10250 in detected_ports:
                host_info.detected_roles.append("kubelet")
            if 2379 in detected_ports:
                host_info.detected_roles.append("etcd")
            if 10251 in detected_ports:
                host_info.detected_roles.append("kube-scheduler")
            if 10252 in detected_ports:
                host_info.detected_roles.append("kube-controller-manager")

            logger.debug("k8s_node_detected", ip_address=host_info.ip_address,
                         roles=host_info.detected_roles)

        # Check for ingress/controller ports
        if any(p in detected_ports for p in K8S_INGRESS_PORTS):
            host_info.is_k8s_ingress = True
            host_info.detected_roles.append("ingress")
            logger.debug("k8s_ingress_detected",
                         ip_address=host_info.ip_address)

        # Detect from service banners
        for port in detected_ports.values():
            banner = port.get("banner", "") or ""
            service = port.get("service", "") or ""

            for role, patterns in K8S_SERVICE_PATTERNS.items():
                for pattern in patterns:
                    if pattern.lower() in banner.lower() or pattern.lower() in service.lower():
                        if role not in host_info.detected_roles:
                            host_info.detected_roles.append(role)
                        break

        host_info.detected_ports = detected_ports
        host_info.service_banners = service_banners

        # Calculate confidence score
        host_info.confidence_score = self._calculate_host_confidence(host_info)

        # Only return if there's meaningful detection
        if host_info.confidence_score > 0:
            self._host_cache[host.id] = host_info
            return host_info

        return None

    def _calculate_host_confidence(self, host_info: K8sHostInfo) -> float:
        """Calculate confidence score for K8s detection.

        Args:
            host_info: K8s host information

        Returns:
            Confidence score between 0.0 and 1.0
        """
        score = 0.0

        # K8s API server is high confidence
        if host_info.is_k8s_api:
            score += 0.5
            # Additional points for standard port
            if 6443 in host_info.detected_ports:
                score += 0.2

        # K8s node with multiple K8s ports
        if host_info.is_k8s_node:
            score += 0.4
            # More ports = higher confidence
            node_ports_found = sum(
                1 for p in K8S_NODE_PORTS if p in host_info.detected_ports)
            score += min(node_ports_found * 0.1, 0.2)

        # Service banner detection
        for banner in host_info.service_banners:
            banner_lower = banner.lower()
            if "kubernetes" in banner_lower:
                score += 0.15
            if "kubelet" in banner_lower:
                score += 0.1
            if "etcd" in banner_lower:
                score += 0.1

        return min(score, 1.0)

    def detect_clusters(
        self, hosts: List[DiscoveredHost], scan_id: Optional[UUID] = None
    ) -> List[K8sClusterInfo]:
        """Detect K8s clusters from a list of discovered hosts.

        Args:
            hosts: List of discovered hosts
            scan_id: Optional scan job ID

        Returns:
            List of detected K8s cluster information
        """
        # First pass: detect individual K8s hosts
        k8s_hosts: List[K8sHostInfo] = []

        for host in hosts:
            # Get ports for this host
            port_list = getattr(host, "ports", []) or []
            host_info = self.detect_k8s_host(host, port_list)
            if host_info:
                k8s_hosts.append(host_info)

        # Second pass: group hosts into clusters
        clusters = self._group_into_clusters(k8s_hosts, scan_id)

        logger.info(
            "k8s_detection_complete",
            total_hosts=len(hosts),
            k8s_hosts=len(k8s_hosts),
            clusters_detected=len(clusters),
        )

        return clusters

    def _group_into_clusters(
        self, k8s_hosts: List[K8sHostInfo], scan_id: Optional[UUID]
    ) -> List[K8sClusterInfo]:
        """Group K8s hosts into clusters based on IP ranges and roles.

        Args:
            k8s_hosts: List of detected K8s hosts
            scan_id: Optional scan job ID

        Returns:
            List of detected K8s clusters
        """
        if not k8s_hosts:
            return []

        # Sort hosts by IP for consistent grouping
        sorted_hosts = sorted(k8s_hosts, key=lambda h: h.ip_address)

        # Group by /24 subnets (simplified clustering)
        subnet_groups: Dict[str, List[K8sHostInfo]] = {}
        for host in sorted_hosts:
            ip_parts = host.ip_address.rsplit(".", 1)[0]
            subnet = f"{ip_parts}.0/24"
            if subnet not in subnet_groups:
                subnet_groups[subnet] = []
            subnet_groups[subnet].append(host)

        clusters: List[K8sClusterInfo] = []

        for subnet, hosts_in_subnet in subnet_groups.items():
            cluster = self._create_cluster_info(
                subnet, hosts_in_subnet, scan_id)
            if cluster.confidence_score > 0.3:
                clusters.append(cluster)

        # Cross-reference API servers across subnets to find master nodes
        self._identify_master_nodes(clusters, k8s_hosts)

        return clusters

    def _create_cluster_info(
        self, subnet: str, hosts: List[K8sHostInfo], scan_id: Optional[UUID]
    ) -> K8sClusterInfo:
        """Create cluster info from hosts in a subnet.

        Args:
            subnet: Subnet string
            hosts: List of K8s hosts in this subnet
            scan_id: Optional scan job ID

        Returns:
            K8sClusterInfo
        """
        cluster_id = f"cluster-{subnet.replace('.', '-').replace('/', '-')}"

        cluster = K8sClusterInfo(
            cluster_id=cluster_id,
            scan_id=scan_id,
        )

        api_endpoints: List[str] = []
        node_ips: List[str] = []
        master_ips: List[str] = []
        etcd_ips: List[str] = []

        for host in hosts:
            if host.is_k8s_api:
                api_endpoints.append(host.ip_address)
            if host.is_k8s_node:
                node_ips.append(host.ip_address)
            if "etcd" in host.detected_roles:
                etcd_ips.append(host.ip_address)

        cluster.api_endpoints = api_endpoints
        cluster.node_ips = node_ips
        cluster.etcd_ips = etcd_ips
        cluster.estimated_node_count = len(node_ips)
        cluster.estimated_master_count = len(api_endpoints)

        # Calculate cluster confidence
        if api_endpoints:
            cluster.confidence_score = 0.9
        elif node_ips:
            cluster.confidence_score = 0.6
        else:
            cluster.confidence_score = 0.3

        cluster.detected_roles = {
            "api_servers": api_endpoints,
            "nodes": node_ips,
            "etcd": etcd_ips,
        }

        return cluster

    def _identify_master_nodes(
        self, clusters: List[K8sClusterInfo], all_hosts: List[K8sHostInfo]
    ) -> None:
        """Identify master nodes across cluster groups.

        Args:
            clusters: List of detected clusters
            all_hosts: All K8s hosts detected
        """
        # Create lookup by IP
        host_by_ip = {h.ip_address: h for h in all_hosts}

        for cluster in clusters:
            for api_ip in cluster.api_endpoints:
                if api_ip in host_by_ip:
                    host = host_by_ip[api_ip]
                    if "scheduler" in host.detected_roles or "controller" in host.detected_roles:
                        if api_ip not in cluster.master_ips:
                            cluster.master_ips.append(api_ip)

    def get_detection_metadata(self, cluster: K8sClusterInfo) -> Dict[str, Any]:
        """Get detection metadata for a cluster.

        Args:
            cluster: K8s cluster information

        Returns:
            Dictionary containing detection metadata
        """
        return {
            "cluster_id": cluster.cluster_id,
            "confidence_score": cluster.confidence_score,
            "detection_type": "k8s_auto_detected",
            "api_endpoints": cluster.api_endpoints,
            "node_count": cluster.estimated_node_count,
            "master_count": cluster.estimated_master_count,
            "detected_roles": cluster.detected_roles,
            "scan_id": str(cluster.scan_id) if cluster.scan_id else None,
            "detected_at": cluster.detected_at.isoformat(),
            "recommendation": self._get_recommendation(cluster),
        }

    def _get_recommendation(self, cluster: K8sClusterInfo) -> str:
        """Get onboarding recommendation for a cluster.

        Args:
            cluster: K8s cluster information

        Returns:
            Recommendation string
        """
        if cluster.confidence_score >= 0.8:
            if cluster.api_endpoints:
                return f"High confidence K8s cluster detected with API at {', '.join(cluster.api_endpoints)}. Ready for one-click onboarding."
            return f"High confidence K8s cluster detected with {cluster.estimated_node_count} nodes. Manual API endpoint entry required."
        elif cluster.confidence_score >= 0.5:
            return f"Possible K8s cluster detected ({cluster.estimated_node_count} nodes). Verify API endpoint manually."
        else:
            return f"Potential K8s infrastructure found. Further investigation recommended."


# Module-level singleton
_k8s_detector: Optional[K8sDetector] = None


def get_k8s_detector() -> K8sDetector:
    """Get the K8s detector singleton instance."""
    global _k8s_detector
    if _k8s_detector is None:
        _k8s_detector = K8sDetector()
    return _k8s_detector
