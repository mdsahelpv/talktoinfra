"""
Safety validation engine for Agent Service.
Zero-trust approach: everything is dangerous until proven safe.
"""

import fnmatch
import structlog
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from ..app.config import Settings
from ..models import (
    SafetyResult,
    RiskLevel,
    Approval,
    ApprovalStatus,
)
from .audit_logger import AuditLogger

logger = structlog.get_logger()


class SafetyEngine:
    """
    Validates all actions before execution.
    Production-ready safety with mandatory approval gates.
    """

    def __init__(
        self, settings: Settings, db_session: AsyncSession, audit_logger: AuditLogger
    ):
        self.settings = settings
        self.db = db_session
        self.audit = audit_logger

        # Load blocked operations from config
        self.blocked_operations = settings.get_blocked_operations()
        self.high_risk_resources = settings.get_high_risk_resources()

        # Cache for user preferences (loaded on first use)
        self._user_prefs_cache = {}

    async def validate(
        self, action: Dict[str, Any], context: Dict[str, Any]
    ) -> SafetyResult:
        """
        Validate an action for safety.
        Returns SafetyResult with approval requirements.
        """
        checks_performed = []
        warnings = []

        # 1. Check if operation is blocked
        operation = (
            f"{action.get('tool', 'unknown')}.{action.get('operation', 'unknown')}"
        )
        if operation in self.blocked_operations:
            await self.audit.log_safety_violation(
                action=action, context=context, reason=f"Blocked operation: {operation}"
            )
            return SafetyResult(
                allowed=False,
                risk_level=RiskLevel.CRITICAL,
                requires_approval=False,
                reason=f"Operation '{operation}' is permanently blocked",
                checks_performed=["blocked_operations_check"],
                warnings=["Attempted blocked operation"],
            )
        checks_performed.append("blocked_operations_check")

        # 2. Check tool risk level
        tool_risk = await self.get_tool_risk_level(action.get("tool"))
        checks_performed.append("tool_risk_check")

        # 3. Check target resource
        target = action.get("target", "") or action.get("parameters", {}).get(
            "name", ""
        )
        is_high_risk_resource = self.is_high_risk_resource(target)
        if is_high_risk_resource:
            warnings.append(f"Target '{target}' matches high-risk pattern")
        checks_performed.append("resource_risk_check")

        # 4. Check environment
        environment = context.get("environment", "development")
        if environment == "production":
            warnings.append("Operating in production environment")
        checks_performed.append("environment_check")

        # 5. Check namespace restrictions
        namespace = action.get("parameters", {}).get("namespace", "default")
        namespace_check = self.check_namespace_restrictions(
            action.get("tool"), namespace
        )
        if not namespace_check[0]:
            return SafetyResult(
                allowed=False,
                risk_level=RiskLevel.CRITICAL,
                requires_approval=False,
                reason=namespace_check[1],
                checks_performed=["namespace_check"],
            )
        checks_performed.append("namespace_check")

        # 6. Calculate final risk level
        risk_level = self.calculate_risk(
            tool_risk=tool_risk,
            is_high_risk_resource=is_high_risk_resource,
            environment=environment,
            action_type=action.get("type", "unknown"),
        )
        checks_performed.append("risk_calculation")

        # 7. Determine approval requirements
        requires_approval, approvers = await self.determine_approval_requirements(
            risk_level=risk_level,
            user_id=context.get("user_id"),
            environment=environment,
            action=action,
            tool_name=action.get("tool", "unknown"),
        )
        checks_performed.append("approval_requirements_check")

        # 8. Always require dry-run for non-read-only
        dry_run_required = risk_level != RiskLevel.READ_ONLY

        # 9. Log safety check
        await self.audit.log_safety_check(
            action=action,
            context=context,
            result=SafetyResult(
                allowed=True,
                risk_level=risk_level,
                requires_approval=requires_approval,
                reason=None,
                approvers=approvers,
                requires_justification=risk_level
                in [RiskLevel.HIGH, RiskLevel.CRITICAL],
                dry_run_required=dry_run_required,
                checks_performed=checks_performed,
                warnings=warnings,
            ),
        )

        return SafetyResult(
            allowed=True,
            risk_level=risk_level,
            requires_approval=requires_approval,
            approvers=approvers,
            requires_justification=risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL],
            dry_run_required=dry_run_required,
            checks_performed=checks_performed,
            warnings=warnings,
        )

    async def get_tool_risk_level(self, tool_name: Optional[str]) -> RiskLevel:
        """Get risk level for a tool."""
        if not tool_name:
            return RiskLevel.HIGH  # Unknown = risky

        # Tool name patterns for risk assessment
        read_patterns = ["get", "list", "describe", "read", "search", "query"]
        write_patterns = ["create", "update", "patch", "write", "apply"]
        delete_patterns = ["delete", "remove", "terminate", "destroy"]
        critical_patterns = ["delete_namespace", "delete_all", "terminate_all"]

        tool_lower = tool_name.lower()

        # Check for critical operations first
        if any(pattern in tool_lower for pattern in critical_patterns):
            return RiskLevel.CRITICAL

        # Check for delete operations
        if any(pattern in tool_lower for pattern in delete_patterns):
            return RiskLevel.HIGH

        # Check for write operations
        if any(pattern in tool_lower for pattern in write_patterns):
            return RiskLevel.MEDIUM

        # Check for read operations
        if any(pattern in tool_lower for pattern in read_patterns):
            return RiskLevel.READ_ONLY

        # Default to medium risk for unknown tools
        return RiskLevel.MEDIUM

    def is_high_risk_resource(self, target: str) -> bool:
        """Check if target matches high-risk resource patterns."""
        if not target:
            return False

        for pattern in self.high_risk_resources:
            if fnmatch.fnmatch(target, pattern):
                return True
        return False

    def check_namespace_restrictions(
        self, tool: Optional[str], namespace: str
    ) -> Tuple[bool, Optional[str]]:
        """Check if operation is allowed in namespace."""
        # Block operations in protected namespaces
        protected = ["kube-system", "kube-public", "kube-node-lease"]

        if namespace in protected and tool and "write" in tool.lower():
            return (
                False,
                f"Write operations not allowed in protected namespace: {namespace}",
            )

        return True, None

    def calculate_risk(
        self,
        tool_risk: RiskLevel,
        is_high_risk_resource: bool,
        environment: str,
        action_type: str,
    ) -> RiskLevel:
        """Calculate final risk level based on multiple factors."""
        # Start with tool risk
        risk = tool_risk

        # Upgrade risk for high-risk resources
        if is_high_risk_resource:
            if risk == RiskLevel.READ_ONLY:
                risk = RiskLevel.LOW
            elif risk == RiskLevel.LOW:
                risk = RiskLevel.MEDIUM
            elif risk == RiskLevel.MEDIUM:
                risk = RiskLevel.HIGH

        # Upgrade risk for production environment
        if environment == "production":
            if risk == RiskLevel.READ_ONLY:
                pass  # Read-only is still safe
            elif risk == RiskLevel.LOW:
                risk = RiskLevel.MEDIUM
            elif risk == RiskLevel.MEDIUM:
                risk = RiskLevel.HIGH
            elif risk == RiskLevel.HIGH:
                risk = RiskLevel.CRITICAL

        # Deletions are always at least MEDIUM
        if action_type == "delete" and risk == RiskLevel.READ_ONLY:
            risk = RiskLevel.MEDIUM

        return risk

    async def determine_approval_requirements(
        self,
        risk_level: RiskLevel,
        user_id: str,
        environment: str,
        action: Dict[str, Any],
        tool_name: str,
    ) -> Tuple[bool, Optional[List[str]]]:
        """Determine if approval is required and who should approve."""
        # Read-only: no approval needed
        if risk_level == RiskLevel.READ_ONLY:
            return False, None

        # Check user preferences for auto-approval in non-production
        if environment != "production":
            user_prefs = await self.get_user_preferences(user_id)

            if risk_level == RiskLevel.LOW and user_prefs.get(
                "auto_approve_low_risk", False
            ):
                return False, None

            if risk_level == RiskLevel.MEDIUM and user_prefs.get(
                "auto_approve_medium_risk", False
            ):
                return False, None

        # Production environment: always require approval for modifications
        if environment == "production" and risk_level != RiskLevel.READ_ONLY:
            approvers = await self.get_production_approvers(user_id, action)
            return True, approvers

        # High/Critical risk: always require approval
        if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            approvers = await self.get_high_risk_approvers(user_id, action)
            return True, approvers

        # Default: require approval
        return True, [await self.get_team_lead(user_id)]

    async def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user preferences for auto-approval settings."""
        # In production, load from database or cache
        # For now, use defaults
        return {
            "auto_approve_low_risk": False,
            "auto_approve_medium_risk": False,
        }

    async def get_production_approvers(
        self, user_id: str, action: Dict[str, Any]
    ) -> List[str]:
        """Get approvers for production changes."""
        # In production, query from Policy Engine or user database
        # Return list of user IDs who can approve
        return ["team-lead", "on-call-engineer", "sre-manager"]

    async def get_high_risk_approvers(
        self, user_id: str, action: Dict[str, Any]
    ) -> List[str]:
        """Get approvers for high-risk changes."""
        return ["sre-manager", "platform-lead"]

    async def get_team_lead(self, user_id: str) -> str:
        """Get team lead for user."""
        # In production, query from org chart or user database
        return "team-lead"

    async def create_approval_request(
        self, task_id: str, step: Any, safety_result: SafetyResult
    ) -> Approval:
        """Create approval request in database."""
        approval = Approval(
            id=str(uuid.uuid4()),
            task_id=task_id,
            action_type=step.tool_name,
            dry_run_result={"preview": "Dry run results will be stored here"},
            requester_id="user_id",  # Get from context
            approvers=safety_result.approvers or ["team-lead"],
            status=ApprovalStatus.PENDING,
            expires_at=datetime.utcnow()
            + timedelta(seconds=self.settings.approval_timeout_seconds),
        )

        # Save to database
        from ..db.models import ApprovalModel

        db_approval = ApprovalModel(
            id=approval.id,
            task_id=approval.task_id,
            action_type=approval.action_type,
            dry_run_result=approval.dry_run_result,
            requester_id=approval.requester_id,
            approvers=approval.approvers,
            status=approval.status,
            expires_at=approval.expires_at,
        )

        self.db.add(db_approval)
        await self.db.commit()

        # Log
        logger.info(
            "approval_created",
            approval_id=approval.id,
            task_id=task_id,
            approvers=approval.approvers,
        )

        return approval

    async def wait_for_approval(
        self, approval_id: str, timeout: int = 3600
    ) -> Approval:
        """Wait for approval decision (blocking with timeout)."""
        from ..db.models import ApprovalModel

        start_time = datetime.utcnow()

        while True:
            # Check current status
            result = await self.db.execute(
                select(ApprovalModel).where(ApprovalModel.id == approval_id)
            )
            approval = result.scalar_one_or_none()

            if not approval:
                raise ValueError(f"Approval {approval_id} not found")

            if approval.status != ApprovalStatus.PENDING:
                return Approval(
                    id=approval.id,
                    task_id=approval.task_id,
                    status=approval.status,
                    approved_by=approval.approved_by,
                    approved_at=approval.approved_at,
                )

            # Check timeout
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            if elapsed > timeout:
                # Mark as expired
                await self.db.execute(
                    update(ApprovalModel)
                    .where(ApprovalModel.id == approval_id)
                    .values(status=ApprovalStatus.EXPIRED)
                )
                await self.db.commit()

                return Approval(
                    id=approval_id,
                    task_id=approval.task_id,
                    status=ApprovalStatus.EXPIRED,
                )

            # Wait before checking again
            await asyncio.sleep(1)


import uuid
import asyncio
