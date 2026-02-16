"""
Rollback Engine for Workflow Service

Provides step-level rollback handlers, execution history tracking,
and manual rollback triggers for workflow executions.
"""

import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

import structlog

logger = structlog.get_logger()


class RollbackStrategy(str, Enum):
    """Rollback strategies for workflow steps."""

    NONE = "none"  # No rollback
    MANUAL = "manual"  # Requires manual intervention
    AUTO = "auto"  # Automatic rollback
    COMPENSATE = "compensate"  # Run compensating action
    REVERT = "revert"  # Revert to previous state


class RollbackStatus(str, Enum):
    """Status of rollback operation."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class StepRollback:
    """Represents a rollback operation for a step."""

    def __init__(
        self,
        step_id: str,
        step_name: str,
        original_result: Dict[str, Any],
        rollback_action: Optional[str] = None,
        rollback_config: Optional[Dict[str, Any]] = None,
    ):
        self.step_id = step_id
        self.step_name = step_name
        self.original_result = original_result
        self.rollback_action = rollback_action
        self.rollback_config = rollback_config or {}
        self.status = RollbackStatus.PENDING
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None


class ExecutionHistory:
    """Tracks execution history for a workflow execution."""

    def __init__(self, execution_id: str, workflow_id: str):
        self.execution_id = execution_id
        self.workflow_id = workflow_id
        self.events: List[Dict[str, Any]] = []
        self.step_results: Dict[str, Dict[str, Any]] = {}
        self.rollback_history: List[Dict[str, Any]] = []
        self.created_at = datetime.utcnow().isoformat()

    def add_event(
        self,
        event_type: str,
        step_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add an event to the execution history.

        Args:
            event_type: Type of event
            step_id: Optional step ID
            data: Optional event data
        """
        event = {
            "event_type": event_type,
            "step_id": step_id,
            "data": data or {},
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.events.append(event)

    def record_step_result(
        self,
        step_id: str,
        result: Dict[str, Any],
    ) -> None:
        """Record step execution result.

        Args:
            step_id: Step ID
            result: Step result
        """
        self.step_results[step_id] = {
            "result": result,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def record_rollback(
        self,
        step_id: str,
        status: RollbackStatus,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> None:
        """Record rollback operation.

        Args:
            step_id: Step ID
            status: Rollback status
            result: Optional rollback result
            error: Optional error message
        """
        self.rollback_history.append({
            "step_id": step_id,
            "status": status,
            "result": result,
            "error": error,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "events": self.events,
            "step_results": self.step_results,
            "rollback_history": self.rollback_history,
            "created_at": self.created_at,
        }


class RollbackEngine:
    """Engine for executing rollbacks of workflow steps."""

    def __init__(self, action_engine_url: Optional[str] = None):
        """Initialize the rollback engine.

        Args:
            action_engine_url: URL of the action engine service
        """
        self.action_engine_url = action_engine_url or "http://localhost:8003"

    def get_rollback_handler(self, step_type: str) -> "StepRollbackHandler":
        """Get the appropriate rollback handler for a step type.

        Args:
            step_type: Type of workflow step

        Returns:
            Rollback handler instance
        """
        handlers = {
            "action": ActionRollbackHandler(self.action_engine_url),
            "deployment": DeploymentRollbackHandler(self.action_engine_url),
            "scale": ScaleRollbackHandler(self.action_engine_url),
            "notification": NotificationRollbackHandler(),
        }
        return handlers.get(step_type, DefaultRollbackHandler())

    async def execute_rollback(
        self,
        step: Dict[str, Any],
        original_result: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute rollback for a step.

        Args:
            step: Step configuration
            original_result: Original step execution result
            context: Execution context

        Returns:
            Rollback result
        """
        step_type = step.get("type", "action")
        handler = self.get_rollback_handler(step_type)

        rollback = StepRollback(
            step_id=step.get("id", ""),
            step_name=step.get("name", ""),
            original_result=original_result,
            rollback_action=step.get("rollback_action"),
            rollback_config=step.get("rollback_config", {}),
        )

        rollback.started_at = datetime.utcnow().isoformat()
        rollback.status = RollbackStatus.IN_PROGRESS

        logger.info(
            "rollback_started",
            step_id=rollback.step_id,
            step_name=rollback.step_name,
            action=rollback.rollback_action,
        )

        try:
            result = await handler.execute(rollback, original_result, context)
            rollback.status = RollbackStatus.COMPLETED
            rollback.result = result

            logger.info(
                "rollback_completed",
                step_id=rollback.step_id,
                result=result,
            )

            return {
                "status": "success",
                "step_id": rollback.step_id,
                "result": result,
            }

        except Exception as e:
            rollback.status = RollbackStatus.FAILED
            rollback.error = str(e)

            logger.error(
                "rollback_failed",
                step_id=rollback.step_id,
                error=str(e),
            )

            return {
                "status": "failed",
                "step_id": rollback.step_id,
                "error": str(e),
            }

        finally:
            rollback.completed_at = datetime.utcnow().isoformat()

    async def rollback_workflow(
        self,
        execution_id: str,
        workflow_id: str,
        steps: List[Dict[str, Any]],
        step_results: Dict[str, Dict[str, Any]],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Rollback entire workflow execution.

        Args:
            execution_id: Execution ID
            workflow_id: Workflow ID
            steps: List of workflow steps (in reverse order)
            step_results: Map of step IDs to their results
            context: Execution context

        Returns:
            Rollback summary
        """
        history = ExecutionHistory(execution_id, workflow_id)
        history.add_event("workflow_rollback_started")

        rollback_results: List[Dict[str, Any]] = []
        failed_rollbacks: List[str] = []

        # Rollback in reverse order
        for step in reversed(steps):
            step_id = step.get("id", "")
            step_result = step_results.get(step_id, {}).get("result", {})

            # Skip steps that didn't execute
            if not step_result:
                continue

            # Skip steps without rollback configuration
            if not step.get("rollback_action") and not step.get("on_failure") == "rollback":
                continue

            result = await self.execute_rollback(step, step_result, context)
            rollback_results.append(result)

            if result.get("status") == "failed":
                failed_rollbacks.append(step_id)

            history.record_rollback(
                step_id=step_id,
                status=RollbackStatus.COMPLETED if result.get(
                    "status") == "success" else RollbackStatus.FAILED,
                result=result,
            )

        history.add_event("workflow_rollback_completed")

        return {
            "execution_id": execution_id,
            "workflow_id": workflow_id,
            "total_steps_rolled_back": len(rollback_results),
            "failed_rollbacks": failed_rollbacks,
            "rollback_results": rollback_results,
            "history": history.to_dict(),
        }


class StepRollbackHandler:
    """Base class for step rollback handlers."""

    def __init__(self, action_engine_url: str):
        self.action_engine_url = action_engine_url

    async def execute(
        self,
        rollback: StepRollback,
        original_result: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute rollback operation.

        Args:
            rollback: Rollback configuration
            original_result: Original step result
            context: Execution context

        Returns:
            Rollback result
        """
        raise NotImplementedError


class ActionRollbackHandler(StepRollbackHandler):
    """Rollback handler for action steps."""

    async def execute(
        self,
        rollback: StepRollback,
        original_result: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute action rollback by calling action engine."""
        import httpx

        action_type = rollback.rollback_config.get("compensating_action")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.action_engine_url}/api/v1/rollback",
                json={
                    "action_type": action_type,
                    "original_parameters": rollback.original_result.get("parameters", {}),
                    "context": context,
                },
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()


class DeploymentRollbackHandler(StepRollbackHandler):
    """Rollback handler for deployment steps."""

    async def execute(
        self,
        rollback: StepRollback,
        original_result: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute deployment rollback."""
        import httpx

        deployment_name = rollback.original_result.get("deployment_name")
        namespace = rollback.original_result.get("namespace")
        previous_revision = rollback.rollback_config.get("previous_revision")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.action_engine_url}/api/v1/k8s/rollback-deployment",
                json={
                    "deployment_name": deployment_name,
                    "namespace": namespace,
                    "revision": previous_revision,
                },
                timeout=60.0,
            )
            response.raise_for_status()
            return response.json()


class ScaleRollbackHandler(StepRollbackHandler):
    """Rollback handler for scale steps."""

    async def execute(
        self,
        rollback: StepRollback,
        original_result: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute scale rollback."""
        import httpx

        resource_type = rollback.original_result.get("resource_type")
        resource_name = rollback.original_result.get("resource_name")
        namespace = rollback.original_result.get("namespace")
        previous_replicas = rollback.rollback_config.get(
            "previous_replicas", 1)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.action_engine_url}/api/v1/k8s/scale",
                json={
                    "resource_type": resource_type,
                    "resource_name": resource_name,
                    "namespace": namespace,
                    "replicas": previous_replicas,
                },
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()


class NotificationRollbackHandler(StepRollbackHandler):
    """Rollback handler for notification steps (no-op)."""

    async def execute(
        self,
        rollback: StepRollback,
        original_result: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Notification rollbacks are no-ops."""
        return {
            "status": "skipped",
            "message": "Notification rollbacks are not applicable",
        }


class DefaultRollbackHandler(StepRollbackHandler):
    """Default rollback handler for unknown step types."""

    async def execute(
        self,
        rollback: StepRollback,
        original_result: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Default rollback - log and skip."""
        logger.warning(
            "no_rollback_handler",
            step_type=rollback.rollback_config.get("step_type"),
        )
        return {
            "status": "skipped",
            "message": f"No rollback handler for step type",
        }


# Global rollback engine instance
_rollback_engine: Optional[RollbackEngine] = None


def get_rollback_engine(action_engine_url: Optional[str] = None) -> RollbackEngine:
    """Get or create the global rollback engine instance.

    Args:
        action_engine_url: Optional action engine URL

    Returns:
        RollbackEngine instance
    """
    global _rollback_engine
    if _rollback_engine is None:
        _rollback_engine = RollbackEngine(action_engine_url=action_engine_url)
    return _rollback_engine
