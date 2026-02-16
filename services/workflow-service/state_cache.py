"""
Redis State Cache for Workflow Service

Provides Redis-backed workflow state caching for fast state queries.
Replaces in-memory storage with distributed Redis cache.
"""

import json
import redis
from typing import Any, Dict, List, Optional
from datetime import datetime


class RedisStateCache:
    """Redis-based workflow state caching."""

    def __init__(self, redis_client: redis.Redis, ttl: int = 86400):
        """Initialize the Redis state cache.

        Args:
            redis_client: Redis client instance
            ttl: Default TTL in seconds (default: 24 hours)
        """
        self.redis = redis_client
        self.prefix = "workflow:state:"
        self.ttl = ttl

    def _key(self, workflow_id: str, execution_id: str) -> str:
        """Generate cache key for workflow execution state."""
        return f"{self.prefix}{workflow_id}:{execution_id}"

    async def set_execution_state(
        self,
        workflow_id: str,
        execution_id: str,
        state: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> None:
        """Cache execution state.

        Args:
            workflow_id: Workflow identifier
            execution_id: Execution identifier
            state: State dictionary to cache
            ttl: Optional TTL override in seconds
        """
        key = self._key(workflow_id, execution_id)
        state["cached_at"] = datetime.utcnow().isoformat()
        self.redis.setex(key, ttl or self.ttl, json.dumps(state))

    async def get_execution_state(
        self, workflow_id: str, execution_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached execution state.

        Args:
            workflow_id: Workflow identifier
            execution_id: Execution identifier

        Returns:
            Cached state dictionary or None if not found
        """
        key = self._key(workflow_id, execution_id)
        data: Optional[bytes] = self.redis.get(key)  # type: ignore[assignment]
        if data:
            return json.loads(data)
        return None

    async def update_step_status(
        self,
        workflow_id: str,
        execution_id: str,
        step_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> None:
        """Update step status in cached state.

        Args:
            workflow_id: Workflow identifier
            execution_id: Execution identifier
            step_id: Step identifier to update
            status: New status value
            result: Optional step result data
            error: Optional error message
        """
        state = await self.get_execution_state(workflow_id, execution_id)
        if state and "steps" in state:
            for step in state["steps"]:
                if step["id"] == step_id:
                    step["status"] = status
                    step["updated_at"] = datetime.utcnow().isoformat()
                    if result:
                        step["result"] = result
                    if error:
                        step["error"] = error
                    break
            await self.set_execution_state(workflow_id, execution_id, state)

    async def increment_progress(
        self, workflow_id: str, execution_id: str, completed_steps: int
    ) -> None:
        """Increment completed steps counter.

        Args:
            workflow_id: Workflow identifier
            execution_id: Execution identifier
            completed_steps: Number of completed steps
        """
        state = await self.get_execution_state(workflow_id, execution_id)
        if state:
            state["completed_steps"] = completed_steps
            if state.get("total_steps", 0) > 0:
                state["progress_percent"] = int(
                    (completed_steps / state["total_steps"]) * 100
                )
            await self.set_execution_state(workflow_id, execution_id, state)

    async def delete_execution_state(self, workflow_id: str, execution_id: str) -> None:
        """Delete cached execution state.

        Args:
            workflow_id: Workflow identifier
            execution_id: Execution identifier
        """
        key = self._key(workflow_id, execution_id)
        self.redis.delete(key)

    async def get_all_execution_ids(self, workflow_id: str) -> List[str]:
        """Get all execution IDs for a workflow.

        Args:
            workflow_id: Workflow identifier

        Returns:
            List of execution IDs
        """
        pattern = f"{self.prefix}{workflow_id}:*"
        keys: List[str] = self.redis.keys(pattern)  # type: ignore[assignment]
        execution_ids = []
        for key in keys:
            # Extract execution_id from key (format: prefix:workflow_id:execution_id)
            parts = key.split(":")
            if len(parts) >= 4:
                execution_ids.append(parts[-1])
        return execution_ids
