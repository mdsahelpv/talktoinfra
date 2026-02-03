"""Kubernetes Client module.

Fetches resources from Kubernetes API with real cluster connections.
Uses kubernetes client library with proper authentication and retry logic.
"""

import asyncio
from typing import Any, Dict, List, Optional

from kubernetes import client, config
from kubernetes.client.rest import ApiException
import structlog
import tenacity
from tenacity import retry, stop_after_attempt, wait_exponential

from config import get_settings

logger = structlog.get_logger()


class KubernetesClient:
    """Client for fetching Kubernetes resources from real clusters."""

    def __init__(self) -> None:
        """Initialize the Kubernetes client with proper configuration."""
        self._core_v1: Optional[client.CoreV1Api] = None
        self._apps_v1: Optional[client.AppsV1Api] = None
        self._initialized = False
        self._settings = get_settings()

    def _initialize(self) -> None:
        """Initialize Kubernetes client configuration.

        Attempts to load configuration in order:
        1. Load from kubeconfig file (for external access)
        2. Fall back to in-cluster config (when running inside a pod)

        Raises:
            RuntimeError: If unable to configure Kubernetes client.
        """
        if self._initialized:
            return

        try:
            config.load_kube_config()
            logger.info("kubernetes_config_loaded", source="kubeconfig")
        except config.ConfigException:
            try:
                config.load_incluster_config()
                logger.info("kubernetes_config_loaded", source="incluster")
            except config.ConfigException as e:
                logger.error(
                    "kubernetes_config_failed",
                    error=str(e),
                    error_type="ConfigException",
                )
                raise RuntimeError(f"Unable to configure Kubernetes client: {e}") from e

        self._core_v1 = client.CoreV1Api()
        self._apps_v1 = client.AppsV1Api()
        self._initialized = True

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=tenacity.retry_if_exception_type(ApiException),
        before_sleep=lambda retry_state: logger.warning(
            "k8s_retry_attempt",
            attempt=retry_state.attempt_number,
            error=str(retry_state.outcome.exception()) if retry_state.outcome else None,
        ),
    )
    async def list_pods(self, namespace: str) -> List[Dict[str, Any]]:
        """List all pods in the specified namespace.

        Args:
            namespace: The Kubernetes namespace to query.

        Returns:
            List of pod dictionaries containing metadata and status.

        Raises:
            HTTPException: If authentication fails or API call errors.
        """
        self._initialize()
        assert self._core_v1 is not None, "CoreV1Api not initialized"

        logger.info("k8s_list_pods", namespace=namespace)

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._core_v1.list_namespaced_pod,
                namespace,
            )

            pods = []
            for pod in result.items:
                pod_dict = {
                    "name": pod.metadata.name,
                    "namespace": pod.metadata.namespace,
                    "labels": pod.metadata.labels or {},
                    "annotations": pod.metadata.annotations or {},
                    "status": {
                        "phase": pod.status.phase,
                        "conditions": [
                            {
                                "type": c.type,
                                "status": c.status,
                                "reason": c.reason,
                            }
                            for c in (pod.status.conditions or [])
                        ],
                        "container_statuses": [
                            {
                                "name": cs.name,
                                "ready": cs.ready,
                                "restart_count": cs.restart_count,
                                "image": cs.image,
                            }
                            for cs in (pod.status.container_statuses or [])
                        ],
                    },
                    "spec": {
                        "node_name": pod.spec.node_name,
                        "containers": [
                            {
                                "name": c.name,
                                "image": c.image,
                                "resources": (
                                    {
                                        "requests": c.resources.requests,
                                        "limits": c.resources.limits,
                                    }
                                    if c.resources
                                    else None
                                ),
                            }
                            for c in (pod.spec.containers or [])
                        ],
                    },
                    "created_at": (
                        pod.metadata.creation_timestamp.isoformat()
                        if pod.metadata.creation_timestamp
                        else None
                    ),
                }
                pods.append(pod_dict)

            logger.info(
                "k8s_list_pods_completed",
                namespace=namespace,
                count=len(pods),
            )
            return pods

        except ApiException as e:
            logger.error(
                "k8s_list_pods_error",
                namespace=namespace,
                status=e.status,
                reason=e.reason,
                error=str(e),
            )
            raise self._handle_api_exception(e, "list_pods", namespace)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=tenacity.retry_if_exception_type(ApiException),
        before_sleep=lambda retry_state: logger.warning(
            "k8s_retry_attempt",
            attempt=retry_state.attempt_number,
            error=str(retry_state.outcome.exception()) if retry_state.outcome else None,
        ),
    )
    async def list_deployments(self, namespace: str) -> List[Dict[str, Any]]:
        """List all deployments in the specified namespace.

        Args:
            namespace: The Kubernetes namespace to query.

        Returns:
            List of deployment dictionaries containing metadata and status.

        Raises:
            HTTPException: If authentication fails or API call errors.
        """
        self._initialize()
        assert self._apps_v1 is not None, "AppsV1Api not initialized"

        logger.info("k8s_list_deployments", namespace=namespace)

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._apps_v1.list_namespaced_deployment,
                namespace,
            )

            deployments = []
            for deployment in result.items:
                deployment_dict = {
                    "name": deployment.metadata.name,
                    "namespace": deployment.metadata.namespace,
                    "labels": deployment.metadata.labels or {},
                    "annotations": deployment.metadata.annotations or {},
                    "spec": {
                        "replicas": deployment.spec.replicas,
                        "selector": (
                            deployment.spec.selector.match_labels
                            if deployment.spec.selector
                            else {}
                        ),
                        "strategy": (
                            deployment.spec.strategy.type
                            if deployment.spec.strategy
                            else None
                        ),
                    },
                    "status": {
                        "replicas": deployment.status.replicas,
                        "ready_replicas": deployment.status.ready_replicas or 0,
                        "available_replicas": deployment.status.available_replicas or 0,
                        "updated_replicas": deployment.status.updated_replicas or 0,
                    },
                    "created_at": (
                        deployment.metadata.creation_timestamp.isoformat()
                        if deployment.metadata.creation_timestamp
                        else None
                    ),
                }
                deployments.append(deployment_dict)

            logger.info(
                "k8s_list_deployments_completed",
                namespace=namespace,
                count=len(deployments),
            )
            return deployments

        except ApiException as e:
            logger.error(
                "k8s_list_deployments_error",
                namespace=namespace,
                status=e.status,
                reason=e.reason,
                error=str(e),
            )
            raise self._handle_api_exception(e, "list_deployments", namespace)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=tenacity.retry_if_exception_type(ApiException),
        before_sleep=lambda retry_state: logger.warning(
            "k8s_retry_attempt",
            attempt=retry_state.attempt_number,
            error=str(retry_state.outcome.exception()) if retry_state.outcome else None,
        ),
    )
    async def get_logs(
        self,
        pod_name: str,
        namespace: str,
        container: Optional[str] = None,
        tail_lines: Optional[int] = None,
    ) -> str:
        """Get logs from a specific pod.

        Args:
            pod_name: Name of the pod to fetch logs from.
            namespace: The Kubernetes namespace containing the pod.
            container: Optional container name (for multi-container pods).
            tail_lines: Optional number of lines to fetch from end of logs.

        Returns:
            String containing the pod logs.

        Raises:
            HTTPException: If pod not found or logs unavailable.
        """
        self._initialize()
        assert self._core_v1 is not None, "CoreV1Api not initialized"

        logger.info(
            "k8s_get_logs",
            pod_name=pod_name,
            namespace=namespace,
            container=container,
            tail_lines=tail_lines,
        )

        try:
            loop = asyncio.get_event_loop()

            def _read_logs():
                # type: () -> str
                assert self._core_v1 is not None
                return self._core_v1.read_namespaced_pod_log(
                    name=pod_name,
                    namespace=namespace,
                    container=container,
                    tail_lines=tail_lines,
                )

            result = await loop.run_in_executor(None, _read_logs)

            logger.info(
                "k8s_get_logs_completed",
                pod_name=pod_name,
                namespace=namespace,
                log_length=len(result) if result else 0,
            )
            return result or ""

        except ApiException as e:
            logger.error(
                "k8s_get_logs_error",
                pod_name=pod_name,
                namespace=namespace,
                status=e.status,
                reason=e.reason,
                error=str(e),
            )
            raise self._handle_api_exception(e, "get_logs", namespace, pod_name)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=tenacity.retry_if_exception_type(ApiException),
        before_sleep=lambda retry_state: logger.warning(
            "k8s_retry_attempt",
            attempt=retry_state.attempt_number,
            error=str(retry_state.outcome.exception()) if retry_state.outcome else None,
        ),
    )
    async def get_namespaces(self) -> List[str]:
        """Get list of all namespaces in the cluster.

        Returns:
            List of namespace names.

        Raises:
            HTTPException: If unable to list namespaces.
        """
        self._initialize()
        assert self._core_v1 is not None, "CoreV1Api not initialized"

        logger.info("k8s_list_namespaces")

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._core_v1.list_namespace,
            )

            namespaces = [ns.metadata.name for ns in result.items]

            logger.info(
                "k8s_list_namespaces_completed",
                count=len(namespaces),
            )
            return namespaces

        except ApiException as e:
            logger.error(
                "k8s_list_namespaces_error",
                status=e.status,
                reason=e.reason,
                error=str(e),
            )
            raise self._handle_api_exception(e, "get_namespaces", "_all")

    async def get_resources(
        self,
        namespace: str,
        resource_type: str,
    ) -> List[Dict[str, Any]]:
        """Get resources from Kubernetes.

        Routes to appropriate list method based on resource_type.

        Args:
            namespace: The Kubernetes namespace to query.
            resource_type: Type of resource (pod, deployment, service).

        Returns:
            List of resource dictionaries.

        Raises:
            ValueError: If resource_type is not supported.
            HTTPException: If API call fails.
        """
        logger.info(
            "fetching_k8s_resources",
            namespace=namespace,
            resource_type=resource_type,
        )

        if resource_type == "pod":
            return await self.list_pods(namespace)
        elif resource_type == "deployment":
            return await self.list_deployments(namespace)
        elif resource_type == "service":
            return await self.list_services(namespace)
        else:
            logger.error(
                "unsupported_resource_type",
                resource_type=resource_type,
            )
            raise ValueError(f"Unsupported resource type: {resource_type}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=tenacity.retry_if_exception_type(ApiException),
        before_sleep=lambda retry_state: logger.warning(
            "k8s_retry_attempt",
            attempt=retry_state.attempt_number,
            error=str(retry_state.outcome.exception()) if retry_state.outcome else None,
        ),
    )
    async def list_services(self, namespace: str) -> List[Dict[str, Any]]:
        """List all services in the specified namespace.

        Args:
            namespace: The Kubernetes namespace to query.

        Returns:
            List of service dictionaries containing metadata and spec.

        Raises:
            HTTPException: If authentication fails or API call errors.
        """
        self._initialize()
        assert self._core_v1 is not None, "CoreV1Api not initialized"

        logger.info("k8s_list_services", namespace=namespace)

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._core_v1.list_namespaced_service,
                namespace,
            )

            services = []
            for service in result.items:
                service_dict = {
                    "name": service.metadata.name,
                    "namespace": service.metadata.namespace,
                    "labels": service.metadata.labels or {},
                    "annotations": service.metadata.annotations or {},
                    "spec": {
                        "type": service.spec.type,
                        "cluster_ip": service.spec.cluster_ip,
                        "ports": [
                            {
                                "name": p.name,
                                "port": p.port,
                                "target_port": p.target_port,
                                "protocol": p.protocol,
                            }
                            for p in (service.spec.ports or [])
                        ],
                        "selector": service.spec.selector or {},
                    },
                    "created_at": (
                        service.metadata.creation_timestamp.isoformat()
                        if service.metadata.creation_timestamp
                        else None
                    ),
                }
                services.append(service_dict)

            logger.info(
                "k8s_list_services_completed",
                namespace=namespace,
                count=len(services),
            )
            return services

        except ApiException as e:
            logger.error(
                "k8s_list_services_error",
                namespace=namespace,
                status=e.status,
                reason=e.reason,
                error=str(e),
            )
            raise self._handle_api_exception(e, "list_services", namespace)

    def _handle_api_exception(
        self,
        e: ApiException,
        operation: str,
        namespace: str,
        resource_name: Optional[str] = None,
    ) -> Exception:
        """Convert Kubernetes API exceptions to appropriate HTTP exceptions.

        Args:
            e: The ApiException from Kubernetes client.
            operation: The operation being performed.
            namespace: The namespace being accessed.
            resource_name: Optional resource name.

        Returns:
            HTTPException with appropriate status and detail.
        """
        from fastapi import HTTPException

        status_code = e.status
        detail = f"Kubernetes API error: {e.reason}"

        if status_code == 401:
            detail = "Authentication failed. Please check your Kubernetes credentials."
        elif status_code == 403:
            detail = f"Permission denied for {operation} in namespace {namespace}."
        elif status_code == 404:
            resource_str = f" {resource_name}" if resource_name else ""
            detail = f"Resource{resource_str} not found in namespace {namespace}."
        elif status_code == 503:
            detail = (
                "Kubernetes API server unavailable. Please check cluster connectivity."
            )
        elif status_code in [408, 504]:
            detail = "Request timeout while connecting to Kubernetes API."
        elif status_code == 0:
            detail = (
                "Unable to connect to Kubernetes cluster. Please verify connectivity."
            )
            status_code = 503

        logger.error(
            "k8s_api_exception_handled",
            operation=operation,
            namespace=namespace,
            status=e.status,
            reason=e.reason,
            detail=detail,
        )

        return HTTPException(status_code=status_code or 500, detail=detail)


async def get_kubernetes_client() -> KubernetesClient:
    """Factory function to create a KubernetesClient instance.

    Returns:
        Configured KubernetesClient instance.
    """
    return KubernetesClient()
