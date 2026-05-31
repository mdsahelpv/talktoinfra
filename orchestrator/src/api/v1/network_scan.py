from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.auth.deps import require_permission, AuthContext
from src.auth.rbac import Permission
from src.discovery.network_scanner import scanner, QUICK_PORTS, SERVICE_MAP

router = APIRouter()


class ScanRequest(BaseModel):
    cidr: str
    ports: list[int] | None = None


class DeployRequest(BaseModel):
    job_id: str
    host_ips: list[str]


@router.post("/network-scan")
async def start_scan(
    req: ScanRequest,
    auth: AuthContext = Depends(require_permission(Permission.AGENT_READ)),
):
    try:
        job = await scanner.start_scan(req.cidr, req.ports)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "job_id": job.id,
        "cidr": job.cidr,
        "status": job.status,
        "total_hosts": job.total_hosts,
    }


@router.get("/network-scan/{job_id}")
async def get_scan_status(
    job_id: str,
    auth: AuthContext = Depends(require_permission(Permission.AGENT_READ)),
):
    job = scanner.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Scan job not found")
    return {
        "job_id": job.id,
        "cidr": job.cidr,
        "status": job.status,
        "progress": job.progress,
        "total_hosts": job.total_hosts,
        "scanned_hosts": job.scanned_hosts,
        "hosts_found": len(job.hosts),
        "hosts": [
            {
                "ip": h.ip,
                "hostname": h.hostname,
                "status": h.status,
                "ports": [
                    {"port": p.port, "service": p.service, "state": p.state}
                    for p in h.ports
                ],
            }
            for h in job.hosts
        ],
        "created_at": job.created_at,
        "completed_at": job.completed_at,
        "error": job.error,
    }


@router.get("/network-scan/ports/common")
async def list_common_ports(
    auth: AuthContext = Depends(require_permission(Permission.AGENT_READ)),
):
    groups = {
        "SSH": [22],
        "Web": [80, 443, 8080, 8443],
        "Databases": [3306, 5432, 6379, 27017, 1433, 1521],
        "Kubernetes": [6443, 2379, 2380, 10250, 10255],
        "Monitoring": [9090, 3000, 9100, 5601, 9200],
        "Remote Desktop": [3389, 5900],
        "Mail": [25, 110, 143, 465, 587, 993, 995],
    }
    return {
        "ports": [{"port": p, "service": s} for p, s in SERVICE_MAP.items()],
        "groups": groups,
        "quick_ports": QUICK_PORTS,
    }


@router.post("/network-scan/{job_id}/deploy-agent")
async def deploy_agent(
    job_id: str,
    req: DeployRequest,
    auth: AuthContext = Depends(require_permission(Permission.AGENT_MANAGE)),
):
    result = await scanner.deploy_agent(job_id, req.host_ips)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/network-scan/{job_id}/connect-agentless")
async def connect_agentless(
    job_id: str,
    req: DeployRequest,
    auth: AuthContext = Depends(require_permission(Permission.AGENT_MANAGE)),
):
    result = await scanner.connect_agentless(job_id, req.host_ips)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
