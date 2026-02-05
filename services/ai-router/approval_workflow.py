"""
Action approval workflow for human-in-the-loop operations.
Manages approval requests, risk assessment, and audit logging.
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import structlog

from conversation_models import (
    ActionApproval,
    ApprovalStatus,
    RiskLevel,
)

logger = structlog.get_logger()


class ApprovalWorkflow:
    """Manage action approvals for infrastructure operations."""

    def __init__(self, redis_url: str, postgres_url: str):
        """Initialize approval workflow manager.

        Args:
            redis_url: Redis connection URL for caching
            postgres_url: PostgreSQL connection URL
        """
        self.redis_url = redis_url
        self.postgres_url = postgres_url
        self._redis = None
        self._pg_pool = None

    async def _get_redis(self):
        """Get Redis connection."""
        import redis.asyncio as redis

        if self._redis is None:
            self._redis = await redis.from_url(
                self.redis_url, encoding="utf-8", decode_responses=True
            )
        return self._redis

    def _calculate_expiration(self, risk_level: RiskLevel) -> datetime:
        """Calculate approval expiration based on risk level."""
        expiration_map = {
            RiskLevel.LOW: timedelta(hours=24),
            RiskLevel.MEDIUM: timedelta(hours=8),
            RiskLevel.HIGH: timedelta(hours=4),
            RiskLevel.CRITICAL: timedelta(hours=1),
        }
        return datetime.utcnow() + expiration_map.get(risk_level, timedelta(hours=8))

    async def create_approval(
        self,
        conversation_id: str,
        user_id: str,
        action_type: str,
        target_resources: List[str],
        description: str,
        risk_level: RiskLevel,
        impact_summary: str,
        rollback_plan: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ActionApproval:
        """Create a new approval request.

        Args:
            conversation_id: Related conversation ID
            user_id: Requesting user
            action_type: Type of action
            target_resources: Target resource names
            description: Human-readable description
            risk_level: Risk assessment level
            impact_summary: Expected impact description
            rollback_plan: Optional rollback instructions
            metadata: Additional metadata

        Returns:
            Created approval request
        """
        approval_id = str(uuid.uuid4())
        expires_at = self._calculate_expiration(risk_level)

        approval = ActionApproval(
            id=approval_id,
            conversation_id=conversation_id,
            user_id=user_id,
            action_type=action_type,
            target_resources=target_resources,
            description=description,
            risk_level=risk_level,
            impact_summary=impact_summary,
            rollback_plan=rollback_plan,
            status=ApprovalStatus.PENDING,
            expires_at=expires_at,
            metadata=metadata or {},
        )

        # Store in Redis for quick access
        redis_client = await self._get_redis()
        await redis_client.setex(
            f"approval:{approval_id}",
            int((expires_at - datetime.utcnow()).total_seconds()),
            approval.model_dump_json(),
        )

        # Also index by conversation for lookup
        await redis_client.sadd(
            f"conversation_approvals:{conversation_id}", approval_id
        )

        logger.info(
            "approval_created",
            approval_id=approval_id,
            conversation_id=conversation_id,
            risk_level=risk_level.value,
            action_type=action_type,
        )

        return approval

    async def get_approval(self, approval_id: str) -> Optional[ActionApproval]:
        """Retrieve an approval request by ID.

        Args:
            approval_id: Approval request ID

        Returns:
            Approval request or None if not found
        """
        redis_client = await self._get_redis()
        data = await redis_client.get(f"approval:{approval_id}")

        if data:
            return ActionApproval.model_validate_json(data)

        return None

    async def get_conversation_approvals(
        self, conversation_id: str
    ) -> List[ActionApproval]:
        """Get all approval requests for a conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            List of approval requests
        """
        redis_client = await self._get_redis()
        approval_ids = await redis_client.smembers(
            f"conversation_approvals:{conversation_id}"
        )

        approvals = []
        for aid in approval_ids:
            approval = await self.get_approval(aid)
            if approval:
                approvals.append(approval)

        return approvals

    async def approve(
        self,
        approval_id: str,
        approver_id: str,
        reason: Optional[str] = None,
    ) -> Optional[ActionApproval]:
        """Approve an action request.

        Args:
            approval_id: Approval request ID
            approver_id: Approving user
            reason: Optional approval reason

        Returns:
            Updated approval request or None if not found
        """
        approval = await self.get_approval(approval_id)
        if not approval:
            return None

        if approval.status != ApprovalStatus.PENDING:
            logger.warning(
                "approval_already_processed",
                approval_id=approval_id,
                status=approval.status.value,
            )
            return approval

        # Check expiration
        if datetime.utcnow() > approval.expires_at:
            approval.status = ApprovalStatus.EXPIRED
            await self._update_approval(approval)
            logger.info("approval_expired", approval_id=approval_id)
            return approval

        approval.status = ApprovalStatus.APPROVED
        approval.approver_id = approver_id
        approval.approved_at = datetime.utcnow()

        await self._update_approval(approval)

        logger.info(
            "approval_granted",
            approval_id=approval_id,
            approver_id=approver_id,
            reason=reason,
        )

        return approval

    async def reject(
        self,
        approval_id: str,
        approver_id: str,
        reason: str,
    ) -> Optional[ActionApproval]:
        """Reject an action request.

        Args:
            approval_id: Approval request ID
            approver_id: Rejecting user
            reason: Rejection reason

        Returns:
            Updated approval request or None if not found
        """
        approval = await self.get_approval(approval_id)
        if not approval:
            return None

        if approval.status != ApprovalStatus.PENDING:
            logger.warning(
                "approval_already_processed",
                approval_id=approval_id,
                status=approval.status.value,
            )
            return approval

        approval.status = ApprovalStatus.REJECTED
        approval.approver_id = approver_id
        approval.rejected_at = datetime.utcnow()
        approval.rejection_reason = reason

        await self._update_approval(approval)

        logger.info(
            "approval_denied",
            approval_id=approval_id,
            approver_id=approver_id,
            reason=reason,
        )

        return approval

    async def cancel(self, approval_id: str, user_id: str) -> bool:
        """Cancel an approval request (by requester).

        Args:
            approval_id: Approval request ID
            user_id: User cancelling

        Returns:
            True if cancelled, False otherwise
        """
        approval = await self.get_approval(approval_id)
        if not approval:
            return False

        if approval.user_id != user_id:
            logger.warning(
                "approval_cancel_unauthorized",
                approval_id=approval_id,
                user_id=user_id,
            )
            return False

        # Mark as expired/cancelled
        approval.status = ApprovalStatus.EXPIRED
        await self._update_approval(approval)

        logger.info("approval_cancelled", approval_id=approval_id, user_id=user_id)
        return True

    async def _update_approval(self, approval: ActionApproval):
        """Update approval in storage."""
        redis_client = await self._get_redis()
        remaining = int((approval.expires_at - datetime.utcnow()).total_seconds())
        if remaining > 0:
            await redis_client.setex(
                f"approval:{approval.id}",
                remaining,
                approval.model_dump_json(),
            )

    async def list_pending(self, limit: int = 50) -> List[ActionApproval]:
        """List all pending approvals.

        Args:
            limit: Maximum results to return

        Returns:
            List of pending approval requests
        """
        redis_client = await self._get_redis()
        pattern = "approval:*"
        keys = []

        async for key in redis_client.scan_iter(match=pattern, count=100):
            keys.append(key)
            if len(keys) >= limit * 2:  # Get extra for filtering
                break

        approvals = []
        for key in keys[:limit]:
            data = await redis_client.get(key)
            if data:
                approval = ActionApproval.model_validate_json(data)
                if approval.status == ApprovalStatus.PENDING:
                    approvals.append(approval)

        return approvals

    async def cleanup_expired(self) -> int:
        """Clean up expired approval requests.

        Returns:
            Number of expired approvals cleaned
        """
        redis_client = await self._get_redis()
        pattern = "approval:*"
        expired_count = 0

        async for key in redis_client.scan_iter(match=pattern, count=100):
            data = await redis_client.get(key)
            if data:
                approval = ActionApproval.model_validate_json(data)
                if (
                    approval.status == ApprovalStatus.PENDING
                    and datetime.utcnow() > approval.expires_at
                ):
                    approval.status = ApprovalStatus.EXPIRED
                    await redis_client.setex(
                        key,
                        3600,  # Keep expired for 1 hour for audit
                        approval.model_dump_json(),
                    )
                    expired_count += 1

        logger.info("cleanup_expired_approvals", count=expired_count)
        return expired_count


class RiskAssessor:
    """Assess risk levels for infrastructure actions."""

    # High-risk action patterns
    CRITICAL_ACTIONS = {
        "delete": ["cluster", "namespace", "persistentvolume", "node"],
        "force_delete": ["pod", "deployment"],
        "stop": ["node", "cluster"],
    }

    # Moderate-risk patterns
    HIGH_ACTIONS = {
        "restart": ["deployment", "statefulset"],
        "scale": ["deployment"],
        "patch": ["deployment", "service"],
        "update": ["configmap", "secret"],
    }

    def assess(
        self,
        action_type: str,
        target_resources: List[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> RiskLevel:
        """Assess risk level for an action.

        Args:
            action_type: Type of action
            target_resources: Target resource names
            context: Additional context

        Returns:
            Risk level assessment
        """
        action_lower = action_type.lower()

        # Check for critical actions
        if action_lower in self.CRITICAL_ACTIONS:
            critical_targets = self.CRITICAL_ACTIONS[action_lower]
            for resource in target_resources:
                for target in critical_targets:
                    if target in resource.lower():
                        return RiskLevel.CRITICAL

        # Check for high-risk actions
        if action_lower in self.HIGH_ACTIONS:
            high_targets = self.HIGH_ACTIONS[action_lower]
            for resource in target_resources:
                for target in high_targets:
                    if target in resource.lower():
                        return RiskLevel.HIGH

        # Check for bulk operations
        if len(target_resources) > 5:
            if action_lower in ["delete", "restart", "scale"]:
                return RiskLevel.HIGH

        # Default to medium for unknown actions
        return RiskLevel.MEDIUM

    def requires_approval(self, risk_level: RiskLevel) -> bool:
        """Determine if action requires approval based on risk.

        Args:
            risk_level: Assessed risk level

        Returns:
            True if approval is required
        """
        return risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]

    def get_impact_summary(
        self,
        action_type: str,
        target_resources: List[str],
        risk_level: RiskLevel,
    ) -> str:
        """Generate impact summary for approval request.

        Args:
            action_type: Type of action
            target_resources: Target resources
            risk_level: Assessed risk

        Returns:
            Human-readable impact summary
        """
        resource_count = len(target_resources)

        impact_parts = [
            f"This action will {action_type} {resource_count} resource(s).",
        ]

        if risk_level == RiskLevel.CRITICAL:
            impact_parts.append(
                "⚠️ CRITICAL: This operation may cause service disruption."
            )
            impact_parts.append("Recommended: Notify stakeholders before proceeding.")
        elif risk_level == RiskLevel.HIGH:
            impact_parts.append(
                "⚠️ HIGH: This operation may cause temporary service interruption."
            )
        elif risk_level == RiskLevel.MEDIUM:
            impact_parts.append("This operation has moderate impact.")
        else:
            impact_parts.append("This operation has low impact.")

        return " ".join(impact_parts)
