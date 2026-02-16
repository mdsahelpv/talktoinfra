"""
Google Cloud Platform Tools for TalkAI Platform

Provides tools for managing GCP resources including GCE, GKE, and Cloud Storage.
"""

from .gce_tools import (
    list_gce_instances,
    get_gce_instance,
    start_gce_instance,
    stop_gce_instance,
    reset_gce_instance,
    create_gce_instance,
    delete_gce_instance,
)
from .gke_tools import (
    list_gke_clusters,
    get_gke_cluster,
    get_gke_cluster_credentials,
    resize_gke_node_pool,
)
from .storage_tools import (
    list_buckets,
    list_objects,
    upload_object,
    download_object,
    delete_object,
)

__all__ = [
    # GCE tools
    "list_gce_instances",
    "get_gce_instance",
    "start_gce_instance",
    "stop_gce_instance",
    "reset_gce_instance",
    "create_gce_instance",
    "delete_gce_instance",
    # GKE tools
    "list_gke_clusters",
    "get_gke_cluster",
    "get_gke_cluster_credentials",
    "resize_gke_node_pool",
    # Storage tools
    "list_buckets",
    "list_objects",
    "upload_object",
    "download_object",
    "delete_object",
]
