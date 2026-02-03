"""
Action Executor module.
Handles the actual execution of infrastructure actions.
"""

import asyncio
import subprocess
import time
from typing import Any, Dict, List, Optional

import structlog

from models import ActionExecutionResult

logger = structlog.get_logger()


class ActionExecutor:
    """Executes infrastructure actions."""

    def __init__(self):
        self.running_actions: Dict[str, asyncio.Task] = {}

    async def execute(
        self,
        action: str,
        target: str,
        parameters: Dict[str, Any],
    ) -> ActionExecutionResult:
        """Execute an action."""
        start_time = time.time()
        logs: List[str] = []

        try:
            logger.info(
                "action_execution_start",
                action=action,
                target=target,
            )

            # Build command based on action type
            command = self._build_command(action, target, parameters)
            logs.append(f"Executing command: {command}")

            # Execute command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()
            duration = time.time() - start_time

            output = stdout.decode() if stdout else ""
            error_output = stderr.decode() if stderr else ""

            logs.append(f"Exit code: {process.returncode}")
            if output:
                logs.append(f"Output: {output[:1000]}")  # Truncate long output
            if error_output:
                logs.append(f"Stderr: {error_output[:500]}")

            success = process.returncode == 0

            if success:
                logger.info(
                    "action_execution_success",
                    action=action,
                    target=target,
                    duration=duration,
                )
            else:
                logger.warning(
                    "action_execution_failed",
                    action=action,
                    target=target,
                    exit_code=process.returncode,
                )

            return ActionExecutionResult(
                success=success,
                output=output,
                exit_code=process.returncode,
                duration_seconds=duration,
                resources_modified=self._parse_resources_modified(output),
                logs=logs,
                metadata={
                    "command": command,
                    "stderr": error_output if error_output else None,
                },
            )

        except Exception as e:
            logger.error("action_execution_exception", error=str(e))
            return ActionExecutionResult(
                success=False,
                output="",
                exit_code=-1,
                duration_seconds=time.time() - start_time,
                logs=logs + [f"Exception: {str(e)}"],
                metadata={"error": str(e)},
            )

    def _build_command(
        self, action: str, target: str, parameters: Dict[str, Any]
    ) -> str:
        """Build execution command based on action type."""
        action_handlers = {
            "restart": self._build_restart_command,
            "scale": self._build_scale_command,
            "deploy": self._build_deploy_command,
            "delete": self._build_delete_command,
            "patch": self._build_patch_command,
            "exec": self._build_exec_command,
            "logs": self._build_logs_command,
            "describe": self._build_describe_command,
        }

        handler = action_handlers.get(action.lower())
        if handler:
            return handler(target, parameters)

        # Default: treat as custom command
        return f"echo 'Unknown action: {action}'"

    def _build_restart_command(self, target: str, parameters: Dict[str, Any]) -> str:
        """Build restart command."""
        namespace = parameters.get("namespace", "default")
        resource_type = parameters.get("resource_type", "deployment")
        return f"kubectl rollout restart {resource_type} {target} -n {namespace}"

    def _build_scale_command(self, target: str, parameters: Dict[str, Any]) -> str:
        """Build scale command."""
        namespace = parameters.get("namespace", "default")
        replicas = parameters.get("replicas", 1)
        resource_type = parameters.get("resource_type", "deployment")
        return f"kubectl scale {resource_type} {target} --replicas={replicas} -n {namespace}"

    def _build_deploy_command(self, target: str, parameters: Dict[str, Any]) -> str:
        """Build deploy command."""
        namespace = parameters.get("namespace", "default")
        image = parameters.get("image", target)
        return f"kubectl set image deployment/{target} {target}={image} -n {namespace}"

    def _build_delete_command(self, target: str, parameters: Dict[str, Any]) -> str:
        """Build delete command."""
        namespace = parameters.get("namespace", "default")
        resource_type = parameters.get("resource_type", "pod")
        return f"kubectl delete {resource_type} {target} -n {namespace}"

    def _build_patch_command(self, target: str, parameters: Dict[str, Any]) -> str:
        """Build patch command."""
        namespace = parameters.get("namespace", "default")
        patch = parameters.get("patch", "")
        resource_type = parameters.get("resource_type", "deployment")
        return f"kubectl patch {resource_type} {target} -n {namespace} -p '{patch}'"

    def _build_exec_command(self, target: str, parameters: Dict[str, Any]) -> str:
        """Build exec command."""
        namespace = parameters.get("namespace", "default")
        command = parameters.get("command", "sh")
        container = parameters.get("container", "")
        container_flag = f" -c {container}" if container else ""
        return f"kubectl exec {target} -n {namespace}{container_flag} -- {command}"

    def _build_logs_command(self, target: str, parameters: Dict[str, Any]) -> str:
        """Build logs command."""
        namespace = parameters.get("namespace", "default")
        container = parameters.get("container", "")
        tail = parameters.get("tail", 100)
        container_flag = f" -c {container}" if container else ""
        return f"kubectl logs {target} -n {namespace}{container_flag} --tail={tail}"

    def _build_describe_command(self, target: str, parameters: Dict[str, Any]) -> str:
        """Build describe command."""
        namespace = parameters.get("namespace", "default")
        resource_type = parameters.get("resource_type", "pod")
        return f"kubectl describe {resource_type} {target} -n {namespace}"

    def _parse_resources_modified(self, output: str) -> List[Dict[str, Any]]:
        """Parse output to identify modified resources."""
        # Simple parsing - can be enhanced based on actual output formats
        resources = []
        lines = output.split("\n")
        for line in lines:
            if "deployment.apps" in line or "pod" in line:
                parts = line.split()
                if len(parts) >= 2:
                    resources.append(
                        {
                            "type": parts[0] if parts[0] else "unknown",
                            "name": parts[1] if len(parts) > 1 else "unknown",
                            "action": "modified",
                        }
                    )
        return resources
