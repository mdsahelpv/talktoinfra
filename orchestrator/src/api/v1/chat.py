from fastapi import APIRouter, Depends, HTTPException

from src.auth.deps import get_auth_context, require_permission, AuthContext
from src.auth.rbac import Permission
from src.core.agent_engine import AgentEngine
from src.models.chat import ChatRequest, ChatResponse
from src.models.session import SessionManager

router = APIRouter()
agent_engine = AgentEngine()
session_manager = SessionManager()


@router.post("")
async def chat(
    request: ChatRequest,
    auth: AuthContext = Depends(require_permission(Permission.TOOL_EXECUTE)),
):
    session = await session_manager.get_or_create(request.session_id, auth.user_id)
    response = await agent_engine.process_message(
        session_id=session.id,
        message=request.message,
        user_id=auth.user_id,
        org_id=auth.org_id,
        user_roles=auth.roles,
    )
    return ChatResponse(
        session_id=session.id,
        message=response["content"],
        tool_calls=response.get("tool_calls", []),
        requires_approval=response.get("requires_approval", False),
        approval_id=response.get("approval_id"),
    )


@router.post("/approve")
async def approve_action(
    approval_id: str,
    approved: bool,
    note: str = "",
    auth: AuthContext = Depends(require_permission(Permission.APPROVE_MUTATE)),
):
    result = await agent_engine.handle_approval(
        approval_id=approval_id,
        approved=approved,
        approved_by=auth.user_id,
        note=note,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return {"success": True, "tool_call_id": result}
