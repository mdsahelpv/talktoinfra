"""Heartbeat SLA monitoring — tracks agent liveness."""

import asyncio
import logging
from datetime import datetime, timezone

from src.config import settings

logger = logging.getLogger(__name__)


class HeartbeatMonitor:
    def __init__(self) -> None:
        self._heartbeats: dict[str, datetime] = {}
        self._sla_seconds = settings.heartbeat_sla_seconds
        self._background_task: asyncio.Task | None = None

    def record_heartbeat(self, agent_id: str) -> None:
        self._heartbeats[agent_id] = datetime.now(timezone.utc)

    def check_sla(self, agent_id: str, max_gap_seconds: int | None = None) -> bool:
        max_gap = max_gap_seconds or self._sla_seconds
        last = self._heartbeats.get(agent_id)
        if last is None:
            return False
        elapsed = (datetime.now(timezone.utc) - last).total_seconds()
        return elapsed <= max_gap

    def get_stale_agents(self, max_gap_seconds: int | None = None) -> list[str]:
        max_gap = max_gap_seconds or self._sla_seconds
        now = datetime.now(timezone.utc)
        stale = []
        for agent_id, last_seen in self._heartbeats.items():
            if (now - last_seen).total_seconds() > max_gap:
                stale.append(agent_id)
        return stale

    async def start_background_check(self, interval_seconds: int = 30) -> None:
        async def _check_loop():
            while True:
                await asyncio.sleep(interval_seconds)
                stale = self.get_stale_agents()
                for agent_id in stale:
                    logger.warning("Stale agent detected (no heartbeat): %s", agent_id)

        self._background_task = asyncio.create_task(_check_loop())

    async def stop_background_check(self) -> None:
        if self._background_task:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass
            self._background_task = None
