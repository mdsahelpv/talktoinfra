"""Permission tier definitions."""

from enum import Enum


class ActionTier(str, Enum):
    READ = "read"
    MUTATE = "mutate"
    DESTRUCTIVE = "destructive"

    @property
    def requires_approval(self) -> bool:
        return self in (ActionTier.MUTATE, ActionTier.DESTRUCTIVE)

    @property
    def requires_fresh_approval(self) -> bool:
        return self == ActionTier.DESTRUCTIVE
