"""
Shared NATS Client for TalkAI Platform Services

Provides a centralized NATS client that can be used by all services
for event-driven communication.
"""

from typing import Any, Awaitable, Callable, Dict, List, Optional
from nats.aio.client import Client as NATS
from nats.aio.msg import Msg
import structlog


logger = structlog.get_logger()


class NATSClient:
    """Shared NATS client for cross-service event publishing and subscribing."""

    def __init__(self, service_name: str = "shared"):
        """Initialize NATS client.

        Args:
            service_name: Name of the service using this client
        """
        self._client: Optional[NATS] = None
        self._connected: bool = False
        self._service_name: str = service_name

    async def connect(
        self,
        servers: List[str],
        name: Optional[str] = None,
        connection_timeout: int = 5,
        reconnect_timeout: int = 5,
    ) -> None:
        """Connect to NATS cluster.

        Args:
            servers: List of NATS server URLs
            name: Client name for identification (defaults to service_name)
            connection_timeout: Connection timeout in seconds
            reconnect_timeout: Reconnect timeout in seconds
        """
        try:
            self._client = NATS()
            client_name = name or f"{self._service_name}-nats-client"
            await self._client.connect(
                servers=servers,
                name=client_name,
                connect_timeout=connection_timeout,
                reconnect_time_wait=reconnect_timeout,
            )
            self._connected = True
            logger.info("nats_connected", servers=servers, name=client_name)
        except Exception as e:
            logger.error("nats_connection_failed", error=str(e))
            raise

    async def disconnect(self) -> None:
        """Disconnect from NATS."""
        if self._client and self._connected:
            await self._client.close()
            self._connected = False
            logger.info("nats_disconnected", service=self._service_name)

    async def publish(self, subject: str, payload: Dict[str, Any]) -> None:
        """Publish event to subject.

        Args:
            subject: NATS subject to publish to
            payload: Dictionary payload to send
        """
        if not self._connected or not self._client:
            logger.warning("nats_not_connected", subject=subject, service=self._service_name)
            return

        try:
            await self._client.publish(
                subject=subject,
                payload=self._encode_payload(payload),
            )
            logger.info("nats_published", subject=subject, service=self._service_name)
        except Exception as e:
            logger.error("nats_publish_failed", subject=subject, error=str(e), service=self._service_name)
            raise

    async def subscribe(
        self,
        subject: str,
        callback: Callable[[Msg], Awaitable[None]],
        queue: str = "",
    ) -> str:
        """Subscribe to subject for receiving events.

        Args:
            subject: NATS subject to subscribe to
            callback: Async callback function for received messages
            queue: Optional queue group name

        Returns:
            Subscription ID
        """
        if not self._connected or not self._client:
            logger.warning("nats_not_connected", subject=subject, service=self._service_name)
            return ""

        try:
            sub = await self._client.subscribe(
                subject=subject,
                cb=callback,
                queue=queue,
            )
            logger.info("nats_subscribed", subject=subject, queue=queue, service=self._service_name)
            return sub.sid
        except Exception as e:
            logger.error("nats_subscribe_failed", subject=subject, error=str(e), service=self._service_name)
            raise

    async def unsubscribe(self, sid: str) -> None:
        """Unsubscribe from a subject.

        Args:
            sid: Subscription ID to unsubscribe
        """
        if not self._connected or not self._client:
            return

        try:
            await self._client.unsubscribe(sid)
            logger.info("nats_unsubscribed", sid=sid, service=self._service_name)
        except Exception as e:
            logger.error("nats_unsubscribe_failed", sid=sid, error=str(e), service=self._service_name)

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


async def get_nats_client(service_name: str = "shared") -> NATSClient:
    """Get or create the global NATS client instance.

    Args:
        service_name: Name of the service

    Returns:
        NATSClient instance
    """
    global _nats_client
    if _nats_client is None:
        _nats_client = NATSClient(service_name=service_name)
    return _nats_client


async def init_nats_client(
    servers: List[str],
    service_name: str = "shared",
    name: Optional[str] = None,
    connection_timeout: int = 5,
    reconnect_timeout: int = 5,
) -> NATSClient:
    """Initialize the global NATS client.

    Args:
        servers: List of NATS server URLs
        service_name: Name of the service
        name: Client name for identification
        connection_timeout: Connection timeout in seconds
        reconnect_timeout: Reconnect timeout in seconds

    Returns:
        Initialized NATSClient instance
    """
    client = await get_nats_client(service_name=service_name)
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
