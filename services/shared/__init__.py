"""
Shared utilities for TalkAI Platform services.
"""

from .nats_client import NATSClient, get_nats_client, init_nats_client, close_nats_client

__all__ = [
    "NATSClient",
    "get_nats_client",
    "init_nats_client",
    "close_nats_client",
]
