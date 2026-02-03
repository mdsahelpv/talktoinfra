"""
Rollback Manager module.
Manages rollback points and executes rollback operations.
"""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from models import RollbackResult, ActionResponse
from config import get_settings

logger = structlog.get_logger()


class RollbackManager:
    """Manages rollback operations and points."""

    def __init__(self):
        self.settings = get_settings()
        # In-memory storage - replace with database in production
        self.rollback_points: Dict[str, Dict[str, Any]] = {}

    async def create_rollback_point(self, action: ActionResponse) -> Dict[str, Any]:
        """Create a rollback point before executing an action."""
        rollback_id = f"rb-{action.action_id}"

        logger.info(
            "creating_rollback_point",
            action_id=action.action_id,
            rollback_id=rollback_id,
        )

        try:
            # Capture current state
            current_state = await self._capture_state(action.target, action.parameters)

            rollback_point = {
                "id": rollback_id,
                "action_id": action.action_id,
                "created_at": datetime.utcnow().isoformat(),
                "target": action.target,
                "action_type": action.action,
                "original_state": current_state,
                "parameters": action.parameters,
            }

            self.rollback_points[rollback_id] = rollback_point

            # Cleanup old rollback points
            await self._cleanup_old_rollback_points()

            logger.info(
                "rollback_point_created",
                rollback_id=rollback_id,
                action_id=action.action_id,
            )

            return rollback_point

        except Exception as e:
            logger.error(
                "rollback_point_creation_failed",
                action_id=action.action_id,
                error=str(e),
            )
            raise

    async def rollback(
        self,
        rollback_point_id: str,
        action: Optional[ActionResponse] = None,
    ) -> RollbackResult:
        """Execute rollback from a rollback point."""
        start_time = time.time()

        if rollback_point_id not in self.rollback_points:
            return RollbackResult(
                success=False,
                rollback_point_id=rollback_point_id,
                restored_resources=[],
                errors=["Rollback point not found or expired"],
                duration_seconds=0,
            )

        rollback_point = self.rollback_points[rollback_point_id]

        logger.info(
            "rollback_started",
            rollback_point_id=rollback_point_id,
            action_id=rollback_point.get("action_id"),
        )

        errors: List[str] = []
        restored_resources: List[Dict[str, Any]] = []

        try:
            # Restore original state based on action type
            action_type = rollback_point.get("action_type", "unknown")
            original_state = rollback_point.get("original_state", {})
            target = rollback_point.get("target", "")
            parameters = rollback_point.get("parameters", {})

            if action_type in ["scale", "deploy", "patch"]:
                # Restore replica count or image
                restored = await self._restore_deployment_state(
                    target, parameters, original_state
                )
                restored_resources.extend(restored)

            elif action_type == "delete":
                # Recreate deleted resource
                restored = await self._recreate_resource(
                    target, parameters, original_state
                )
                restored_resources.extend(restored)

            else:
                errors.append(
                    f"Rollback for action type '{action_type}' not fully implemented"
                )

            duration = time.time() - start_time

            success = len(errors) == 0

            logger.info(
                "rollback_completed",
                rollback_point_id=rollback_point_id,
                success=success,
                resources_restored=len(restored_resources),
            )

            return RollbackResult(
                success=success,
                rollback_point_id=rollback_point_id,
                restored_resources=restored_resources,
                errors=errors,
                duration_seconds=duration,
            )

        except Exception as e:
            logger.error("rollback_failed", error=str(e))
            return RollbackResult(
                success=False,
                rollback_point_id=rollback_point_id,
                restored_resources=restored_resources,
                errors=errors + [str(e)],
                duration_seconds=time.time() - start_time,
            )

    async def _capture_state(
        self, target: str, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Capture current state of target resource."""
        namespace = parameters.get("namespace", "default")
        resource_type = parameters.get("resource_type", "deployment")

        # In production, this would make actual API calls to capture state
        # For now, simulate state capture
        return {
            "namespace": namespace,
            "resource_type": resource_type,
            "name": target,
            "spec": {
                "replicas": 3,  # Would be fetched from actual resource
                "template": {
                    "spec": {
                        "containers": [{"name": target, "image": "current-image:tag"}]
                    }
                },
            },
            "captured_at": datetime.utcnow().isoformat(),
        }

    async def _restore_deployment_state(
        self,
        target: str,
        parameters: Dict[str, Any],
        original_state: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Restore deployment to original state."""
        namespace = parameters.get("namespace", "default")

        # In production, this would apply the original state
        restored = [
            {
                "type": "deployment",
                "name": target,
                "namespace": namespace,
                "action": "restored",
                "state": original_state,
            }
        ]

        logger.info(
            "deployment_state_restored",
            target=target,
            namespace=namespace,
        )

        return restored

    async def _recreate_resource(
        self,
        target: str,
        parameters: Dict[str, Any],
        original_state: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Recreate a deleted resource."""
        namespace = parameters.get("namespace", "default")

        restored = [
            {
                "type": parameters.get("resource_type", "pod"),
                "name": target,
                "namespace": namespace,
                "action": "recreated",
                "state": original_state,
            }
        ]

        logger.info(
            "resource_recreated",
            target=target,
            namespace=namespace,
        )

        return restored

    async def _cleanup_old_rollback_points(self):
        """Remove expired rollback points."""
        max_points = self.settings.max_rollback_points
        retention_hours = self.settings.rollback_retention_hours

        if len(self.rollback_points) <= max_points:
            return

        # Sort by creation time
        sorted_points = sorted(
            self.rollback_points.items(),
            key=lambda x: x[1].get("created_at", ""),
        )

        # Remove oldest points exceeding max
        to_remove = len(sorted_points) - max_points
        for i in range(to_remove):
            rollback_id = sorted_points[i][0]
            del self.rollback_points[rollback_id]
            logger.info("old_rollback_point_removed", rollback_id=rollback_id)

    def get_rollback_point(self, rollback_id: str) -> Optional[Dict[str, Any]]:
        """Get a rollback point by ID."""
        return self.rollback_points.get(rollback_id)

    def list_rollback_points(
        self, action_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List rollback points, optionally filtered by action."""
        points = list(self.rollback_points.values())

        if action_id:
            points = [p for p in points if p.get("action_id") == action_id]

        return points
