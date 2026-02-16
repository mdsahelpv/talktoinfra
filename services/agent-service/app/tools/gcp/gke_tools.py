"""
Google Kubernetes Engine (GKE) Tools

Provides tools for managing Google Kubernetes Engine clusters.
"""

from typing import Any, Dict, List, Optional
from google.cloud import container_v1
from google.api_core.exceptions import GoogleAPIError
import structlog


logger = structlog.get_logger()


def get_gke_client() -> container_v1.ClusterManagerClient:
    """Get GKE Cluster Manager Client.

    Returns:
        ClusterManagerClient instance
    """
    return container_v1.ClusterManagerClient()


async def list_gke_clusters(
    project_id: str,
    location: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List Google Kubernetes Engine clusters.

    Args:
        project_id: GCP project ID
        location: Optional location/zone to filter by (e.g., 'us-central1')

    Returns:
        List of GKE cluster information dictionaries
    """
    try:
        client = get_gke_client()
        
        result = []
        
        if location:
            # List clusters in specific location
            parent = f"projects/{project_id}/locations/{location}"
            clusters = client.list_clusters(parent=parent)
            for cluster in clusters.clusters:
                result.append(_format_cluster(cluster, location))
        else:
            # List clusters in all locations
            # Get list of locations first
            locations_client = container_v1.LocationsClient()
            locations = locations_client.list_locations(parent=f"projects/{project_id}")
            
            for loc in locations.locations:
                try:
                    parent = f"projects/{project_id}/locations/{loc.location_id}"
                    clusters = client.list_clusters(parent=parent)
                    for cluster in clusters.clusters:
                        result.append(_format_cluster(cluster, loc.location_id))
                except GoogleAPIError:
                    continue

        logger.info("gke_clusters_listed", count=len(result), project_id=project_id)
        return result

    except GoogleAPIError as e:
        logger.error("gke_list_clusters_failed", error=str(e))
        raise


async def get_gke_cluster(
    project_id: str,
    location: str,
    cluster_name: str,
) -> Dict[str, Any]:
    """Get Google Kubernetes Engine cluster details.

    Args:
        project_id: GCP project ID
        location: Location/zone (e.g., 'us-central1-a')
        cluster_name: Cluster name

    Returns:
        GKE cluster information dictionary
    """
    try:
        client = get_gke_client()
        
        name = f"projects/{project_id}/locations/{location}/clusters/{cluster_name}"
        cluster = client.get_cluster(name=name)

        result = _format_cluster(cluster, location)
        result["location"] = location

        logger.info("gke_cluster_retrieved", cluster_name=cluster_name, location=location)
        return result

    except GoogleAPIError as e:
        logger.error("gke_get_cluster_failed", error=str(e), cluster_name=cluster_name)
        raise


async def get_gke_cluster_credentials(
    project_id: str,
    location: str,
    cluster_name: str,
) -> Dict[str, Any]:
    """Get Google Kubernetes Engine cluster credentials.

    Args:
        project_id: GCP project ID
        location: Location/zone (e.g., 'us-central1-a')
        cluster_name: Cluster name

    Returns:
        Dictionary containing kubeconfig and cluster info
    """
    try:
        client = get_gke_client()
        
        name = f"projects/{project_id}/locations/{location}/clusters/{cluster_name}"
        
        # Get cluster credentials
        cluster = client.get_cluster(name=name)
        
        # Build kubeconfig
        kubeconfig = _build_kubeconfig(project_id, location, cluster_name, cluster.endpoint)
        
        result = {
            "cluster_name": cluster_name,
            "location": location,
            "endpoint": cluster.endpoint,
            "kubeconfig": kubeconfig,
        }

        logger.info("gke_cluster_credentials_retrieved", cluster_name=cluster_name, location=location)
        return result

    except GoogleAPIError as e:
        logger.error("gke_get_cluster_credentials_failed", error=str(e), cluster_name=cluster_name)
        raise


async def resize_gke_node_pool(
    project_id: str,
    location: str,
    cluster_name: str,
    node_pool_name: str,
    node_count: int,
) -> Dict[str, Any]:
    """Resize a GKE node pool.

    Args:
        project_id: GCP project ID
        location: Location/zone (e.g., 'us-central1-a')
        cluster_name: Cluster name
        node_pool_name: Node pool name
        node_count: New node count

    Returns:
        Operation result dictionary
    """
    try:
        client = get_gke_client()
        
        name = f"projects/{project_id}/locations/{location}/clusters/{cluster_name}/nodePools/{node_pool_name}"
        
        # Get current node pool
        node_pool = client.get_node_pool(name=name)
        
        # Update node count
        node_pool.config.num_nodes = node_count
        
        # Resize node pool
        operation = client.set_node_pool_size(
            name=name,
            node_count=node_count,
        )
        
        # Wait for operation to complete
        _wait_for_operation(client, project_id, location, operation.name)
        
        result = {
            "status": "resized",
            "cluster_name": cluster_name,
            "node_pool_name": node_pool_name,
            "node_count": node_count,
            "location": location,
        }

        logger.info("gke_node_pool_resized", cluster_name=cluster_name, node_pool_name=node_pool_name, node_count=node_count)
        return result

    except GoogleAPIError as e:
        logger.error("gke_resize_node_pool_failed", error=str(e), cluster_name=cluster_name)
        raise


def _format_cluster(cluster: Any, location: str) -> Dict[str, Any]:
    """Format cluster to dictionary.

    Args:
        cluster: Cluster resource
        location: Location/zone

    Returns:
        Formatted dictionary
    """
    node_pools = []
    if cluster.node_pools:
        for pool in cluster.node_pools:
            node_pools.append({
                "name": pool.name,
                "num_nodes": pool.config.num_nodes,
                "machine_type": pool.config.machine_type,
                "disk_size_gb": pool.config.disk_size_gb,
                "auto_repair": pool.management.auto_repair_enabled,
                "auto_upgrade": pool.management.auto_upgrade_enabled,
            })

    return {
        "name": cluster.name,
        "id": cluster.id,
        "location": location,
        "endpoint": cluster.endpoint,
        "status": cluster.status.name if cluster.status else "UNKNOWN",
        "version": cluster.current_master_version,
        "node_version": cluster.current_node_version,
        "node_pools": node_pools,
        "private_cluster_config": {
            "enable_private_nodes": cluster.private_cluster_config.enable_private_nodes if cluster.private_cluster_config else False,
            "master_ipv4_cidr": cluster.private_cluster_config.master_ipv4_cidr_block if cluster.private_cluster_config else None,
        } if cluster.private_cluster_config else None,
        "network": cluster.network,
        "subnetwork": cluster.subnetwork,
        "labels": dict(cluster.resource_labels) if cluster.resource_labels else {},
    }


def _build_kubeconfig(project_id: str, location: str, cluster_name: str, endpoint: str) -> str:
    """Build kubeconfig for GKE cluster.

    Args:
        project_id: GCP project ID
        location: Location/zone
        cluster_name: Cluster name
        endpoint: Cluster endpoint

    Returns:
        Kubeconfig as YAML string
    """
    # Note: In production, you'd use the generated kubeconfig from the API
    # This is a simplified version
    return f"""apiVersion: v1
clusters:
- cluster:
    certificate-authority-data: 
    server: https://{endpoint}
  name: {cluster_name}
contexts:
- context:
    cluster: {cluster_name}
    user: {cluster_name}
  name: {cluster_name}
current-context: {cluster_name}
kind: Config
preferences: {{}}
users:
- name: {cluster_name}
  user:
    auth-provider:
      config:
        cmd-args: config config-helper --format=json
        cmd-path: gcloud
        expiry-key: '{{{{.credential.token_expiry}}}}'
        token-key: '{{{{.credential.access_token}}}}'
      name: gcp
"""


def _wait_for_operation(client: Any, project_id: str, location: str, operation_name: str) -> None:
    """Wait for a GKE operation to complete.

    Args:
        client: ClusterManagerClient
        project_id: GCP project ID
        location: Location/zone
        operation_name: Operation name
    """
    while True:
        operation = client.get_operation(
            name=f"projects/{project_id}/locations/{location}/operations/{operation_name}"
        )
        if operation.status == container_v1.Operation.Status.DONE:
            if operation.error:
                raise GoogleAPIError(f"Operation failed: {operation.error}")
            break
        import time
        time.sleep(1)
