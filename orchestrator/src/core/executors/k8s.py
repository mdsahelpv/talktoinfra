"""Kubernetes action executor — uses kubectl or K8s Python client."""

import asyncio
import json


async def execute_k8s_action(action: str, params: dict) -> dict:
    """Execute a Kubernetes action. In MVP, uses subprocess kubectl.
    Production should use the official kubernetes Python client."""
    try:
        cmd = _build_kubectl_command(action, params)
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        if proc.returncode != 0:
            return {"success": False, "error": stderr.decode().strip()}
        output = stdout.decode().strip()
        return {"success": True, "output": output}
    except asyncio.TimeoutError:
        return {"success": False, "error": "Command timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _build_kubectl_command(action: str, params: dict) -> str:
    ns = params.get("namespace", "default")
    all_ns = params.get("all_namespaces", False)
    ns_flag = "" if all_ns else f"-n {ns}"

    commands = {
        "k8s_get_pods": f"kubectl get pods {ns_flag} -o wide",
        "k8s_describe_pod": f"kubectl describe pod {params['pod_name']} {ns_flag}",
        "k8s_logs": _build_logs_cmd(params, ns_flag),
        "k8s_events": "kubectl get events --sort-by=.lastTimestamp " + ("--all-namespaces" if all_ns else ns_flag),
        "k8s_top_pod": f"kubectl top pod {ns_flag}",
        "k8s_get_deployments": f"kubectl get deployments {ns_flag}",
        "k8s_restart_deployment": f"kubectl rollout restart deployment/{params['name']} {ns_flag}",
        "k8s_scale_deployment": f"kubectl scale deployment/{params['name']} --replicas={params['replicas']} {ns_flag}",
        "k8s_delete_pod": f"kubectl delete pod {params['pod_name']} {ns_flag}",
        "k8s_get_nodes": "kubectl get nodes -o wide",
    }
    return commands.get(action, "kubectl help")


def _build_logs_cmd(params: dict, ns_flag: str) -> str:
    cmd = f"kubectl logs {params['pod_name']} {ns_flag}"
    if params.get("container"):
        cmd += f" -c {params['container']}"
    if params.get("tail_lines"):
        cmd += f" --tail={params['tail_lines']}"
    if params.get("previous"):
        cmd += " --previous"
    return cmd
