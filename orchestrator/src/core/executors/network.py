"""Network/DNS action executor."""

import asyncio


async def execute_network_action(action: str, params: dict) -> dict:
    try:
        commands = {
            "dns_lookup": _build_dig_cmd(params),
            "network_ping": f"ping -n {params.get('count', 4)} {params['host']}",
            "network_port_check": _build_port_check_cmd(params),
            "network_traceroute": f"tracert {params['host']}" if __import__('sys').platform == 'win32' else f"traceroute {params['host']}",
        }
        cmd = commands.get(action)
        if not cmd:
            return {"success": False, "error": f"Unknown network action: {action}"}

        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        if proc.returncode != 0:
            return {"success": False, "error": stderr.decode().strip()}
        return {"success": True, "output": stdout.decode().strip()}
    except asyncio.TimeoutError:
        return {"success": False, "error": "Command timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _build_dig_cmd(params: dict) -> str:
    hostname = params["hostname"]
    rtype = params.get("record_type", "A")
    cmd = f"nslookup -type={rtype} {hostname}"
    if params.get("dns_server"):
        cmd += f" {params['dns_server']}"
    return cmd


def _build_port_check_cmd(params: dict) -> str:
    host = params["host"]
    port = params["port"]
    proto = params.get("protocol", "tcp")
    if __import__('sys').platform == 'win32':
        return f"powershell Test-NetConnection -ComputerName {host} -Port {port}"
    return f"nc -zv {host} {port}"
