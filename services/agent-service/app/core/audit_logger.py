"""
Audit Logger for Agent Service.
Immutable audit trail with hash chaining for tamper detection.
"""

import hashlib
import json
import structlog
from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = structlog.get_logger()


class AuditLogger:
    """
    Structured audit logging with hash chain for tamper detection.
    All operations are logged for compliance.
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.logger = logger.bind(service="audit")

    async def log_task_created(self, task: Any) -> None:
        """Log task creation."""
        await self._log_event(
            event_type="task_created",
            task_id=task.id,
            user_id=task.user_id,
            agent_type=task.agent_type,
            details={
                "query": task.query,
                "environment": task.environment,
                "context_keys": list(task.context.keys()) if task.context else [],
            },
        )

    async def log_task_completed(self, task: Any, result: Any) -> None:
        """Log task completion."""
        await self._log_event(
            event_type="task_completed",
            task_id=task.id,
            user_id=task.user_id,
            agent_type=task.agent_type,
            success=result.success,
            details={
                "execution_time_ms": result.execution_time_ms,
                "steps_executed": (
                    len(result.step_results) if result.step_results else 0
                ),
                "error": result.error_message,
            },
        )

    async def log_task_failed(self, task: Any, error: str) -> None:
        """Log task failure."""
        await self._log_event(
            event_type="task_failed",
            task_id=task.id,
            user_id=task.user_id,
            agent_type=task.agent_type,
            success=False,
            details={"error": error},
        )

    async def log_tool_called(self, task_id: str, tool_call: Any) -> None:
        """Log tool execution."""
        await self._log_event(
            event_type="tool_called",
            task_id=task_id,
            details={
                "tool_name": tool_call.tool_name,
                "parameters": tool_call.parameters,
                "started_at": (
                    tool_call.started_at.isoformat() if tool_call.started_at else None
                ),
                "completed_at": (
                    tool_call.completed_at.isoformat()
                    if tool_call.completed_at
                    else None
                ),
                "success": tool_call.error is None,
            },
        )

    async def log_safety_check(self, action: Dict, context: Dict, result: Any) -> None:
        """Log safety validation."""
        await self._log_event(
            event_type="safety_check",
            task_id=context.get("task_id"),
            user_id=context.get("user_id"),
            details={
                "action": action,
                "risk_level": result.risk_level.value,
                "requires_approval": result.requires_approval,
                "allowed": result.allowed,
                "reason": result.reason,
                "checks_performed": result.checks_performed,
                "warnings": result.warnings,
            },
        )

    async def log_safety_violation(
        self, action: Dict, context: Dict, reason: str
    ) -> None:
        """Log blocked safety violation."""
        await self._log_event(
            event_type="safety_violation",
            task_id=context.get("task_id"),
            user_id=context.get("user_id"),
            success=False,
            details={"action": action, "violation_reason": reason, "blocked": True},
        )

    async def log_approval_requested(self, approval: Any) -> None:
        """Log approval request."""
        await self._log_event(
            event_type="approval_requested",
            task_id=approval.task_id,
            user_id=approval.requester_id,
            details={
                "approval_id": approval.id,
                "action_type": approval.action_type,
                "approvers": approval.approvers,
                "expires_at": approval.expires_at.isoformat(),
            },
        )

    async def log_approval_decision(
        self, approval: Any, decision: str, decided_by: str
    ) -> None:
        """Log approval decision."""
        await self._log_event(
            event_type=f"approval_{decision}",
            task_id=approval.task_id,
            user_id=decided_by,
            details={
                "approval_id": approval.id,
                "decision": decision,
                "previous_status": "pending",
                "notes": getattr(approval, "rejection_reason", None),
            },
        )

    async def log_agent_decision(
        self, task_id: str, agent_type: str, decision: Dict
    ) -> None:
        """Log agent decision with reasoning."""
        await self._log_event(
            event_type="agent_decision",
            task_id=task_id,
            agent_type=agent_type,
            details={
                "reasoning": decision.get("reasoning"),
                "alternatives_considered": decision.get("alternatives"),
                "confidence": decision.get("confidence"),
                "tools_selected": decision.get("tools_selected"),
            },
        )

    async def log_rollback_executed(
        self, task_id: str, checkpoint_id: str, reason: str
    ) -> None:
        """Log rollback execution."""
        await self._log_event(
            event_type="rollback_executed",
            task_id=task_id,
            details={
                "checkpoint_id": checkpoint_id,
                "rollback_reason": reason,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    async def _log_event(
        self,
        event_type: str,
        task_id: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_type: Optional[str] = None,
        success: bool = True,
        details: Dict[str, Any] = None,
    ) -> None:
        """
        Log event to database with hash chain for tamper detection.
        """
        from ..db.models import AuditEventModel

        # Get previous hash for chain
        previous_hash = await self._get_last_hash()

        # Prepare data
        event_data = {
            "event_type": event_type,
            "task_id": task_id,
            "user_id": user_id or "system",
            "agent_type": agent_type,
            "action": details.get("action", event_type) if details else event_type,
            "details": details or {},
            "success": success,
        }

        # Calculate hash
        data_hash = self._calculate_hash(event_data, previous_hash)

        # Create audit event
        audit_event = AuditEventModel(
            id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            event_type=event_type,
            task_id=task_id,
            user_id=user_id or "system",
            agent_type=agent_type,
            action=event_data["action"],
            details=event_data["details"],
            success=success,
            previous_hash=previous_hash,
            data_hash=data_hash,
        )

        # Save to database
        self.db.add(audit_event)
        await self.db.commit()

        # Also log to structured logger
        self.logger.info(
            "audit_event",
            event_type=event_type,
            task_id=task_id,
            user_id=user_id,
            success=success,
        )

    async def _get_last_hash(self) -> Optional[str]:
        """Get hash of last audit event for chain."""
        from ..db.models import AuditEventModel

        result = await self.db.execute(
            select(AuditEventModel).order_by(AuditEventModel.timestamp.desc()).limit(1)
        )
        last_event = result.scalar_one_or_none()

        return last_event.data_hash if last_event else None

    def _calculate_hash(self, data: Dict, previous_hash: Optional[str]) -> str:
        """Calculate SHA-256 hash of event data."""
        hash_input = {
            "data": data,
            "previous_hash": previous_hash,
            "timestamp": datetime.utcnow().isoformat(),
        }

        hash_str = json.dumps(hash_input, sort_keys=True)
        return hashlib.sha256(hash_str.encode()).hexdigest()

    async def verify_chain_integrity(self) -> bool:
        """
        Verify hash chain integrity for tamper detection.
        Returns True if chain is intact, False if tampering detected.
        """
        from ..db.models import AuditEventModel

        result = await self.db.execute(
            select(AuditEventModel).order_by(AuditEventModel.timestamp.asc())
        )
        events = result.scalars().all()

        previous_hash = None
        for event in events:
            # Recalculate hash
            event_data = {
                "event_type": event.event_type,
                "task_id": event.task_id,
                "user_id": event.user_id,
                "agent_type": event.agent_type,
                "action": event.action,
                "details": event.details,
                "success": event.success,
            }

            calculated_hash = self._calculate_hash(event_data, previous_hash)

            if calculated_hash != event.data_hash:
                logger.error(
                    "audit_chain_integrity_violation",
                    event_id=event.id,
                    expected_hash=calculated_hash,
                    actual_hash=event.data_hash,
                )
                return False

            previous_hash = event.data_hash

        return True


import uuid
