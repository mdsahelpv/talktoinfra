"""
Azure Kubernetes Service (AKS) Tools

Provides tools for managing Azure Kubernetes Service clusters.
"""

from typing import Any, Dict, List, Optional
from azure.identity import DefaultAzureCredential
from azure.mgmt.containerservice import ContainerServiceClient
from azure.mgmt.containerservice.models import ManagedCluster, AgentPool
from azure.core.exceptions import AzureError
import structlog


logger = structlog.get_logger()


def get_azure_aks_client(subscription_id: str) -> ContainerServiceClient:
    """Get Azure Container Service Client.

    Args:
        subscription_id: Azure subscription ID

    Returns:
        ContainerServiceClient instance
    """
    credential = DefaultAzureCredential()
    return ContainerServiceClient(credential, subscription_id)


async def list_aks_clusters(
    subscription_id: str,
    resource_group: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List Azure Kubernetes Service clusters.

    Args:
        subscription_id: Azure subscription ID
        resource_group: Optional resource group name to filter by

    Returns:
        List of AKS cluster information dictionaries
    """
    try:
        client = get_azure_aks_client(subscription_id)
        
        if resource_group:
            clusters = client.managed_clusters.list(resource_group_name=resource_group)
        else:
            # List all clusters in subscription
            clusters = client.managed_clusters.list()
        
        result = []
        for cluster in clusters:
            result.append({
                "id": cluster.id,
                "name": cluster.name,
                "resource_group": cluster.id.split("/")[4],
                "location": cluster.location,
                "kubernetes_version": cluster.kubernetes_version,
                "provisioning_state": cluster.provisioning_state,
                "dns_prefix": cluster.dns_prefix,
                "fqdn": cluster.fqdn,
                "node_count": _get_node_count(cluster),
                "node_pool_mode": cluster.mode.value if cluster.mode else "User",
                "sku_tier": cluster.sku.tier.value if cluster.sku and cluster.sku.tier else "Free",
            })

        logger.info("azure_aks_clusters_listed", count=len(result), subscription_id=subscription_id)
        return result

    except AzureError as e:
        logger.error("azure_list_aks_clusters_failed", error=str(e))
        raise


async def get_aks_cluster(
    subscription_id: str,
    resource_group: str,
    cluster_name: str,
) -> Dict[str, Any]:
    """Get Azure Kubernetes Service cluster details.

    Args:
        subscription_id: Azure subscription ID
        resource_group: Resource group name
        cluster_name: Cluster name

    Returns:
        AKS cluster information dictionary
    """
    try:
        client = get_azure_aks_client(subscription_id)
        cluster = client.managed_clusters.get(
            resource_group_name=resource_group,
            resource_name=cluster_name
        )

        result = {
            "id": cluster.id,
            "name": cluster.name,
            "resource_group": resource_group,
            "location": cluster.location,
            "kubernetes_version": cluster.kubernetes_version,
            "provisioning_state": cluster.provisioning_state,
            "dns_prefix": cluster.dns_prefix,
            "fqdn": cluster.fqdn,
            "private_fqdn": cluster.private_fqdn,
            "node_count": _get_node_count(cluster),
            "node_pools": _get_node_pools(cluster),
            "api_server_access_profile": {
                "enable_private_cluster": cluster.api_server_access_profile.enable_private_cluster if cluster.api_server_access_profile else False,
                "authorized_ip_ranges": list(cluster.api_server_access_profile.authorized_ip_ranges) if cluster.api_server_access_profile and cluster.api_server_access_profile.authorized_ip_ranges else [],
            } if cluster.api_server_access_profile else None,
            "identity": {
                "type": cluster.identity.type.value if cluster.identity else None,
                "principal_id": cluster.identity.principal_id if cluster.identity else None,
            } if cluster.identity else None,
            "sku_tier": cluster.sku.tier.value if cluster.sku and cluster.sku.tier else "Free",
        }

        logger.info("azure_aks_cluster_retrieved", cluster_name=cluster_name, resource_group=resource_group)
        return result

    except AzureError as e:
        logger.error("azure_get_aks_cluster_failed", error=str(e), cluster_name=cluster_name)
        raise


async def get_aks_cluster_credentials(
    subscription_id: str,
    resource_group: str,
    cluster_name: str,
) -> Dict[str, Any]:
    """Get Azure Kubernetes Service cluster credentials.

    Args:
        subscription_id: Azure subscription ID
        resource_group: Resource group name
        cluster_name: Cluster name

    Returns:
        Dictionary containing kubeconfig and cluster info
    """
    try:
        client = get_azure_aks_client(subscription_id)
        
        creds = client.managed_clusters.list_cluster_admin_credentials(
            resource_group_name=resource_group,
            resource_name=cluster_name
        )
        
        # Get the kubeconfig
        kubeconfig = None
        if creds.kubeconfigs:
            import base64
            kubeconfig = base64.b64decode(creds.kubeconfigs[0].value).decode("utf-8")

        result = {
            "cluster_name": cluster_name,
            "resource_group": resource_group,
            "kubeconfig": kubeconfig,
        }

        logger.info("azure_aks_cluster_credentials_retrieved", cluster_name=cluster_name, resource_group=resource_group)
        return result

    except AzureError as e:
        logger.error("azure_get_aks_cluster_credentials_failed", error=str(e), cluster_name=cluster_name)
        raise


async def scale_aks_node_pool(
    subscription_id: str,
    resource_group: str,
    cluster_name: str,
    node_pool_name: str,
    node_count: int,
) -> Dict[str, Any]:
    """Scale an AKS node pool.

    Args:
        subscription_id: Azure subscription ID
        resource_group: Resource group name
        cluster_name: Cluster name
        node_pool_name: Node pool name
        node_count: New node count

    Returns:
        Operation result dictionary
    """
    try:
        client = get_azure_aks_client(subscription_id)
        
        # Get current agent pool
        agent_pool = client.agent_pools.get(
            resource_group_name=resource_group,
            resource_name=cluster_name,
            agent_pool_name=node_pool_name
        )
        
        # Update node count
        agent_pool.count = node_count
        
        poller = client.agent_pools.begin_create_or_update(
            resource_group_name=resource_group,
            resource_name=cluster_name,
            agent_pool_name=node_pool_name,
            parameters=agent_pool
        )
        poller.wait()
        
        result = {
            "status": "scaled",
            "cluster_name": cluster_name,
            "node_pool_name": node_pool_name,
            "node_count": node_count,
            "resource_group": resource_group,
        }

        logger.info("azure_aks_node_pool_scaled", cluster_name=cluster_name, node_pool_name=node_pool_name, node_count=node_count)
        return result

    except AzureError as e:
        logger.error("azure_scale_aks_node_pool_failed", error=str(e), cluster_name=cluster_name)
        raise


def _get_node_count(cluster: ManagedCluster) -> int:
    """Get total node count from cluster.

    Args:
        cluster: ManagedCluster instance

    Returns:
        Total node count
    """
    if not cluster.agent_pool_profiles:
        return 0
    return sum(pool.count or 0 for pool in cluster.agent_pool_profiles)


def _get_node_pools(cluster: ManagedCluster) -> List[Dict[str, Any]]:
    """Get node pool information from cluster.

    Args:
        cluster: ManagedCluster instance

    Returns:
        List of node pool dictionaries
    """
    if not cluster.agent_pool_profiles:
        return []
    
    pools = []
    for pool in cluster.agent_pool_profiles:
        pools.append({
            "name": pool.name,
            "count": pool.count,
            "vm_size": pool.vm_size,
            "os_type": pool.os_type.value if pool.os_type else "Linux",
            "os_sku": pool.os_sku.value if pool.os_sku else None,
            "mode": pool.mode.value if pool.mode else "User",
            "availability_zones": list(pool.availability_zones) if pool.availability_zones else [],
            "scale_set_eviction_policy": pool.scale_set_eviction_policy.value if pool.scale_set_eviction_policy else None,
            "scale_set_priority": pool.scale_set_priority.value if pool.scale_set_priority else None,
        })
    
    return pools
