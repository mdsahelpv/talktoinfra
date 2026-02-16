"""
Kubernetes write tools for infrastructure modifications.
All operations require approval before execution.
"""

from typing import Any, Dict, Optional
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException

from app.tools.validators import (
    ScaleDeploymentInput,
    RestartPodInput,
    DeleteResourceInput,
)


class K8sWriteClient:
    """Kubernetes client wrapper for write operations."""

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
            raise RuntimeError("K8sWriteClient not initialized")
        return self._core_api

    @property
    def apps_api(self) -> client.AppsV1Api:
        if not self._apps_api:
            raise RuntimeError("K8sWriteClient not initialized")
        return self._apps_api


# Global client instance
_k8s_write_client = K8sWriteClient()


async def get_k8s_write_client() -> K8sWriteClient:
    """Get initialized Kubernetes write client."""
    await _k8s_write_client.initialize()
    return _k8s_write_client


async def scale_deployment(
    deployment_name: str,
    namespace: str,
    replicas: int,
) -> Dict[str, Any]:
    """
    Scale a Kubernetes deployment to the specified number of replicas.

    Args:
        deployment_name: Name of the deployment
        namespace: Kubernetes namespace
        replicas: Target number of replicas

    Returns:
        Dictionary with operation result or error information
    """
    try:
        validated = ScaleDeploymentInput(
            deployment_name=deployment_name,
            namespace=namespace,
            replicas=replicas,
        )

        k8s = await get_k8s_write_client()

        # Get current deployment to preserve other settings
        deployment = k8s.apps_api.read_namespaced_deployment(
            name=validated.deployment_name,
            namespace=validated.namespace,
        )

        # Update replica count
        deployment.spec.replicas = validated.replicas

        # Apply the update
        updated = k8s.apps_api.patch_namespaced_deployment(
            name=validated.deployment_name,
            namespace=validated.namespace,
            body=deployment,
        )

        return {
            "success": True,
            "message": f"Deployment '{validated.deployment_name}' scaled to {validated.replicas} replicas",
            "deployment": {
                "name": updated.metadata.name,
                "namespace": updated.metadata.namespace,
                "replicas": updated.spec.replicas,
                "ready_replicas": updated.status.ready_replicas,
                "available_replicas": updated.status.available_replicas,
            },
        }

    except ApiException as e:
        if e.status == 404:
            return {
                "success": False,
                "error": f"Deployment '{deployment_name}' not found in namespace '{namespace}'",
                "error_type": "NotFound",
            }
        return {
            "success": False,
            "error": f"Kubernetes API error: {e.reason}",
            "error_type": "ApiException",
        }

    except Exception as e:
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


