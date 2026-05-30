"""DNS connector using dnspython."""

import dns.resolver
import dns.reversename

from src.connectors.base import BaseConnector


class DNSConnector(BaseConnector):
    def __init__(self):
        self._available = True

    async def initialize(self) -> None:
        self._available = True

    @property
    def name(self) -> str:
        return "dns"

    @property
    def is_available(self) -> bool:
        return self._available

    async def health(self) -> dict:
        return {"healthy": self._available}

    async def execute(self, action: str, params: dict) -> dict:
        handlers = {
            "dns_lookup": self._dns_lookup,
            "network_ping": self._ping,
            "network_port_check": self._port_check,
        }
        handler = handlers.get(action)
        if not handler:
            return {"success": False, "error": f"Unknown network action: {action}"}
        return await handler(params)

    async def _dns_lookup(self, params: dict) -> dict:
        hostname = params["hostname"]
        rtype = params.get("record_type", "A")
        try:
            resolver = dns.resolver.Resolver()
            if params.get("dns_server"):
                resolver.nameservers = [params["dns_server"]]
            answers = resolver.resolve(hostname, rtype)
            items = [str(r) for r in answers]
            return {"success": True, "output": {"hostname": hostname, "type": rtype, "records": items}}
        except dns.resolver.NoAnswer:
            return {"success": False, "error": f"No {rtype} records found for {hostname}"}
        except dns.resolver.NXDOMAIN:
            return {"success": False, "error": f"Domain not found: {hostname}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _ping(self, params: dict) -> dict:
        import asyncio
        host = params["host"]
        count = params.get("count", 4)
        cmd = ["ping", "-n" if __import__("sys").platform == "win32" else "-c", str(count), host]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode == 0:
            return {"success": True, "output": stdout.decode().strip()}
        return {"success": False, "error": stderr.decode().strip()}

    async def _port_check(self, params: dict) -> dict:
        import asyncio
        host = params["host"]
        port = params["port"]
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=5
            )
            writer.close()
            return {"success": True, "output": f"Port {port} is open on {host}"}
        except asyncio.TimeoutError:
            return {"success": False, "error": f"Port {port} on {host} timed out"}
        except ConnectionRefusedError:
            return {"success": False, "error": f"Connection refused on {host}:{port}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
