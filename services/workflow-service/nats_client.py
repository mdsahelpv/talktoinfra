"""
NATS Client for Workflow Event Publishing

Provides async NATS client wrapper for workflow event publishing.
"""

from typing import Any, Awaitable, Callable, Dict, List, Optional
from nats.aio.client import Client as NATS
from nats.aio.msg import Msg
import structlog


logger = structlog.get_logger()


class NATSClient:
    """NATS client for workflow event publishing."""

    def __init__(self):
        """Initialize NATS client."""
        self._client: Optional[NATS] = None
        self._connected: bool = False

    async def connect(
        self,
        servers: List[str],
        name: str = "workflow-service",
        connection_timeout: int = 5,
        reconnect_timeout: int = 5,
    ) -> None:
        """Connect to NATS cluster.

        Args:
            servers: List of NATS server URLs
            name: Client name for identification
            connection_timeout: Connection timeout in seconds
            reconnect_timeout: Reconnect timeout in seconds
        """
        try:
            self._client = NATS()
            await self._client.connect(
                servers=servers,
                name=name,
                connect_timeout=connection_timeout,
                reconnect_time_wait=reconnect_timeout,
            )
            self._connected = True
            logger.info("nats_connected", servers=servers, name=name)
        except Exception as e:
            logger.error("nats_connection_failed", error=str(e))
            raise

    async def disconnect(self) -> None:
        """Disconnect from NATS."""
        if self._client and self._connected:
            await self._client.close()
            self._connected = False
            logger.info("nats_disconnected")

    async def publish(self, subject: str, payload: Dict[str, Any]) -> None:
        """Publish event to subject.

        Args:
            subject: NATS subject to publish to
            payload: Dictionary payload to send
        """
        if not self._connected or not self._client:
            logger.warning("nats_not_connected", subject=subject)
            return

        try:
            await self._client.publish(
                subject=subject,
                payload=self._encode_payload(payload),
            )
            logger.info("nats_published", subject=subject)
        except Exception as e:
            logger.error("nats_publish_failed", subject=subject, error=str(e))
            raise

    async def subscribe(
        self,
        subject: str,
        callback: Callable[[Msg], Awaitable[None]],
        queue: str = "",
    ) -> None:
        """Subscribe to subject for receiving events.

        Args:
            subject: NATS subject to subscribe to
            callback: Async callback function for received messages
            queue: Optional queue group name
        """
        if not self._connected or not self._client:
            logger.warning("nats_not_connected", subject=subject)
            return

        try:
            await self._client.subscribe(
                subject=subject,
                cb=callback,
                queue=queue,
            )
            logger.info("nats_subscribed", subject=subject, queue=queue)
        except Exception as e:
            logger.error("nats_subscribe_failed", subject=subject, error=str(e))
            raise

    def is_connected(self) -> bool:
        """Check if client is connected to NATS.

        Returns:
            True if connected, False otherwise
        """
        return self._connected

    @staticmethod
    def _encode_payload(payload: Dict[str, Any]) -> bytes:
        """Encode payload to bytes.

        Args:
            payload: Dictionary to encode

        Returns:
            JSON-encoded bytes
        """
        import json

        return json.dumps(payload).encode()


# Global NATS client instance
_nats_client: Optional[NATSClient] = None


async def get_nats_client() -> NATSClient:
    """Get or create the global NATS client instance.

    Returns:
        NATSClient instance
    """
    global _nats_client
    if _nats_client is None:
        _nats_client = NATSClient()
    return _nats_client


async def init_nats_client(
    servers: List[str],
    name: str = "workflow-service",
    connection_timeout: int = 5,
    reconnect_timeout: int = 5,
) -> NATSClient:
    """Initialize the global NATS client.

    Args:
        servers: List of NATS server URLs
        name: Client name for identification
        connection_timeout: Connection timeout in seconds
        reconnect_timeout: Reconnect timeout in seconds

    Returns:
        Initialized NATSClient instance
    """
    client = await get_nats_client()
    await client.connect(
        servers=servers,
        name=name,
        connection_timeout=connection_timeout,
        reconnect_timeout=reconnect_timeout,
    )
    return client


async def close_nats_client() -> None:
    """Close the global NATS client connection."""
    global _nats_client
    if _nats_client:
        await _nats_client.disconnect()
        _nats_client = None
