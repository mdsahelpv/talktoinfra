"""Autonomy maturity model — maps agent autonomy to permission tiers."""

from dataclasses import dataclass, field
from enum import Enum


class AutonomyLevel(str, Enum):
    INTERN = "intern"
    JUNIOR = "junior"
    SENIOR = "senior"
    PRINCIPAL = "principal"


@dataclass
class AutonomyConfig:
    level: AutonomyLevel
    allowed_tiers: set[str] = field(default_factory=set)
    auto_tiers: set[str] = field(default_factory=set)
    hitl_tiers: set[str] = field(default_factory=set)

    @classmethod
    def for_level(cls, level: AutonomyLevel) -> "AutonomyConfig":
        configs = {
            AutonomyLevel.INTERN: cls(
                level=level,
                allowed_tiers={"read"},
                auto_tiers={"read"},
                hitl_tiers=set(),
            ),
            AutonomyLevel.JUNIOR: cls(
                level=level,
                allowed_tiers={"read", "mutate"},
                auto_tiers={"read"},
                hitl_tiers={"mutate"},
            ),
            AutonomyLevel.SENIOR: cls(
                level=level,
                allowed_tiers={"read", "mutate", "destructive"},
                auto_tiers={"read", "mutate"},
                hitl_tiers={"destructive"},
            ),
            AutonomyLevel.PRINCIPAL: cls(
                level=level,
                allowed_tiers={"read", "mutate", "destructive"},
                auto_tiers={"read", "mutate", "destructive"},
                hitl_tiers=set(),
            ),
        }
        return configs[level]


def get_effective_tier(autonomy_level: AutonomyLevel, requested_tier: str) -> str:
    config = AutonomyConfig.for_level(autonomy_level)
    if requested_tier in config.allowed_tiers:
        return requested_tier
    return "read"
