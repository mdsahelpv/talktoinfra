"""Base connector interface — each infra type implements this."""

from abc import ABC, abstractmethod


class BaseConnector(ABC):
    @abstractmethod
    async def initialize(self) -> None:
        """Set up connections, auth, etc."""
        ...

    @abstractmethod
    async def health(self) -> dict:
        """Return health status of this connector."""
        ...

    @abstractmethod
    async def execute(self, action: str, params: dict) -> dict:
        """Execute a tool action specific to this connector.

        Returns {"success": bool, "output": str, "error": str | None}
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def is_available(self) -> bool:
        ...
