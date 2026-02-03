"""
Kubernetes read-only tools for infrastructure queries.
All operations are read-only and safe for auto-execution.
"""

import asyncio
from typing import Any, Dict, List, Optional
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException

from app.tools.validators import (
    PodQueryInput,
    LogQueryInput,
    DescribeResourceInput,
    validate_k8s_resource_name,
    validate_namespace,
    ValidationResult,
)


class K8sClient:
    """Kubernetes client wrapper with error handling."""

    def __init__(self):
        self._core_api: Optional[client.CoreV1Api] = None
        self._apps_api: Optional[client.AppsV1Api] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the Kubernetes client."""
        if self._initialized:
            return

        try:
            config.load_incluster_config()
        except config.ConfigException:
            try:
                config.load_kube_config()
            except config.ConfigException as e:
                raise RuntimeError(f"Failed to load Kubernetes config: {e}")

        self._core_api = client.CoreV1Api()
        self._apps_api = client.AppsV1Api()
        self._initialized = True

    @property
    def core_api(self) -> client.CoreV1Api:
        if not self._core_api:
            raise RuntimeError("K8sClient not initialized")
        return self._core_api

    @property
    def apps_api(self) -> client.AppsV1Api:
        if not self._apps_api:
            raise RuntimeError("K8sClient not initialized")
        return self._apps_api


# Global client instance
_k8s_client = K8sClient()


async def get_k8s_client() -> K8sClient:
    """Get initialized Kubernetes client."""
    await _k8s_client.initialize()
    return _k8s_client


async def list_pods(
    namespace: Optional[str] = "default", label_selector: Optional[str] = None
) -> Dict[str, Any]:
    """
    List pods in a namespace.

    Args:
        namespace: Kubernetes namespace
        label_selector: Optional label selector filter

    Returns:
        Dictionary with pod list or error information
    """
    try:
        # Validate inputs
        validated = PodQueryInput(namespace=namespace, label_selector=label_selector)

        k8s = await get_k8s_client()

        if validated.namespace:
            response = k8s.core_api.list_namespaced_pod(
                namespace=validated.namespace, label_selector=validated.label_selector
            )
        else:
            response = k8s.core_api.list_pod_for_all_namespaces(
                label_selector=validated.label_selector
            )

        pods = []
        for pod in response.items:
            pods.append(
                {
                    "name": pod.metadata.name,
                    "namespace": pod.metadata.namespace,
                    "status": pod.status.phase,
                    "ip": pod.status.pod_ip,
                    "node": pod.spec.node_name,
                    "created": pod.metadata.creation_timestamp.isoformat()
                    if pod.metadata.creation_timestamp
                    else None,
                    "labels": pod.metadata.labels or {},
                    "containers": [c.name for c in pod.spec.containers],
                }
            )

        return {"success": True, "count": len(pods), "pods": pods}

    except Exception as e:
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


async def get_pod(
    pod_name: str, namespace: Optional[str] = "default"
) -> Dict[str, Any]:
    """
    Get detailed information about a specific pod.

    Args:
        pod_name: Name of the pod
        namespace: Kubernetes namespace

    Returns:
        Dictionary with pod details or error information
    """
    try:
        # Validate inputs
        validated = PodQueryInput(pod_name=pod_name, namespace=namespace)

        k8s = await get_k8s_client()

        pod = k8s.core_api.read_namespaced_pod(
            name=validated.pod_name, namespace=validated.namespace or "default"
        )

        return {
            "success": True,
            "pod": {
                "name": pod.metadata.name,
                "namespace": pod.metadata.namespace,
                "status": pod.status.phase,
                "ip": pod.status.pod_ip,
                "node": pod.spec.node_name,
                "created": pod.metadata.creation_timestamp.isoformat()
                if pod.metadata.creation_timestamp
                else None,
                "labels": pod.metadata.labels or {},
                "annotations": pod.metadata.annotations or {},
                "containers": [
                    {
                        "name": c.name,
                        "image": c.image,
                        "resources": {
                            "requests": c.resources.requests if c.resources else None,
                            "limits": c.resources.limits if c.resources else None,
                        },
                    }
                    for c in pod.spec.containers
                ],
                "volumes": [v.name for v in pod.spec.volumes]
                if pod.spec.volumes
                else [],
                "conditions": [
                    {
                        "type": c.type,
                        "status": c.status,
                        "reason": c.reason,
                        "message": c.message,
                    }
                    for c in pod.status.conditions
                ]
                if pod.status.conditions
                else [],
            },
        }

    except ApiException as e:
        if e.status == 404:
            return {
                "success": False,
                "error": f"Pod '{pod_name}' not found in namespace '{namespace}'",
                "error_type": "NotFound",
            }
        return {
            "success": False,
            "error": f"Kubernetes API error: {e.reason}",
            "error_type": "ApiException",
        }

    except Exception as e:
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


async def get_logs(
    pod_name: str,
    namespace: Optional[str] = "default",
    container: Optional[str] = None,
    tail_lines: Optional[int] = 100,
) -> Dict[str, Any]:
    """
    Get logs from a pod.

    Args:
        pod_name: Name of the pod
        namespace: Kubernetes namespace
        container: Container name (required if pod has multiple containers)
        tail_lines: Number of lines to retrieve from the end (default: 100, max: 10000)

    Returns:
        Dictionary with logs or error information
    """
    try:
        # Validate inputs
        validated = LogQueryInput(
            pod_name=pod_name,
            namespace=namespace,
            container=container,
            tail_lines=tail_lines,
        )

        k8s = await get_k8s_client()

        logs = k8s.core_api.read_namespaced_pod_log(
            name=validated.pod_name,
            namespace=validated.namespace or "default",
            container=validated.container,
            tail_lines=validated.tail_lines,
        )

        return {
            "success": True,
            "pod": validated.pod_name,
            "namespace": validated.namespace or "default",
            "container": validated.container,
            "logs": logs,
            "lines_retrieved": len(logs.split("\n")) if logs else 0,
        }

    except ApiException as e:
        if e.status == 404:
            return {
                "success": False,
                "error": f"Pod '{pod_name}' not found in namespace '{namespace}'",
                "error_type": "NotFound",
            }
        return {
            "success": False,
            "error": f"Kubernetes API error: {e.reason}",
            "error_type": "ApiException",
        }

    except Exception as e:
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


async def describe_resource(
    resource_type: str, resource_name: str, namespace: Optional[str] = "default"
) -> Dict[str, Any]:
    """
    Describe a Kubernetes resource with detailed information.

    Args:
        resource_type: Type of resource (pod, service, deployment, etc.)
        resource_name: Name of the resource
        namespace: Kubernetes namespace

    Returns:
        Dictionary with resource details or error information
    """
    try:
        # Validate inputs
        validated = DescribeResourceInput(
            resource_type=resource_type,
            resource_name=resource_name,
            namespace=namespace,
        )

        k8s = await get_k8s_client()

        resource_type_lower = validated.resource_type.lower()
        result = {"success": True, "resource_type": resource_type_lower}

        # Map resource types to API calls
        if resource_type_lower in ["pod", "pods"]:
            resource = k8s.core_api.read_namespaced_pod(
                name=validated.resource_name, namespace=validated.namespace or "default"
            )
            result["resource"] = _format_pod(resource)

        elif resource_type_lower in ["service", "services", "svc"]:
            resource = k8s.core_api.read_namespaced_service(
                name=validated.resource_name, namespace=validated.namespace or "default"
            )
            result["resource"] = _format_service(resource)

        elif resource_type_lower in ["deployment", "deployments", "deploy"]:
            resource = k8s.apps_api.read_namespaced_deployment(
                name=validated.resource_name, namespace=validated.namespace or "default"
            )
            result["resource"] = _format_deployment(resource)

        elif resource_type_lower in ["configmap", "configmaps", "cm"]:
            resource = k8s.core_api.read_namespaced_config_map(
                name=validated.resource_name, namespace=validated.namespace or "default"
            )
            result["resource"] = _format_configmap(resource)

        elif resource_type_lower in ["secret", "secrets"]:
            resource = k8s.core_api.read_namespaced_secret(
                name=validated.resource_name, namespace=validated.namespace or "default"
            )
            result["resource"] = _format_secret(resource)

        elif resource_type_lower in ["node", "nodes"]:
            resource = k8s.core_api.read_node(name=validated.resource_name)
            result["resource"] = _format_node(resource)

        elif resource_type_lower in ["namespace", "namespaces", "ns"]:
            resource = k8s.core_api.read_namespace(name=validated.resource_name)
            result["resource"] = _format_namespace(resource)

        elif resource_type_lower in ["persistentvolume", "persistentvolumes", "pv"]:
            resource = k8s.core_api.read_persistent_volume(name=validated.resource_name)
            result["resource"] = _format_persistent_volume(resource)

        elif resource_type_lower in [
            "persistentvolumeclaim",
            "persistentvolumeclaims",
            "pvc",
        ]:
            resource = k8s.core_api.read_namespaced_persistent_volume_claim(
                name=validated.resource_name, namespace=validated.namespace or "default"
            )
            result["resource"] = _format_pvc(resource)

        else:
            return {
                "success": False,
                "error": f"Resource type '{resource_type}' is not supported yet",
                "error_type": "UnsupportedResourceType",
            }

        return result

    except ApiException as e:
        if e.status == 404:
            return {
                "success": False,
                "error": f"Resource '{resource_name}' of type '{resource_type}' not found in namespace '{namespace}'",
                "error_type": "NotFound",
            }
        return {
            "success": False,
            "error": f"Kubernetes API error: {e.reason}",
            "error_type": "ApiException",
        }

    except Exception as e:
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


def _format_pod(pod: Any) -> Dict[str, Any]:
    """Format pod resource for output."""
    return {
        "name": pod.metadata.name,
        "namespace": pod.metadata.namespace,
        "status": pod.status.phase,
        "ip": pod.status.pod_ip,
        "node": pod.spec.node_name,
        "created": pod.metadata.creation_timestamp.isoformat()
        if pod.metadata.creation_timestamp
        else None,
        "labels": pod.metadata.labels or {},
        "annotations": pod.metadata.annotations or {},
        "containers": [
            {
                "name": c.name,
                "image": c.image,
                "resources": {
                    "requests": c.resources.requests if c.resources else None,
                    "limits": c.resources.limits if c.resources else None,
                },
            }
            for c in pod.spec.containers
        ],
    }


def _format_service(svc: Any) -> Dict[str, Any]:
    """Format service resource for output."""
    return {
        "name": svc.metadata.name,
        "namespace": svc.metadata.namespace,
        "type": svc.spec.type,
        "cluster_ip": svc.spec.cluster_ip,
        "external_ips": svc.spec.external_ips,
        "ports": [
            {
                "port": p.port,
                "target_port": p.target_port,
                "protocol": p.protocol,
                "name": p.name,
            }
            for p in svc.spec.ports
        ]
        if svc.spec.ports
        else [],
        "selector": svc.spec.selector,
        "created": svc.metadata.creation_timestamp.isoformat()
        if svc.metadata.creation_timestamp
        else None,
    }


def _format_deployment(deploy: Any) -> Dict[str, Any]:
    """Format deployment resource for output."""
    return {
        "name": deploy.metadata.name,
        "namespace": deploy.metadata.namespace,
        "replicas": deploy.spec.replicas,
        "available_replicas": deploy.status.available_replicas,
        "ready_replicas": deploy.status.ready_replicas,
        "strategy": deploy.spec.strategy.type if deploy.spec.strategy else None,
        "selector": deploy.spec.selector.match_labels if deploy.spec.selector else None,
        "created": deploy.metadata.creation_timestamp.isoformat()
        if deploy.metadata.creation_timestamp
        else None,
        "labels": deploy.metadata.labels or {},
    }


def _format_configmap(cm: Any) -> Dict[str, Any]:
    """Format configmap resource for output."""
    return {
        "name": cm.metadata.name,
        "namespace": cm.metadata.namespace,
        "data_keys": list(cm.data.keys()) if cm.data else [],
        "binary_data_keys": list(cm.binary_data.keys()) if cm.binary_data else [],
        "created": cm.metadata.creation_timestamp.isoformat()
        if cm.metadata.creation_timestamp
        else None,
        "labels": cm.metadata.labels or {},
    }


def _format_secret(secret: Any) -> Dict[str, Any]:
    """Format secret resource for output (without revealing values)."""
    return {
        "name": secret.metadata.name,
        "namespace": secret.metadata.namespace,
        "type": secret.type,
        "data_keys": list(secret.data.keys()) if secret.data else [],
        "created": secret.metadata.creation_timestamp.isoformat()
        if secret.metadata.creation_timestamp
        else None,
        "labels": secret.metadata.labels or {},
    }


def _format_node(node: Any) -> Dict[str, Any]:
    """Format node resource for output."""
    return {
        "name": node.metadata.name,
        "status": node.status.phase if node.status else None,
        "addresses": [
            {"type": addr.type, "address": addr.address}
            for addr in node.status.addresses
        ]
        if node.status and node.status.addresses
        else [],
        "capacity": node.status.capacity if node.status else None,
        "allocatable": node.status.allocatable if node.status else None,
        "created": node.metadata.creation_timestamp.isoformat()
        if node.metadata.creation_timestamp
        else None,
        "labels": node.metadata.labels or {},
    }


def _format_namespace(ns: Any) -> Dict[str, Any]:
    """Format namespace resource for output."""
    return {
        "name": ns.metadata.name,
        "status": ns.status.phase if ns.status else None,
        "created": ns.metadata.creation_timestamp.isoformat()
        if ns.metadata.creation_timestamp
        else None,
        "labels": ns.metadata.labels or {},
    }


def _format_persistent_volume(pv: Any) -> Dict[str, Any]:
    """Format persistent volume resource for output."""
    return {
        "name": pv.metadata.name,
        "capacity": pv.spec.capacity if pv.spec else None,
        "access_modes": pv.spec.access_modes if pv.spec else None,
        "status": pv.status.phase if pv.status else None,
        "storage_class": pv.spec.storage_class_name if pv.spec else None,
        "created": pv.metadata.creation_timestamp.isoformat()
        if pv.metadata.creation_timestamp
        else None,
    }


def _format_pvc(pvc: Any) -> Dict[str, Any]:
    """Format persistent volume claim resource for output."""
    return {
        "name": pvc.metadata.name,
        "namespace": pvc.metadata.namespace,
        "status": pvc.status.phase if pvc.status else None,
        "volume_name": pvc.spec.volume_name if pvc.spec else None,
        "access_modes": pvc.spec.access_modes if pvc.spec else None,
        "storage_class": pvc.spec.storage_class_name if pvc.spec else None,
        "resources": pvc.spec.resources.requests
        if pvc.spec and pvc.spec.resources
        else None,
        "created": pvc.metadata.creation_timestamp.isoformat()
        if pvc.metadata.creation_timestamp
        else None,
    }
