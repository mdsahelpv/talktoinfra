from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.auth.deps import require_permission, AuthContext
from src.auth.rbac import Permission
from src.discovery.network_scanner import scanner, SERVICE_MAP

QUICK_PORTS = [22, 80, 443, 445, 8080, 8443, 8000, 3306, 5432, 6379, 27017, 6443, 9090, 3000, 3389]

router = APIRouter()


class ScanRequest(BaseModel):
    cidr: str
    ports: list[int] | None = None


class DeployRequest(BaseModel):
    job_id: str
    host_ips: list[str]


class PublishResult(BaseModel):
    cidr: str
    hosts: list[dict]
    scanned_from: str = "cli"


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
        "Web": [80, 443, 8080, 8443, 8000],
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


@router.get("/network-scan")
async def list_scan_jobs(
    auth: AuthContext = Depends(require_permission(Permission.AGENT_READ)),
):
    jobs = []
    for jid, job in scanner._jobs.items():
        jobs.append({
            "job_id": jid,
            "cidr": job.cidr,
            "status": job.status,
            "hosts_found": len(job.hosts),
            "created_at": job.created_at,
            "completed_at": job.completed_at,
        })
    jobs.sort(key=lambda j: j["created_at"], reverse=True)
    return {"jobs": jobs, "total": len(jobs)}


@router.post("/network-scan/publish")
async def publish_scan_results(
    req: PublishResult,
    auth: AuthContext = Depends(require_permission(Permission.AGENT_READ)),
):
    from src.discovery.network_scanner import DiscoveredHost, DiscoveredPort, ScanJob
    import time
    hosts = []
    for h in req.hosts:
        ports = [DiscoveredPort(port=p["port"], service=p.get("service", "unknown")) for p in h.get("ports", [])]
        hosts.append(DiscoveredHost(ip=h["ip"], hostname=h.get("hostname", ""), status="up", ports=ports))
    job = ScanJob(
        id=f"published_{int(time.time())}",
        cidr=req.cidr,
        status="completed",
        progress=100,
        total_hosts=0,
        scanned_hosts=0,
        hosts=hosts,
        created_at=time.time(),
        completed_at=time.time(),
    )
    scanner._jobs[job.id] = job
    return {"job_id": job.id, "hosts_found": len(hosts), "status": "published"}


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
