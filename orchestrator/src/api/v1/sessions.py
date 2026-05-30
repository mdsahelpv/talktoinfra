from fastapi import APIRouter, Depends, HTTPException

from src.auth.deps import get_auth_context, require_permission, AuthContext
from src.auth.rbac import Permission
from src.models.session import SessionManager

router = APIRouter()
session_manager = SessionManager()


@router.post("")
async def create_session(
    description: str = "",
    auth: AuthContext = Depends(require_permission(Permission.SESSION_CREATE)),
):
    session = await session_manager.create(user_id=auth.user_id, description=description)
    return {"session_id": session.id, "created_at": session.created_at}


@router.get("/{session_id}")
async def get_session(
    session_id: str,
    auth: AuthContext = Depends(require_permission(Permission.SESSION_READ)),
):
    session = await session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": session.id,
        "user_id": session.user_id,
        "message_count": len(session.messages),
        "created_at": session.created_at,
        "last_active": session.last_active,
        "status": session.status,
    }


@router.get("")
async def list_sessions(
    auth: AuthContext = Depends(require_permission(Permission.SESSION_READ)),
    limit: int = 20,
    offset: int = 0,
):
    sessions = await session_manager.list(auth.user_id, limit, offset)
    return {"sessions": sessions, "total": len(sessions)}
