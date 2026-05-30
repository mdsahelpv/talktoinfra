from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field


class AuditEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(__import__("uuid").uuid4()))
    session_id: str = ""
    user_id: str = ""
    action: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)
    tier: str = ""
    approved: bool = False
    approved_by: str = ""
    status: str = ""  # "pending" | "approved" | "denied" | "executed" | "failed"
    result: str = ""
    duration_ms: int = 0
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
