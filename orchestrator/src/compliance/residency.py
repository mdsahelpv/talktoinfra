"""Data residency enforcement — tags data with region and validates data flows."""

import logging

from src.config import settings

logger = logging.getLogger(__name__)


class ResidencyEnforcer:
    def __init__(self) -> None:
        self._region = settings.data_residency_region
        self._region_endpoints: dict[str, str] = {}

    def tag_with_region(self, data: dict) -> dict:
        data["_region"] = self._region
        return data

    def validate_data_flow(self, source_region: str, target_region: str) -> list[str]:
        warnings = []
        if source_region != target_region and source_region != "auto" and target_region != "auto":
            warnings.append(
                f"Data flow crosses region boundaries: {source_region} -> {target_region}"
            )
        return warnings

    def register_storage_endpoint(self, region: str, endpoint: str) -> None:
        self._region_endpoints[region] = endpoint

    def get_storage_endpoint(self, region: str) -> str:
        if region in self._region_endpoints:
            return self._region_endpoints[region]
        if region == "auto":
            return settings.database_url
        return self._region_endpoints.get(self._region, settings.database_url)

    @property
    def region(self) -> str:
        return self._region


residency_enforcer = ResidencyEnforcer()
