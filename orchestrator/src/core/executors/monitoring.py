"""Monitoring action executor (Prometheus)."""

import asyncio


async def execute_monitoring_action(action: str, params: dict) -> dict:
    try:
        commands = {
            "prometheus_query": _build_promql_cmd(params),
            "prometheus_get_alerts": "curl -s http://localhost:9090/api/v1/alerts",
        }
        cmd = commands.get(action)
        if not cmd:
            return {"success": False, "error": f"Unknown monitoring action: {action}"}

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


def _build_promql_cmd(params: dict) -> str:
    query = params["query"]
    time_range = params.get("time_range", "5m")
    return f'curl -s "http://localhost:9090/api/v1/query?query={__import__("urllib").parse.quote(query)}"'
