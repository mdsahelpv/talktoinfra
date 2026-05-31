import ipaddress
import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import click

from ..client.api import APIClient

SERVICE_MAP = {
    22: "SSH", 80: "HTTP", 443: "HTTPS", 445: "SMB",
    3306: "MySQL", 5432: "PostgreSQL", 6379: "Redis",
    27017: "MongoDB", 1433: "MSSQL", 1521: "Oracle",
    8080: "HTTP-Alt", 8443: "HTTPS-Alt", 6443: "K8s API",
    9090: "Prometheus", 3000: "Grafana", 8000: "Orchestrator", 9100: "Node-Exporter",
    9200: "Elasticsearch", 5601: "Kibana", 2379: "etcd",
    3389: "RDP", 5900: "VNC", 25: "SMTP", 53: "DNS",
}

QUICK_PORTS = [22, 80, 443, 445, 8080, 8443, 3306, 5432, 6379, 27017, 6443, 9090, 3000, 3389]


def _check_port(ip: str, port: int, timeout: float) -> int | None:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        result = s.connect_ex((ip, port))
        s.close()
        return port if result == 0 else None
    except:
        return None


def _scan_host(ip: str, ports: list[int], timeout: float) -> list[int]:
    found = []
    for p in ports:
        r = _check_port(ip, p, timeout)
        if r:
            found.append(r)
    return sorted(found)


@click.command("netscan")
@click.argument("cidr", required=True)
@click.option("--ports", "-p", default=",".join(str(p) for p in QUICK_PORTS), help="Comma-separated ports")
@click.option("--timeout", "-t", default=1.0, help="Connection timeout (seconds)")
@click.option("--workers", "-w", default=50, help="Concurrent host workers")
@click.option("--publish", is_flag=True, help="Publish results to orchestrator")
@click.option("--api-key", envvar="TALKTOINFRA_API_KEY", default="", help="Orchestrator API key")
@click.option("--orchestrator-url", "-o", envvar="TALKTOINFRA_ORCHESTRATOR_URL", default="http://localhost:8000", help="Orchestrator URL")
def netscan_cmd(cidr, ports, timeout, workers, publish, api_key, orchestrator_url):
    """Scan a CIDR range for live hosts and open ports.

    Runs from YOUR machine (not Docker), so it can reach your actual LAN.

    Examples:

        talktoinfra netscan 192.168.1.0/24

        talktoinfra netscan 10.0.0.0/24 -p 22,80,443,3306,5432

        talktoinfra netscan 192.168.1.0/24 --publish
    """
    port_list = [int(p.strip()) for p in ports.split(",") if p.strip()]
    network = ipaddress.ip_network(cidr, strict=False)
    hosts = list(network.hosts())
    total = len(hosts)

    print(f"Scanning {cidr} ({total} hosts) for {len(port_list)} ports...\n")
    print(f"  Concurrency: {workers} workers, timeout: {timeout}s\n")
    start = time.time()

    discovered = []

    with ThreadPoolExecutor(max_workers=workers) as pool:
        fut_map = {pool.submit(_scan_host, str(ip), port_list, timeout): str(ip) for ip in hosts}
        done = 0
        for fut in as_completed(fut_map):
            ip = fut_map[fut]
            open_ports = fut.result()
            done += 1
            if open_ports:
                services = [f"{p}/{SERVICE_MAP.get(p, '?')}" for p in open_ports]
                discovered.append({"ip": ip, "ports": open_ports, "services": services})
                print(f"  + {ip:16s}  {', '.join(services)}")

            if done % 50 == 0 or done == total:
                elapsed = time.time() - start
                pct = done / total * 100
                print(f"  [{pct:3.0f}%] {done}/{total} hosts ({elapsed:.1f}s)")

    elapsed = time.time() - start
    print(f"\nDone — {len(discovered)} host(s) found in {elapsed:.1f}s")

    if publish and discovered:
        try:
            client = APIClient(orchestrator_url, api_key)
            import json
            payload = {
                "cidr": cidr,
                "hosts": [
                    {"ip": h["ip"], "ports": [{"port": p, "service": SERVICE_MAP.get(p, "unknown")} for p in h["ports"]]}
                    for h in discovered
                ],
                "scanned_from": "cli",
            }
            resp = client._http.post(
                f"{orchestrator_url}/api/v1/network-scan/publish",
                json=payload,
                headers=client._headers(),
            )
            if resp.status_code == 200:
                job_id = resp.json().get("job_id", "")
                print(f"  Published to orchestrator — job ID: {job_id}")
            else:
                print(f"  Publish failed: {resp.status_code} {resp.text}")
        except Exception as e:
            print(f"  Publish failed: {e}")
