"""Onboarding Service Client for Agent Service.

Client library for communicating with the Onboarding Service (Port 8011).
Provides methods for fetching clusters, credentials, and cloud accounts.
"""

from typing import Any, Dict, List, Optional

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
