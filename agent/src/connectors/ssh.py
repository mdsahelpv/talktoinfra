"""SSH connector for on-premise servers."""

import asyncio

from src.connectors.base import BaseConnector
from src.config import AgentConfig


class SSHConnector(BaseConnector):
    def __init__(self, cfg: AgentConfig):
        self._cfg = cfg
        self._available = cfg.ssh_enabled

    async def initialize(self) -> None:
        pass

    @property
    def name(self) -> str:
        return "ssh"

    @property
    def is_available(self) -> bool:
        return self._available

    async def health(self) -> dict:
        return {"healthy": self._available}

    async def execute(self, action: str, params: dict) -> dict:
        handlers = {
            "ssh_systemctl_status": self._systemctl_status,
            "ssh_journalctl": self._journalctl,
            "ssh_disk_usage": self._disk_usage,
            "ssh_memory_usage": self._memory_usage,
            "ssh_restart_service": self._restart_service,
        }
        handler = handlers.get(action)
        if not handler:
            return {"success": False, "error": f"Unknown SSH action: {action}"}
        return await handler(params)

    async def _run_ssh(self, host: str, cmd: str) -> tuple[str, str, int]:
        ssh_cmd = ["ssh", "-o", "ConnectTimeout=10", "-o", "StrictHostKeyChecking=no", host, cmd]
        proc = await asyncio.create_subprocess_exec(
            *ssh_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        return stdout.decode().strip(), stderr.decode().strip(), proc.returncode or 0

    async def _systemctl_status(self, params: dict) -> dict:
        host = params["host"]
        service = params["service"]
        stdout, stderr, rc = await self._run_ssh(host, f"systemctl status {service} --no-pager -l")
        if rc != 0:
            return {"success": False, "error": stderr}
        return {"success": True, "output": stdout}

    async def _journalctl(self, params: dict) -> dict:
        host = params["host"]
        cmd = "journalctl"
        if params.get("service"):
            cmd += f" -u {params['service']}"
        if params.get("tail_lines"):
            cmd += f" -n {params['tail_lines']}"
        if params.get("since"):
            cmd += f" --since '{params['since']}'"
        cmd += " --no-pager"
        stdout, stderr, rc = await self._run_ssh(host, cmd)
        return {"success": rc == 0, "output": stdout if rc == 0 else stderr}

    async def _disk_usage(self, params: dict) -> dict:
        host = params["host"]
        path = params.get("path", "/")
        stdout, stderr, rc = await self._run_ssh(host, f"df -h {path}")
        return {"success": rc == 0, "output": stdout if rc == 0 else stderr}

    async def _memory_usage(self, params: dict) -> dict:
        host = params["host"]
        stdout, stderr, rc = await self._run_ssh(host, "free -h")
        return {"success": rc == 0, "output": stdout if rc == 0 else stderr}

    async def _restart_service(self, params: dict) -> dict:
        host = params["host"]
        service = params["service"]
        stdout, stderr, rc = await self._run_ssh(host, f"sudo systemctl restart {service}")
        if rc != 0:
            return {"success": False, "error": stderr}
        return {"success": True, "output": f"Restarted {service} on {host}"}
