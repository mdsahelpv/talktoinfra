"""
Multi-cluster Kubernetes client support.
Manages connections to multiple Kubernetes clusters.
"""

import os
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

import structlog
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException

logger = structlog.get_logger()


class ClusterStatus(Enum):
    """Cluster connection status."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class ClusterConfig:
    """Configuration for a Kubernetes cluster."""
    name: str
    kubeconfig_path: Optional[str] = None
    kubeconfig_content: Optional[str] = None
    context: Optional[str] = None
    namespace: str = "default"
    is_default: bool = False


@dataclass
class ClusterInfo:
    """Information about a connected cluster."""
    name: str
    status: ClusterStatus
    version: Optional[str] = None
    api_server: Optional[str] = None
    error: Optional[str] = None


class MultiClusterClient:
    """
    Manages connections to multiple Kubernetes clusters.
    
    Supports:
    - Multiple cluster contexts
    - Cluster health monitoring
    - Automatic reconnection
    - Connection pooling
    """

    def __init__(self):
        self._clusters: Dict[str, client.ApiClient] = {}
        self._cluster_configs: Dict[str, ClusterConfig] = {}
        self._default_cluster: Optional[str] = None

    def add_cluster(self, cluster_config: ClusterConfig) -> None:
        """
        Add a cluster configuration.
        
        Args:
            cluster_config: Configuration for the cluster
        """
        self._cluster_configs[cluster_config.name] = cluster_config
        if cluster_config.is_default:
            self._default_cluster = cluster_config.name
        logger.info("cluster_config_added", name=cluster_config.name)

    def remove_cluster(self, cluster_name: str) -> None:
        """
        Remove a cluster configuration.
        
        Args:
            cluster_name: Name of the cluster to remove
        """
        if cluster_name in self._clusters:
            del self._clusters[cluster_name]
        if cluster_name in self._cluster_configs:
            del self._cluster_configs[cluster_name]
        if self._default_cluster == cluster_name:
            self._default_cluster = None
        logger.info("cluster_removed", name=cluster_name)

    async def connect(self, cluster_name: str) -> ClusterInfo:
        """
        Connect to a cluster.
        
        Args:
            cluster_name: Name of the cluster to connect to
            
        Returns:
            ClusterInfo with connection status
        """
        if cluster_name not in self._cluster_configs:
            return ClusterInfo(
                name=cluster_name,
                status=ClusterStatus.ERROR,
                error=f"Cluster '{cluster_name}' not found in configuration",
            )

        cluster_config = self._cluster_configs[cluster_name]

        try:
            # Load kubeconfig based on configuration
            if cluster_config.kubeconfig_path:
                # Load from file path
                config.load_kube_config(
                    config_file=cluster_config.kubeconfig_path,
                    context=cluster_config.context,
                )
            elif cluster_config.kubeconfig_content:
                # Load from content (for secrets/configmaps)
                import tempfile
                with tempfile.NamedTemporaryFile(
                    mode='w', suffix='.kubeconfig', delete=False
                ) as f:
                    f.write(cluster_config.kubeconfig_content)
                    temp_path = f.name
                try:
                    config.load_kube_config(
                        config_file=temp_path,
                        context=cluster_config.context,
                    )
                finally:
                    os.unlink(temp_path)
            else:
                # Try in-cluster config first, then default kubeconfig
                try:
                    config.load_incluster_config()
                except config.ConfigException:
                    config.load_kube_config(context=cluster_config.context)

            # Create API client
            api_client = client.ApiClient()
            self._clusters[cluster_name] = api_client

            # Get cluster info
            version_api = client.VersionApi(api_client)
            version = version_api.get_code()

            # Get API server URL
            api_instance = client.CoreV1Api(api_client)
            api_server = api_instance.api_client.configuration.host

            logger.info("cluster_connected", name=cluster_name, version=version.git_version)

            return ClusterInfo(
                name=cluster_name,
                status=ClusterStatus.CONNECTED,
                version=version.git_version,
                api_server=api_server,
            )

        except Exception as e:
            logger.error("cluster_connection_failed", name=cluster_name, error=str(e))
            return ClusterInfo(
                name=cluster_name,
                status=ClusterStatus.ERROR,
                error=str(e),
            )

    async def disconnect(self, cluster_name: str) -> None:
        """
        Disconnect from a cluster.
        
        Args:
            cluster_name: Name of the cluster to disconnect from
        """
        if cluster_name in self._clusters:
            del self._clusters[cluster_name]
            logger.info("cluster_disconnected", name=cluster_name)

    def get_client(self, cluster_name: Optional[str] = None) -> client.ApiClient:
        """
        Get the API client for a cluster.
        
        Args:
            cluster_name: Name of the cluster. Uses default if not specified.
            
        Returns:
            Kubernetes API client
            
        Raises:
            RuntimeError: If cluster is not connected
        """
        target = cluster_name or self._default_cluster
        if not target:
            raise RuntimeError("No cluster specified and no default cluster set")

        if target not in self._clusters:
            raise RuntimeError(f"Cluster '{target}' is not connected")

        return self._clusters[target]

    def list_clusters(self) -> List[str]:
        """List all configured cluster names."""
        return list(self._cluster_configs.keys())

    def get_connected_clusters(self) -> List[str]:
        """List all connected cluster names."""
        return list(self._clusters.keys())

    async def health_check(self, cluster_name: str) -> ClusterInfo:
        """
        Check the health of a cluster connection.
        
        Args:
            cluster_name: Name of the cluster to check
            
        Returns:
            ClusterInfo with health status
        """
        if cluster_name not in self._clusters:
            return ClusterInfo(
                name=cluster_name,
                status=ClusterStatus.DISCONNECTED,
            )

        try:
            api_client = self._clusters[cluster_name]
            version_api = client.VersionApi(api_client)
            version = version_api.get_code()

            return ClusterInfo(
                name=cluster_name,
                status=ClusterStatus.CONNECTED,
                version=version.git_version,
            )

        except Exception as e:
            logger.warning("cluster_health_check_failed", name=cluster_name, error=str(e))
            return ClusterInfo(
                name=cluster_name,
                status=ClusterStatus.ERROR,
                error=str(e),
            )

    async def health_check_all(self) -> Dict[str, ClusterInfo]:
        """
        Check health of all connected clusters.
        
        Returns:
            Dictionary mapping cluster names to ClusterInfo
        """
        results = {}
        for cluster_name in self._clusters.keys():
            results[cluster_name] = await self.health_check(cluster_name)
        return results


# Global multi-cluster client instance
_multi_cluster_client = MultiClusterClient()


def get_multi_cluster_client() -> MultiClusterClient:
    """Get the global multi-cluster client instance."""
    return _multi_cluster_client


async def initialize_multi_cluster(clusters: List[ClusterConfig]) -> Dict[str, ClusterInfo]:
    """
    Initialize multiple clusters.
    
    Args:
        clusters: List of cluster configurations
        
    Returns:
        Dictionary mapping cluster names to ClusterInfo
    """
    client = get_multi_cluster_client()
    
    # Add all clusters
    for cluster in clusters:
        client.add_cluster(cluster)
    
    # Connect to all clusters
    results = {}
    for cluster in clusters:
        results[cluster.name] = await client.connect(cluster.name)
    
    return results
