"""Onboarding Service Client.

Client library for communicating with the Onboarding Service (Port 8011).
Provides methods for fetching clusters, credentials, and cloud accounts.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

import httpx
import structlog

logger = structlog.get_logger()


class OnboardingClient:
    """Client for the Onboarding Service."""

    def __init__(
        self,
        base_url: str = "http://localhost:8011",
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        """Initialize the Onboarding Service client.

        Args:
            base_url: Base URL of the Onboarding Service
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url
        self.api_key = api_key
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            headers: Dict[str, str] = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers=headers,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "OnboardingClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def health_check(self) -> bool:
        """Check if Onboarding Service is healthy.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception as e:
            logger.error("onboarding_health_check_failed", error=str(e))
            return False

    # ============ Cluster Operations ============

    async def list_clusters(
        self,
        status_filter: Optional[str] = None,
        provider: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List registered clusters.

        Args:
            status_filter: Filter by cluster status
            provider: Filter by provider (kubernetes, aws, azure, gcp)
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of cluster information dictionaries
        """
        try:
            client = await self._get_client()
            params: Dict[str, Any] = {"limit": limit, "offset": offset}
            if status_filter:
                params["status_filter"] = status_filter
            if provider:
                params["provider"] = provider

            response = await client.get(
                f"{self.base_url}/api/v1/clusters",
                params=params,
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(
                "list_clusters_failed",
                status_code=e.response.status_code,
                error=str(e),
            )
            return []
        except Exception as e:
            logger.error("list_clusters_error", error=str(e))
            return []

    async def get_cluster(self, cluster_id: str) -> Optional[Dict[str, Any]]:
        """Get cluster details by ID.

        Args:
            cluster_id: Cluster UUID

        Returns:
            Cluster information dictionary or None if not found
        """
        try:
            client = await self._get_client()
            response = await client.get(
                f"{self.base_url}/api/v1/clusters/{cluster_id}",
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(
                "get_cluster_failed",
                cluster_id=cluster_id,
                status_code=e.response.status_code,
            )
            return None
        except Exception as e:
            logger.error("get_cluster_error",
                         cluster_id=cluster_id, error=str(e))
            return None

    async def get_cluster_credentials(
        self,
        cluster_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get credentials for a cluster.

        Args:
            cluster_id: Cluster UUID

        Returns:
            Dictionary containing kubeconfig or credentials, or None if not found
        """
        try:
            client = await self._get_client()
            response = await client.get(
                f"{self.base_url}/api/v1/credentials/{cluster_id}",
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(
                "get_credentials_failed",
                cluster_id=cluster_id,
                status_code=e.response.status_code,
            )
            return None
        except Exception as e:
            logger.error(
                "get_credentials_error",
                cluster_id=cluster_id,
                error=str(e),
            )
            return None

    async def test_cluster_connection(self, cluster_id: str) -> Dict[str, Any]:
        """Test cluster connection.

        Args:
            cluster_id: Cluster UUID

        Returns:
            Connection test result dictionary
        """
        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/api/v1/clusters/{cluster_id}/test-connection",
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error(
                "test_connection_failed",
                cluster_id=cluster_id,
                error=str(e),
            )
            return {
                "success": False,
                "message": str(e),
                "error_code": "CONNECTION_FAILED",
            }

    async def register_cluster(
        self,
        name: str,
        kubeconfig: Optional[str] = None,
        kubeconfig_file: Optional[str] = None,
        api_endpoint: Optional[str] = None,
        token: Optional[str] = None,
        certificate_authority: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None,
        namespace_selector: Optional[Dict[str, List[str]]] = None,
    ) -> Dict[str, Any]:
        """Register a new cluster.

        Args:
            name: Human-readable cluster name
            kubeconfig: Base64-encoded kubeconfig content
            kubeconfig_file: Raw kubeconfig file content (YAML)
            api_endpoint: Kubernetes API server endpoint
            token: Service account token
            certificate_authority: CA certificate (base64)
            labels: Cluster labels/tags
            namespace_selector: Namespaces to monitor

        Returns:
            Registered cluster information
        """
        try:
            client = await self._get_client()
            payload: Dict[str, Any] = {"name": name}
            if kubeconfig:
                payload["kubeconfig"] = kubeconfig
            if kubeconfig_file:
                payload["kubeconfig_file"] = kubeconfig_file
            if api_endpoint:
                payload["api_endpoint"] = api_endpoint
            if token:
                payload["token"] = token
            if certificate_authority:
                payload["certificate_authority"] = certificate_authority
            if labels:
                payload["labels"] = labels
            if namespace_selector:
                payload["namespace_selector"] = namespace_selector

            response = await client.post(
                f"{self.base_url}/api/v1/clusters/register",
                json=payload,
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error("register_cluster_failed", name=name, error=str(e))
            return {"error": str(e)}

    async def delete_cluster(self, cluster_id: str) -> bool:
        """Delete a cluster.

        Args:
            cluster_id: Cluster UUID

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            client = await self._get_client()
            response = await client.delete(
                f"{self.base_url}/api/v1/clusters/{cluster_id}",
            )
            response.raise_for_status()
            return True

        except Exception as e:
            logger.error("delete_cluster_failed",
                         cluster_id=cluster_id, error=str(e))
            return False

    # ============ Cloud Account Operations ============

    async def list_cloud_accounts(
        self,
        provider: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List registered cloud accounts.

        Args:
            provider: Filter by provider (aws, azure, gcp)
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of cloud account information dictionaries
        """
        try:
            client = await self._get_client()
            params: Dict[str, Any] = {"limit": limit, "offset": offset}
            if provider:
                params["provider"] = provider

            response = await client.get(
                f"{self.base_url}/api/v1/cloud",
                params=params,
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error("list_cloud_accounts_error", error=str(e))
            return []

    async def register_aws_account(
        self,
        name: str,
        role_arn: Optional[str] = None,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        regions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Register an AWS account.

        Args:
            name: Human-readable account name
            role_arn: IAM Role ARN (for cross-account access)
            access_key_id: Access key ID
            secret_access_key: Secret access key
            regions: AWS regions to scan

        Returns:
            Registered account information
        """
        try:
            client = await self._get_client()
            payload: Dict[str, Any] = {"name": name}
            if role_arn:
                payload["role_arn"] = role_arn
            if access_key_id:
                payload["access_key_id"] = access_key_id
            if secret_access_key:
                payload["secret_access_key"] = secret_access_key
            if regions:
                payload["regions"] = regions

            response = await client.post(
                f"{self.base_url}/api/v1/cloud/aws/register",
                json=payload,
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error("register_aws_account_failed",
                         name=name, error=str(e))
            return {"error": str(e)}

    async def test_cloud_connection(
        self,
        provider: str,
        account_id: str,
    ) -> Dict[str, Any]:
        """Test cloud account connection.

        Args:
            provider: Cloud provider (aws, azure, gcp)
            account_id: Account ID

        Returns:
            Connection test result
        """
        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/api/v1/cloud/{provider}/{account_id}/test-connection",
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error(
                "test_cloud_connection_failed",
                provider=provider,
                account_id=account_id,
                error=str(e),
            )
            return {"success": False, "message": str(e)}


# ============ Helper Functions ============

async def get_onboarding_client(
    base_url: str = "http://localhost:8011",
    api_key: Optional[str] = None,
) -> OnboardingClient:
    """Create and return an OnboardingClient instance.

    Args:
        base_url: Base URL of the Onboarding Service
        api_key: Optional API key for authentication

    Returns:
        Configured OnboardingClient instance
    """
    return OnboardingClient(base_url=base_url, api_key=api_key)


async def get_all_clusters(
    client: OnboardingClient,
    provider: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Get all registered clusters.

    Args:
        client: OnboardingClient instance
        provider: Optional provider filter

    Returns:
        List of cluster dictionaries
    """
    clusters = await client.list_clusters(provider=provider, limit=1000)
    if isinstance(clusters, list):
        return clusters
    return []


async def get_active_clusters(
    client: OnboardingClient,
) -> List[Dict[str, Any]]:
    """Get all active (healthy) clusters.

    Args:
        client: OnboardingClient instance

    Returns:
        List of active cluster dictionaries
    """
    clusters = await client.list_clusters(status_filter="active", limit=1000)
    if isinstance(clusters, list):
        return clusters
    return []
