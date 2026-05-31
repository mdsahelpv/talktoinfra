from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant" | "system"
    content: str
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ConversationTurn(BaseModel):
    user_message: ChatMessage
    assistant_message: ChatMessage | None = None
    intermediate_tool_calls: list[dict[str, Any]] = Field(default_factory=list)


class ChatSession(BaseModel):
    id: str = Field(default_factory=lambda: str(__import__("uuid").uuid4()))
    user_id: str = ""
    description: str = ""
    messages: list[ChatMessage] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_active: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = "active"  # "active" | "archived"
    metadata: dict[str, Any] = Field(default_factory=dict)
