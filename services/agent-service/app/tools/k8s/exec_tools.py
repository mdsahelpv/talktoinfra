"""
Kubernetes execution tools for running commands in pods.
All operations require approval before execution.
"""

import asyncio
from typing import Any, Dict, List, Optional
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException
from kubernetes.stream import stream

from app.tools.validators import ExecCommandInput, PortForwardInput


class K8sExecClient:
    """Kubernetes client wrapper for exec operations."""

    def __init__(self):
        self._core_api: Optional[client.CoreV1Api] = None
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
        self._initialized = True

    @property
    def core_api(self) -> client.CoreV1Api:
        if not self._core_api:
            raise RuntimeError("K8sExecClient not initialized")
        return self._core_api


# Global client instance
_k8s_exec_client = K8sExecClient()


async def get_k8s_exec_client() -> K8sExecClient:
    """Get initialized Kubernetes exec client."""
    await _k8s_exec_client.initialize()
    return _k8s_exec_client


async def exec_command_in_pod(
    pod_name: str,
    namespace: str,
    command: List[str],
    container: Optional[str] = None,
    timeout: int = 30,
) -> Dict[str, Any]:
    """
    Execute a command in a running container.

    Args:
        pod_name: Name of the pod
        namespace: Kubernetes namespace
        command: Command to execute as a list
        container: Container name (required if pod has multiple containers)
        timeout: Command timeout in seconds

    Returns:
        Dictionary with command output or error information
    """
    try:
        validated = ExecCommandInput(
            pod_name=pod_name,
            namespace=namespace,
            command=command,
            container=container,
            timeout=timeout,
        )

        k8s = await get_k8s_exec_client()

        # Execute command in container
        response = stream(
            k8s.core_api.connect_get_namespaced_pod_exec,
            name=validated.pod_name,
            namespace=validated.namespace,
            command=validated.command,
            container=validated.container,
            stdout=True,
            stderr=True,
            tty=False,
            _preload_content=True,
        )

        return {
            "success": True,
            "pod": validated.pod_name,
            "namespace": validated.namespace,
            "container": validated.container,
            "command": " ".join(validated.command),
            "output": response,
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

    except asyncio.TimeoutError:
        return {
            "success": False,
            "error": f"Command timed out after {timeout} seconds",
            "error_type": "Timeout",
        }

    except Exception as e:
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


async def port_forward(
    pod_name: str,
    namespace: str,
    local_port: int,
    target_port: int,
    container: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Set up a port forward to a pod.

    Note: This creates a local port forward. In production, you'd typically
    use kubectl port-forward or a dedicated sidecar. This function returns
    the configuration needed for port forwarding.

    Args:
        pod_name: Name of the pod
        namespace: Kubernetes namespace
        local_port: Local port to forward to
        target_port: Target port in the pod
        container: Container name (required if pod has multiple containers)

    Returns:
        Dictionary with port forward configuration or error information
    """
    try:
        validated = PortForwardInput(
            pod_name=pod_name,
            namespace=namespace,
            local_port=local_port,
            target_port=target_port,
            container=container,
        )

        k8s = await get_k8s_exec_client()

        # Verify pod exists
        pod = k8s.core_api.read_namespaced_pod(
            name=validated.pod_name,
            namespace=validated.namespace,
        )

        # Check if pod is running
        if pod.status.phase != "Running":
            return {
                "success": False,
                "error": f"Pod is not running (current status: {pod.status.phase})",
                "error_type": "PodNotRunning",
            }

        # Return port forward configuration
        # In a real implementation, you'd use websocket or kubectl port-forward
        return {
            "success": True,
            "message": f"Port forward configuration ready",
            "config": {
                "pod": validated.pod_name,
                "namespace": validated.namespace,
                "container": validated.container,
                "local_port": validated.local_port,
                "target_port": validated.target_port,
                "pod_ip": pod.status.pod_ip,
            },
            "instructions": f"Use 'kubectl port-forward pod/{validated.pod_name} {validated.local_port}:{validated.target_port} -n {validated.namespace}' to establish the connection",
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


async def get_pod_shell(
    pod_name: str,
    namespace: str,
    container: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get an interactive shell in a running container.

    Note: This returns configuration for establishing a shell session.
    Actual shell interaction would require a websocket connection.

    Args:
        pod_name: Name of the pod
        namespace: Kubernetes namespace
        container: Container name (required if pod has multiple containers)

    Returns:
        Dictionary with shell configuration or error information
    """
    try:
        k8s = await get_k8s_exec_client()

        # Verify pod exists and is running
        pod = k8s.core_api.read_namespaced_pod(
            name=pod_name,
            namespace=namespace,
        )

        if pod.status.phase != "Running":
            return {
                "success": False,
                "error": f"Pod is not running (current status: {pod.status.phase})",
                "error_type": "PodNotRunning",
            }

        # Determine shell command based on container image
        shell = "/bin/sh"
        if container:
            # Try to detect shell from container
            pass

        return {
            "success": True,
            "message": "Shell session configuration ready",
            "config": {
                "pod": pod_name,
                "namespace": namespace,
                "container": container,
                "shell": shell,
                "pod_ip": pod.status.pod_ip,
            },
            "instructions": f"Use 'kubectl exec -it {pod_name} -n {namespace} -- {shell}' to open an interactive shell",
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


async def copy_file_to_pod(
    pod_name: str,
    namespace: str,
    source_path: str,
    destination_path: str,
    container: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Copy a file to a pod.

    Note: This returns configuration for file transfer.
    Actual transfer would use kubectl cp or a sidecar.

    Args:
        pod_name: Name of the pod
        namespace: Kubernetes namespace
        source_path: Source file path on local machine
        destination_path: Destination path in the pod
        container: Container name

    Returns:
        Dictionary with copy configuration or error information
    """
    try:
        k8s = await get_k8s_exec_client()

        # Verify pod exists
        pod = k8s.core_api.read_namespaced_pod(
            name=pod_name,
            namespace=namespace,
        )

        return {
            "success": True,
            "message": "File copy configuration ready",
            "config": {
                "pod": pod_name,
                "namespace": namespace,
                "container": container,
                "source_path": source_path,
                "destination_path": destination_path,
            },
            "instructions": f"Use 'kubectl cp {source_path} {pod_name}:{destination_path} -n {namespace}' to copy the file",
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
