"""On-prem SSH action executor."""

import asyncio


async def execute_onprem_action(action: str, params: dict) -> dict:
    try:
        host = params["host"]
        commands = {
            "ssh_systemctl_status": f"ssh {host} systemctl status {params['service']}",
            "ssh_journalctl": _build_journalctl_cmd(params),
            "ssh_disk_usage": f"ssh {host} df -h {params.get('path', '/')}",
            "ssh_memory_usage": f"ssh {host} free -h",
            "ssh_restart_service": f"ssh {host} sudo systemctl restart {params['service']}",
        }
        cmd = commands.get(action)
        if not cmd:
            return {"success": False, "error": f"Unknown onprem action: {action}"}

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


def _build_journalctl_cmd(params: dict) -> str:
    host = params["host"]
    cmd = f"ssh {host} journalctl"
    if params.get("service"):
        cmd += f" -u {params['service']}"
    if params.get("tail_lines"):
        cmd += f" -n {params['tail_lines']}"
    if params.get("since"):
        cmd += f" --since '{params['since']}'"
    return cmd
