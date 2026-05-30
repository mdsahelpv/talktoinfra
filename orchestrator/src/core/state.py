"""Conversation state for the LangGraph agent."""

from typing import TypedDict, Any


class ConversationState(TypedDict, total=False):
    session_id: str
    user_id: str
    user_message: str
    intent: str
    context: str
    tool_calls: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]
    response: str
    requires_approval: bool
    approval_id: str | None
    iteration: int
    max_iterations: int
    error: str | None
