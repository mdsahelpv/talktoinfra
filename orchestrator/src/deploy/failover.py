"""Multi-region failover — monitors primary DB health and promotes replica."""

import logging
from dataclasses import dataclass, field

from src.config import settings

logger = logging.getLogger(__name__)


@dataclass
class RegionConfig:
    database_url: str = ""
    replica_url: str = ""
    active: bool = True


class FailoverManager:
    def __init__(self) -> None:
        self._regions: dict[str, RegionConfig] = {}
        self._primary_region = settings.deploy_primary_region
        self._read_only_mode = False

        regions_str = settings.deploy_regions
        if regions_str:
            for region_str in regions_str.split(","):
                parts = region_str.strip().split(":")
                if len(parts) >= 2:
                    name = parts[0]
                    db_url = parts[1]
                    replica_url = parts[2] if len(parts) > 2 else ""
                    self._regions[name] = RegionConfig(
                        database_url=db_url,
                        replica_url=replica_url,
                        active=(name == self._primary_region),
                    )

    async def check_primary_health(self) -> bool:
        region = self._regions.get(self._primary_region)
        if not region:
            return True
        try:
            from sqlalchemy.ext.asyncio import create_async_engine
            engine = create_async_engine(region.database_url, echo=settings.debug)
            async with engine.connect() as conn:
                await conn.execute(lambda: None)
            await engine.dispose()
            return True
        except Exception as exc:
            logger.error("Primary DB health check failed: %s", exc)
            return False

    async def promote_replica(self, region_name: str) -> bool:
        region = self._regions.get(region_name)
        if not region or not region.replica_url:
            logger.warning("No replica configured for region %s", region_name)
            return False
        region.active = True
        self._primary_region = region_name
        logger.info("Promoted replica in %s to primary", region_name)
        return True

    def read_only_mode(self) -> bool:
        if not self._regions:
            return False
        any_active = any(r.active for r in self._regions.values())
        if not any_active:
            self._read_only_mode = True
        return self._read_only_mode

    @property
    def primary_region(self) -> str:
        return self._primary_region

    @property
    def active_database_url(self) -> str:
        region = self._regions.get(self._primary_region)
        if region and region.active:
            return region.database_url
        for r_name, r_config in self._regions.items():
            if r_config.active:
                return r_config.database_url
        return settings.database_url


failover_manager = FailoverManager()
