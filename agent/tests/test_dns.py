"""Tests for the DNS connector."""

import pytest

from src.connectors.dns import DNSConnector


@pytest.mark.asyncio
async def test_dns_initialize():
    dns = DNSConnector()
    await dns.initialize()
    assert dns.is_available


@pytest.mark.asyncio
async def test_dns_lookup_invalid():
    dns = DNSConnector()
    await dns.initialize()
    result = await dns.execute("dns_lookup", {
        "hostname": "nonexistent-domain-xyz.test",
        "record_type": "A",
    })
    assert result["success"] is False
