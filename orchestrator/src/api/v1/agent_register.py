"""Agent registration endpoints — called by in-cluster agent on startup."""

from datetime import datetime, timezone
from pydantic import BaseModel
from fastapi import APIRouter

router = APIRouter()

# In-memory store of connected agents
_connected_agents: dict[str, dict] = {}


class AgentRegistration(BaseModel):
    agent_id: str
    version: str
    actions: list[str] = []


class Heartbeat(BaseModel):
    agent_id: str


@router.post("/register")
async def register_agent(reg: AgentRegistration):
    _connected_agents[reg.agent_id] = {
        "agent_id": reg.agent_id,
        "version": reg.version,
        "actions": reg.actions,
        "status": "online",
        "last_seen": datetime.now(timezone.utc).isoformat(),
    }
    return {"status": "registered", "agent_id": reg.agent_id}


@router.post("/heartbeat")
async def agent_heartbeat(hb: Heartbeat):
    if hb.agent_id in _connected_agents:
        _connected_agents[hb.agent_id]["last_seen"] = datetime.now(timezone.utc).isoformat()
        _connected_agents[hb.agent_id]["status"] = "online"
        return {"status": "ok"}
    return {"status": "unknown_agent"}


@router.get("")
async def list_agents():
    return {"agents": list(_connected_agents.values())}


@router.get("/{agent_id}")
async def get_agent(agent_id: str):
    agent = _connected_agents.get(agent_id)
    if not agent:
        return {"error": "Agent not found"}, 404
    return agent
