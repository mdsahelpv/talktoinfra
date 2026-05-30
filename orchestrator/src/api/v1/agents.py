from fastapi import APIRouter, Depends, HTTPException

from src.auth.deps import require_permission, AuthContext
from src.auth.rbac import Permission
from src.core.agent_registry import AgentRegistry

router = APIRouter()
registry = AgentRegistry()


@router.get("")
async def list_agents(auth: AuthContext = Depends(require_permission(Permission.AGENT_READ))):
    agents = registry.list_agents()
    return {"agents": agents}


@router.get("/{agent_name}")
async def get_agent_status(
    agent_name: str,
    auth: AuthContext = Depends(require_permission(Permission.AGENT_READ)),
):
    agent = registry.get_agent(agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"name": agent_name, "status": agent.get_status(), "tools": agent.list_tools()}
