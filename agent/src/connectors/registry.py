"""Registry of all available connectors."""

from src.config import AgentConfig
from src.connectors.base import BaseConnector
from src.connectors.k8s import K8sConnector
from src.connectors.aws import AWSConnector
from src.connectors.dns import DNSConnector
from src.connectors.ad import ADConnector
from src.connectors.ssh import SSHConnector


class ConnectorRegistry:
    def __init__(self):
        self._connectors: dict[str, BaseConnector] = {}

    async def initialize_all(self, config: AgentConfig) -> None:
        connectors: list[BaseConnector] = []

        if config.k8s_enabled:
            connectors.append(K8sConnector(config))

        if config.aws_enabled:
            connectors.append(AWSConnector(config))

        if config.dns_enabled:
            connectors.append(DNSConnector())

        if config.ad_enabled:
            connectors.append(ADConnector(config))

        if config.ssh_enabled:
            connectors.append(SSHConnector(config))

        for c in connectors:
            try:
                await c.initialize()
                self._connectors[c.name] = c
                print(f"[agent] Connected: {c.name}")
            except Exception as e:
                print(f"[agent] Failed to initialize {c.name}: {e}")

    def get(self, name: str) -> BaseConnector | None:
        return self._connectors.get(name)

    def list_available(self) -> list[str]:
        return [c.name for c in self._connectors.values() if c.is_available]

    def all_health(self) -> dict[str, dict]:
        return {c.name: {"healthy": c.is_available} for c in self._connectors.values()}
