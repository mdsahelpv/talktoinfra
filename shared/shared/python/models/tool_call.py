from datetime import datetime, timezone
from uuid import uuid4
from typing import Any
from pydantic import BaseModel, Field

from .action import PermissionTier


class ToolCallRequest(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    action: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ToolCallResponse(BaseModel):
    id: str
    success: bool
    output: Any = None
    error: str | None = None
    duration_ms: int = 0
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    truncated: bool = False


class ApprovalRequest(BaseModel):
    action: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    tier: PermissionTier
    reason: str = ""
    session_id: str = ""
    expires_at: str | None = None


class ApprovalResponse(BaseModel):
    approved: bool
    approved_by: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    note: str = ""
