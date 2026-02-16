"""
Kubernetes tools package.
"""

# Read tools
from app.tools.k8s.read_tools import (
    list_pods,
    get_pod,
    get_logs,
    describe_resource,
    K8sClient,
    get_k8s_client,
)

# Write tools
from app.tools.k8s.write_tools import (
    scale_deployment,
    restart_pod,
    delete_resource,
    create_resource,
    patch_resource,
    K8sWriteClient,
    get_k8s_write_client,
)

# Exec tools
from app.tools.k8s.exec_tools import (
    exec_command_in_pod,
    port_forward,
    get_pod_shell,
    copy_file_to_pod,
    K8sExecClient,
    get_k8s_exec_client,
)

# Multi-cluster support
from app.tools.k8s.multi_cluster import (
    MultiClusterClient,
    ClusterConfig,
    ClusterInfo,
    ClusterStatus,
    get_multi_cluster_client,
    initialize_multi_cluster,
)

__all__ = [
    # Read tools
    "list_pods",
    "get_pod",
    "get_logs",
    "describe_resource",
    "K8sClient",
    "get_k8s_client",
    # Write tools
    "scale_deployment",
    "restart_pod",
    "delete_resource",
    "create_resource",
    "patch_resource",
    "K8sWriteClient",
    "get_k8s_write_client",
    # Exec tools
    "exec_command_in_pod",
    "port_forward",
    "get_pod_shell",
    "copy_file_to_pod",
    "K8sExecClient",
    "get_k8s_exec_client",
    # Multi-cluster
    "MultiClusterClient",
    "ClusterConfig",
    "ClusterInfo",
    "ClusterStatus",
    "get_multi_cluster_client",
    "initialize_multi_cluster",
]
