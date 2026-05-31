from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class PermissionTier(str, Enum):
    READ = "read"
    MUTATE = "mutate"
    DESTRUCTIVE = "destructive"


class InfraCategory(str, Enum):
    KUBERNETES = "kubernetes"
    CLOUD = "cloud"
    NETWORK = "network"
    AD = "ad"
    ONPREM = "onprem"
    DATABASE = "database"
    MONITORING = "monitoring"


class ActionParam(BaseModel):
    name: str
    type: str = Field(description="string, integer, boolean, array, object")
    required: bool = False
    description: str = ""
    default: Any = None
    enum_values: list[str] = Field(default_factory=list, alias="enum")


class ActionDefinition(BaseModel):
    name: str
    description: str
    category: InfraCategory
    tier: PermissionTier
    timeout_seconds: int = 30
    parameters: list[ActionParam] = Field(default_factory=list)
    output_schema: dict[str, Any] = Field(default_factory=dict)


class ActionCatalog(BaseModel):
    actions: dict[str, ActionDefinition] = Field(default_factory=dict)

    def register(self, action: ActionDefinition) -> None:
        self.actions[action.name] = action

    def get(self, name: str) -> ActionDefinition | None:
        return self.actions.get(name)

    def list_by_category(self, category: InfraCategory) -> list[ActionDefinition]:
        return [a for a in self.actions.values() if a.category == category]

    def list_by_tier(self, tier: PermissionTier) -> list[ActionDefinition]:
        return [a for a in self.actions.values() if a.tier == tier]
