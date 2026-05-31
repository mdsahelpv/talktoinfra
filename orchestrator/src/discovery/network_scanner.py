import asyncio
import ipaddress
import time
import socket
from dataclasses import dataclass, field
from typing import Optional

SERVICE_MAP = {
    22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
    80: "HTTP", 110: "POP3", 123: "NTP", 143: "IMAP",
    443: "HTTPS", 465: "SMTPS", 587: "SMTP", 993: "IMAPS",
    995: "POP3S", 1433: "MSSQL", 1521: "Oracle DB",
    2049: "NFS", 2379: "etcd", 2380: "etcd-peer",
    3000: "Grafana/Node-exporter", 3306: "MySQL",
    3389: "RDP", 5432: "PostgreSQL", 5601: "Kibana",
    5900: "VNC", 6379: "Redis", 6443: "K8s API",
    8080: "HTTP-Alt", 8443: "HTTPS-Alt", 9000: "Portainer/SonarQube",
    9090: "Prometheus", 9100: "Node-Exporter", 9200: "Elasticsearch",
    10250: "K8s Kubelet", 10255: "K8s Kubelet-RO", 27017: "MongoDB",
}

QUICK_PORTS = [22, 80, 443, 8080, 8443, 3306, 5432, 6379, 27017, 6443, 9090, 3000, 5601, 9200, 2379]
FULL_PORTS = list(SERVICE_MAP.keys())


@dataclass
class DiscoveredPort:
    port: int
    service: str
    state: str = "open"


@dataclass
class DiscoveredHost:
    ip: str
    hostname: str = ""
    status: str = "unknown"
    ports: list[DiscoveredPort] = field(default_factory=list)


@dataclass
class ScanJob:
    id: str
    cidr: str
    status: str = "pending"
    progress: int = 0
    total_hosts: int = 0
    scanned_hosts: int = 0
    hosts: list[DiscoveredHost] = field(default_factory=list)
    created_at: float = 0.0
    completed_at: Optional[float] = None
    error: str = ""


class NetworkScanner:
    def __init__(self, concurrency: int = 100, timeout: float = 1.5):
        self.concurrency = concurrency
        self.timeout = timeout
        self._sem: Optional[asyncio.Semaphore] = None
        self._jobs: dict[str, ScanJob] = {}
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"scan_{int(time.time())}_{self._counter}"

    def get_job(self, job_id: str) -> Optional[ScanJob]:
        return self._jobs.get(job_id)

    async def _ping_host(self, ip: str) -> bool:
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, 7), timeout=self.timeout
            )
            writer.close()
            await writer.wait_closed()
            return True
        except (OSError, asyncio.TimeoutError):
            pass
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, 22), timeout=self.timeout
            )
            writer.close()
            await writer.wait_closed()
            return True
        except (OSError, asyncio.TimeoutError):
            pass
        return False

    async def _scan_ports(self, ip: str, ports: list[int]) -> list[DiscoveredPort]:
        result = []
        async def check_port(port: int):
            async with self._sem:
                try:
                    _, writer = await asyncio.wait_for(
                        asyncio.open_connection(ip, port), timeout=self.timeout
                    )
                    service = SERVICE_MAP.get(port, "unknown")
                    result.append(DiscoveredPort(port=port, service=service))
                    writer.close()
                    await writer.wait_closed()
                except (OSError, asyncio.TimeoutError):
                    pass
        tasks = [check_port(p) for p in ports]
        await asyncio.gather(*tasks)
        result.sort(key=lambda p: p.port)
        return result

    async def _resolve_hostname(self, ip: str) -> str:
        try:
            return await asyncio.get_event_loop().getaddrinfo(ip, None)
        except:
            return ""

    async def start_scan(self, cidr: str, ports: Optional[list[int]] = None) -> ScanJob:
        job = ScanJob(
            id=self._next_id(),
            cidr=cidr,
            status="running",
            created_at=time.time(),
        )
        self._jobs[job.id] = job
        asyncio.create_task(self._run_scan(job, ports or QUICK_PORTS))
        return job

    async def _run_scan(self, job: ScanJob, ports: list[int]):
        self._sem = asyncio.Semaphore(self.concurrency)
        try:
            network = ipaddress.ip_network(job.cidr, strict=False)
            hosts = [str(ip) for ip in network.hosts()]
            job.total_hosts = len(hosts)

            discovered = []
            for i, ip in enumerate(hosts):
                alive = await self._ping_host(ip)
                if alive:
                    hostname = await self._resolve_hostname(ip)
                    open_ports = await self._scan_ports(ip, ports)
                    discovered.append(DiscoveredHost(
                        ip=ip, hostname=hostname, status="up", ports=open_ports
                    ))
                job.scanned_hosts = i + 1
                job.progress = int((i + 1) / len(hosts) * 100)

            job.hosts = discovered
            job.status = "completed"
        except Exception as e:
            job.status = "failed"
            job.error = str(e)
        finally:
            job.completed_at = time.time()

    async def deploy_agent(self, job_id: str, host_ips: list[str]) -> dict:
        job = self._jobs.get(job_id)
        if not job:
            return {"error": "Scan job not found"}
        selected = [h for h in job.hosts if h.ip in host_ips]
        results = []
        for host in selected:
            if any(p.port == 22 for p in host.ports):
                results.append({
                    "ip": host.ip,
                    "status": "ready_for_deploy",
                    "method": "ansible_or_docker_remote",
                    "note": "SSH accessible — deploy agent via Ansible playbook or `docker -H`",
                })
            else:
                results.append({
                    "ip": host.ip,
                    "status": "ssh_not_available",
                    "note": "Port 22 not open — manual deployment required",
                })
        return {"hosts": results}

    async def connect_agentless(self, job_id: str, host_ips: list[str]) -> dict:
        job = self._jobs.get(job_id)
        if not job:
            return {"error": "Scan job not found"}
        selected = [h for h in job.hosts if h.ip in host_ips]
        results = []
        for host in selected:
            ports_info = [{"port": p.port, "service": p.service} for p in host.ports]
            results.append({
                "ip": host.ip,
                "hostname": host.hostname,
                "status": "agentless_ready",
                "open_ports": ports_info,
                "connect_method": "ssh" if any(p.port == 22 for p in host.ports) else "direct_port",
            })
        return {"connection_details": results}


scanner = NetworkScanner()
