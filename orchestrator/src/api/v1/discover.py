from fastapi import APIRouter, Depends
from src.auth.deps import require_permission, AuthContext
from src.auth.rbac import Permission
from src.core.agent_registry import AgentRegistry

router = APIRouter()
registry = AgentRegistry()

SCAN_TEMPLATES = {
    "k8s": {
        "icon": "⎈",
        "resources": {
            "pods": {"count": 0, "examples": []},
            "nodes": {"count": 0, "examples": []},
            "services": {"count": 0, "examples": []},
            "deployments": {"count": 0, "examples": []},
            "namespaces": {"count": 0, "examples": []},
        },
    },
    "network": {
        "icon": "🌐",
        "resources": {
            "dns_servers": {"count": 0, "examples": []},
            "resolved_domains": {"count": 0, "examples": []},
        },
    },
    "cloud": {
        "icon": "☁️",
        "resources": {
            "ec2_instances": {"count": 0, "examples": []},
            "vpc_count": {"count": 0, "examples": []},
            "s3_buckets": {"count": 0, "examples": []},
        },
    },
    "ad": {
        "icon": "🏢",
        "resources": {
            "users": {"count": 0, "examples": []},
            "groups": {"count": 0, "examples": []},
            "computers": {"count": 0, "examples": []},
        },
    },
    "onprem": {
        "icon": "🖥️",
        "resources": {
            "servers": {"count": 0, "examples": []},
            "services": {"count": 0, "examples": []},
        },
    },
    "monitoring": {
        "icon": "📈",
        "resources": {
            "alerts": {"count": 0, "examples": []},
            "metrics": {"count": 0, "examples": []},
        },
    },
    "database": {
        "icon": "🗄️",
        "resources": {
            "databases": {"count": 0, "examples": []},
            "slow_queries": {"count": 0, "examples": []},
        },
    },
}


@router.get("/discover/scan")
async def scan_infrastructure(
    auth: AuthContext = Depends(require_permission(Permission.AGENT_READ)),
):
    agents = registry.list_agents()
    result = {}
    for a in agents:
        tpl = SCAN_TEMPLATES.get(a["name"])
        if not tpl:
            continue
        result[a["name"]] = {
            "name": a["name"],
            "description": a["description"],
            "icon": tpl["icon"],
            "tools": a["tools"],
            "status": "connected" if a["tools"] else "disconnected",
            "resources": tpl["resources"],
        }
    return {"scan": result, "total_agents": len(result), "scan_timestamp": None}


@router.get("/discover/summary")
async def discovery_summary(
    auth: AuthContext = Depends(require_permission(Permission.AGENT_READ)),
):
    agents = registry.list_agents()
    total_resources = 0
    categories = []
    for a in agents:
        tpl = SCAN_TEMPLATES.get(a["name"])
        if not tpl:
            continue
        resource_count = sum(r["count"] for r in tpl["resources"].values())
        total_resources += resource_count
        categories.append({
            "name": a["name"],
            "icon": tpl["icon"],
            "resource_count": resource_count,
            "tool_count": len(a["tools"]),
            "status": "connected" if a["tools"] else "disconnected",
        })
    return {
        "total_categories": len(categories),
        "total_resources": total_resources,
        "categories": categories,
    }
