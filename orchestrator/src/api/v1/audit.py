from fastapi import APIRouter, Depends, HTTPException

from src.auth.deps import get_auth_context, require_permission, AuthContext
from src.auth.rbac import Permission
from src.storage.repository import AuditRepository

router = APIRouter()
audit_repo = AuditRepository()


@router.get("")
async def get_audit_log(
    session_id: str = "",
    limit: int = 50,
    offset: int = 0,
    auth: AuthContext = Depends(require_permission(Permission.AUDIT_READ)),
):
    entries = await audit_repo.list(
        session_id=session_id,
        org_id=auth.org_id,
        limit=limit,
        offset=offset,
    )
    total = await audit_repo.count(session_id=session_id, org_id=auth.org_id)
    return {"entries": entries, "total": total}


@router.get("/verify")
async def verify_audit_chain(
    auth: AuthContext = Depends(require_permission(Permission.AUDIT_EXPORT)),
):
    violations = await audit_repo.verify_chain()
    if violations:
        return {"valid": False, "violations": violations}
    return {"valid": True, "message": "Audit chain integrity verified"}
