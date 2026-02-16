"""
Azure Cloud Tools for TalkAI Platform

Provides tools for managing Azure resources including VMs, AKS, and storage.
"""

from .vm_tools import (
    list_azure_vms,
    get_azure_vm,
    start_azure_vm,
    stop_azure_vm,
    restart_azure_vm,
    create_azure_vm,
    delete_azure_vm,
)
from .aks_tools import (
    list_aks_clusters,
    get_aks_cluster,
    get_aks_cluster_credentials,
    scale_aks_node_pool,
)
from .storage_tools import (
    list_storage_accounts,
    list_storage_containers,
    list_blobs,
    upload_blob,
    download_blob,
    delete_blob,
)

__all__ = [
    # VM tools
    "list_azure_vms",
    "get_azure_vm",
    "start_azure_vm",
    "stop_azure_vm",
    "restart_azure_vm",
    "create_azure_vm",
    "delete_azure_vm",
    # AKS tools
    "list_aks_clusters",
    "get_aks_cluster",
    "get_aks_cluster_credentials",
    "scale_aks_node_pool",
    # Storage tools
    "list_storage_accounts",
    "list_storage_containers",
    "list_blobs",
    "upload_blob",
    "download_blob",
    "delete_blob",
]
