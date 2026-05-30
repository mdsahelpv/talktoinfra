"""SIEM streaming — exports audit events to external security monitoring."""

import json
import logging
import socket
from abc import ABC, abstractmethod
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class SIEMExporter(ABC):
    @abstractmethod
    async def export(self, event: dict) -> bool:
        ...


class WebhookExporter(SIEMExporter):
    def __init__(self, url: str) -> None:
        self.url = url

    async def export(self, event: dict) -> bool:
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.post(self.url, json=event, timeout=10)
                resp.raise_for_status()
                return True
        except Exception as exc:
            logger.error("Webhook SIEM export failed: %s", exc)
            return False


class SyslogExporter(SIEMExporter):
    def __init__(self, host: str, port: int = 514) -> None:
        self.host = host
        self.port = port

    async def export(self, event: dict) -> bool:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            msg = json.dumps(event, default=str)
            sock.sendto(msg.encode(), (self.host, self.port))
            sock.close()
            return True
        except Exception as exc:
            logger.error("Syslog SIEM export failed: %s", exc)
            return False


class CompositeExporter(SIEMExporter):
    def __init__(self, exporters: list[SIEMExporter]) -> None:
        self._exporters = exporters

    async def export(self, event: dict) -> bool:
        results = []
        for exporter in self._exporters:
            try:
                ok = await exporter.export(event)
                results.append(ok)
            except Exception as exc:
                logger.error("CompositeExporter sub-export failed: %s", exc)
                results.append(False)
        return all(results)

    def add_exporter(self, exporter: SIEMExporter) -> None:
        self._exporters.append(exporter)
