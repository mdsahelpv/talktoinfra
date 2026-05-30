from pydantic import BaseModel


class ChatRequest(BaseModel):
    session_id: str = ""
    message: str


class ChatResponse(BaseModel):
    session_id: str
    message: str
    tool_calls: list[dict] = []
    requires_approval: bool = False
    approval_id: str | None = None
