from fastapi import APIRouter, Depends

from src.auth.deps import require_permission, AuthContext
from src.auth.rbac import Permission
from shared.python.catalog import build_default_catalog

router = APIRouter()


@router.get("")
async def list_tools(auth: AuthContext = Depends(require_permission(Permission.TOOL_READ))):
    catalog = build_default_catalog()
    tools = []
    for action in catalog.actions.values():
        tools.append({
            "name": action.name,
            "description": action.description,
            "category": action.category.value,
            "tier": action.tier.value,
            "parameters": [p.model_dump() for p in action.parameters],
        })
    return {"tools": tools, "total": len(tools)}