async def restart_pod(
    pod_name: str,
    namespace: str,
) -> Dict[str, Any]:
    """
    Restart a Kubernetes pod by deleting it (Deployment will recreate it).

    Args:
        pod_name: Name of the pod
        namespace: Kubernetes namespace

    Returns:
        Dictionary with operation result or error information
    """
    try:
        validated = RestartPodInput(pod_name=pod_name, namespace=namespace)

        k8s = await get_k8s_write_client()

        # Delete the pod - if it's managed by a Deployment, it will be recreated
        k8s.core_api.delete_namespaced_pod(
            name=validated.pod_name,
            namespace=validated.namespace,
            body=client.V1DeleteOptions(
                grace_period_seconds=5,
                propagation_policy="Foreground",
            ),
        )

        return {
            "success": True,
            "message": f"Pod '{validated.pod_name}' deleted successfully. A new pod will be created by the controller.",
            "pod": {
                "name": validated.pod_name,
                "namespace": validated.namespace,
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


async def delete_resource(
    resource_type: str,
    resource_name: str,
    namespace: str,
) -> Dict[str, Any]:
    """
    Delete a Kubernetes resource.

    Args:
        resource_type: Type of resource (pod, service, deployment, etc.)
        resource_name: Name of the resource
        namespace: Kubernetes namespace

    Returns:
        Dictionary with operation result or error information
    """
    try:
        validated = DeleteResourceInput(
            resource_type=resource_type,
            resource_name=resource_name,
            namespace=namespace,
        )

        k8s = await get_k8s_write_client()

        resource_type_lower = validated.resource_type.lower()
        result = {
            "success": True,
            "message": f"Resource '{validated.resource_name}' of type '{resource_type_lower}' deleted",
            "resource": {
                "type": resource_type_lower,
                "name": validated.resource_name,
                "namespace": validated.namespace,
            },
        }

        if resource_type_lower in ["pod", "pods"]:
            k8s.core_api.delete_namespaced_pod(
                name=validated.resource_name,
                namespace=validated.namespace,
                body=client.V1DeleteOptions(
                    grace_period_seconds=5,
                    propagation_policy="Foreground",
                ),
            )

        elif resource_type_lower in ["service", "services", "svc"]:
            k8s.core_api.delete_namespaced_service(
                name=validated.resource_name,
                namespace=validated.namespace,
                body=client.V1DeleteOptions(),
            )

        elif resource_type_lower in ["deployment", "deployments", "deploy"]:
            k8s.apps_api.delete_namespaced_deployment(
                name=validated.resource_name,
                namespace=validated.namespace,
                body=client.V1DeleteOptions(
                    grace_period_seconds=5,
                    propagation_policy="Foreground",
                ),
            )

        elif resource_type_lower in ["configmap", "configmaps", "cm"]:
            k8s.core_api.delete_namespaced_config_map(
                name=validated.resource_name,
                namespace=validated.namespace,
                body=client.V1DeleteOptions(),
            )

        elif resource_type_lower in ["secret", "secrets"]:
            k8s.core_api.delete_namespaced_secret(
                name=validated.resource_name,
                namespace=validated.namespace,
                body=client.V1DeleteOptions(),
            )

        elif resource_type_lower in ["job", "jobs"]:
            k8s.batch_api.delete_namespaced_job(
                name=validated.resource_name,
                namespace=validated.namespace,
                body=client.V1DeleteOptions(
                    grace_period_seconds=5,
                    propagation_policy="Foreground",
                ),
            )

        elif resource_type_lower in ["pvc", "persistentvolumeclaim", "persistentvolumeclaims"]:
            k8s.core_api.delete_namespaced_persistent_volume_claim(
                name=validated.resource_name,
                namespace=validated.namespace,
                body=client.V1DeleteOptions(),
            )

        else:
            return {
                "success": False,
                "error": f"Resource type '{resource_type}' is not supported for deletion",
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


async def create_resource(
    resource_type: str,
    manifest: Dict[str, Any],
    namespace: str = "default",
) -> Dict[str, Any]:
    """
    Create a Kubernetes resource from a manifest.

    Args:
        resource_type: Type of resource to create
        manifest: Kubernetes manifest (YAML dict)
        namespace: Kubernetes namespace

    Returns:
        Dictionary with operation result or error information
    """
    try:
        k8s = await get_k8s_write_client()

        resource_type_lower = resource_type.lower()
        result = {
            "success": True,
            "message": f"Resource created successfully",
            "resource": manifest.get("metadata", {}),
        }

        if resource_type_lower in ["pod", "pods"]:
            pod = client.V1Pod(**manifest)
            created = k8s.core_api.create_namespaced_pod(namespace=namespace, body=pod)
            result["resource"] = {
                "name": created.metadata.name,
                "namespace": created.metadata.namespace,
            }

        elif resource_type_lower in ["service", "services", "svc"]:
            svc = client.V1Service(**manifest)
            created = k8s.core_api.create_namespaced_service(namespace=namespace, body=svc)
            result["resource"] = {
                "name": created.metadata.name,
                "namespace": created.metadata.namespace,
            }

        elif resource_type_lower in ["deployment", "deployments", "deploy"]:
            deploy = client.V1Deployment(**manifest)
            created = k8s.apps_api.create_namespaced_deployment(namespace=namespace, body=deploy)
            result["resource"] = {
                "name": created.metadata.name,
                "namespace": created.metadata.namespace,
            }

        elif resource_type_lower in ["configmap", "configmaps", "cm"]:
            cm = client.V1ConfigMap(**manifest)
            created = k8s.core_api.create_namespaced_config_map(namespace=namespace, body=cm)
            result["resource"] = {
                "name": created.metadata.name,
                "namespace": created.metadata.namespace,
            }

        else:
            return {
                "success": False,
                "error": f"Resource type '{resource_type}' is not supported for creation",
                "error_type": "UnsupportedResourceType",
            }

        return result

    except ApiException as e:
        return {
            "success": False,
            "error": f"Kubernetes API error: {e.reason}",
            "error_type": "ApiException",
        }

    except Exception as e:
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


async def patch_resource(
    resource_type: str,
    resource_name: str,
    patch: Dict[str, Any],
    namespace: str = "default",
) -> Dict[str, Any]:
    """
    Patch a Kubernetes resource.

    Args:
        resource_type: Type of resource to patch
        resource_name: Name of the resource
        patch: Patch specification
        namespace: Kubernetes namespace

    Returns:
        Dictionary with operation result or error information
    """
    try:
        k8s = await get_k8s_write_client()

        resource_type_lower = resource_type.lower()
        result = {
            "success": True,
            "message": f"Resource patched successfully",
            "resource": {
                "type": resource_type_lower,
                "name": resource_name,
                "namespace": namespace,
            },
        }

        if resource_type_lower in ["deployment", "deployments", "deploy"]:
            from kubernetes.client import V1Deployment
            deploy = V1Deployment(**patch)
            updated = k8s.apps_api.patch_namespaced_deployment(
                name=resource_name,
                namespace=namespace,
                body=deploy,
            )
            result["resource"]["replicas"] = updated.spec.replicas

        elif resource_type_lower in ["configmap", "configmaps", "cm"]:
            from kubernetes.client import V1ConfigMap
            cm = V1ConfigMap(**patch)
            updated = k8s.core_api.patch_namespaced_config_map(
                name=resource_name,
                namespace=namespace,
                body=cm,
            )
            result["resource"]["data_keys"] = list(updated.data.keys()) if updated.data else []

        else:
            return {
                "success": False,
                "error": f"Resource type '{resource_type}' is not supported for patching",
                "error_type": "UnsupportedResourceType",
            }

        return result

    except ApiException as e:
        return {
            "success": False,
            "error": f"Kubernetes API error: {e.reason}",
            "error_type": "ApiException",
        }

    except Exception as e:
        return {"success": False, "error": str(e), "error_type": type(e).__name__}
