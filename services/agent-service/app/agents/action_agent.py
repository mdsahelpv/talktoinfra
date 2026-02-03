"""
Action Agent for infrastructure modifications.
ALWAYS requires dry-run + approval - NEVER auto-executes.
Implements strict safety controls for all infrastructure changes.
"""

import json
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import structlog

from app.tools.registry import ToolRegistry, get_registry
from app.tools.definitions import ToolDefinition

logger = structlog.get_logger()


class ActionStatus(str, Enum):
    """Status of an action execution."""

    PENDING = "pending"
    DRY_RUN = "dry_run"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    REJECTED = "rejected"


class RiskLevel(str, Enum):
    """Risk levels for actions."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ImpactAnalysis:
    """Analysis of action impact."""

    affected_resources: List[str]
    affected_services: List[str]
    potential_downtime: Optional[str]
    data_impact: str
    security_impact: str
    performance_impact: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "affected_resources": self.affected_resources,
            "affected_services": self.affected_services,
            "potential_downtime": self.potential_downtime,
            "data_impact": self.data_impact,
            "security_impact": self.security_impact,
            "performance_impact": self.performance_impact,
        }


@dataclass
class DryRunResult:
    """Result of dry-run execution."""

    success: bool
    would_succeed: bool
    changes_preview: List[Dict[str, Any]]
    warnings: List[str]
    errors: List[str]
    affected_resources: List[str]
    estimated_duration_seconds: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "would_succeed": self.would_succeed,
            "changes_preview": self.changes_preview,
            "warnings": self.warnings,
            "errors": self.errors,
            "affected_resources": self.affected_resources,
            "estimated_duration_seconds": self.estimated_duration_seconds,
        }


@dataclass
class RollbackCapability:
    """Information about rollback capability."""

    can_rollback: bool
    rollback_steps: List[Dict[str, Any]]
    rollback_window_seconds: int
    automatic_rollback_available: bool
    rollback_risks: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "can_rollback": self.can_rollback,
            "rollback_steps": self.rollback_steps,
            "rollback_window_seconds": self.rollback_window_seconds,
            "automatic_rollback_available": self.automatic_rollback_available,
            "rollback_risks": self.rollback_risks,
        }


@dataclass
class ActionResult:
    """Result of action execution."""

    action_id: str
    status: ActionStatus
    action: str
    target: str
    resource_type: str
    namespace: str

    # Dry-run phase
    dry_run_result: Optional[DryRunResult]
    dry_run_completed: bool

    # Approval phase
    requires_approval: bool
    approval_id: Optional[str]
    approved_by: Optional[str]
    approved_at: Optional[datetime]
    rejection_reason: Optional[str]

    # Execution phase
    execution_result: Optional[Dict[str, Any]]
    execution_error: Optional[str]
    execution_duration_seconds: Optional[int]

    # Impact analysis
    impact_analysis: ImpactAnalysis

    # Rollback
    rollback_capability: RollbackCapability
    rollback_executed: bool
    rollback_result: Optional[Dict[str, Any]]

    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "status": self.status.value,
            "action": self.action,
            "target": self.target,
            "resource_type": self.resource_type,
            "namespace": self.namespace,
            "dry_run_result": self.dry_run_result.to_dict()
            if self.dry_run_result
            else None,
            "dry_run_completed": self.dry_run_completed,
            "requires_approval": self.requires_approval,
            "approval_id": self.approval_id,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "rejection_reason": self.rejection_reason,
            "execution_result": self.execution_result,
            "execution_error": self.execution_error,
            "execution_duration_seconds": self.execution_duration_seconds,
            "impact_analysis": self.impact_analysis.to_dict(),
            "rollback_capability": self.rollback_capability.to_dict(),
            "rollback_executed": self.rollback_executed,
            "rollback_result": self.rollback_result,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
        }


class ActionAgent:
    """
    Action Agent for infrastructure modifications.

    CRITICAL SAFETY REQUIREMENTS:
    1. ALWAYS requires dry-run before execution
    2. ALWAYS requires human approval
    3. NEVER auto-executes
    4. Provides rollback capability
    5. Performs impact analysis

    This agent implements zero-trust for infrastructure changes:
    - Every action must pass dry-run validation
    - Every action requires explicit human approval
    - No autopilot mode for infrastructure modifications
    - Comprehensive audit logging
    - Automatic rollback on failure (when safe)
    """

    # Actions that are completely blocked
    BLOCKED_ACTIONS: Set[str] = {
        "delete_namespace",
        "delete_cluster",
        "terminate_all",
        "purge_all",
        "force_delete",
    }

    # Critical namespaces requiring extra approval
    CRITICAL_NAMESPACES: Set[str] = {
        "kube-system",
        "kube-public",
        "kube-node-lease",
    }

    # Actions supporting automatic rollback
    ROLLBACK_SUPPORTED: Set[str] = {
        "scale",
        "update",
        "patch",
        "restart",
    }

    def __init__(self, registry: Optional[ToolRegistry] = None):
        """
        Initialize the Action Agent.

        Args:
            registry: Optional tool registry to use
        """
        self.registry = registry or get_registry()
        self._pending_actions: Dict[str, ActionResult] = {}
        self._action_history: List[Dict[str, Any]] = []

        self.logger = logger.bind(agent_type="action")

    async def execute_action(
        self,
        action: str,
        target: str,
        resource_type: str,
        namespace: str = "default",
        parameters: Optional[Dict[str, Any]] = None,
        requested_by: str = "unknown",
        skip_approval: bool = False,  # ALWAYS False in production
        context: Optional[Dict[str, Any]] = None,
    ) -> ActionResult:
        """
        Execute an infrastructure action with full safety controls.

        FLOW:
        1. Validate action is not blocked
        2. Perform dry-run (mandatory)
        3. Generate impact analysis
        4. Request approval (mandatory)
        5. Execute only after approval
        6. Verify result
        7. Return detailed result

        Args:
            action: The action to perform
            target: Target resource name
            resource_type: Type of resource
            namespace: Kubernetes namespace
            parameters: Additional parameters
            requested_by: User requesting the action
            skip_approval: SECURITY FLAG - must ALWAYS be False
            context: Additional context

        Returns:
            ActionResult with full execution details

        Raises:
            ValueError: If action is blocked or parameters invalid
            RuntimeError: If execution fails critically
        """
        # SECURITY: Never allow skipping approval
        if skip_approval:
            self.logger.error(
                "approval_skip_blocked",
                action=action,
                target=target,
                reason="Approval skipping is not allowed for any infrastructure changes",
            )
            raise ValueError("Approval skipping is strictly prohibited")

        parameters = parameters or {}
        context = context or {}

        # Generate unique action ID
        action_id = str(uuid.uuid4())

        self.logger.info(
            "action_started",
            action_id=action_id,
            action=action,
            target=target,
            resource_type=resource_type,
            namespace=namespace,
            requested_by=requested_by,
        )

        # Step 1: Validate action
        if self._is_blocked_action(action):
            raise ValueError(f"Action '{action}' is blocked and cannot be executed")

        # Step 2: Create initial result object
        result = ActionResult(
            action_id=action_id,
            status=ActionStatus.PENDING,
            action=action,
            target=target,
            resource_type=resource_type,
            namespace=namespace,
            dry_run_result=None,
            dry_run_completed=False,
            requires_approval=True,  # ALWAYS True
            approval_id=None,
            approved_by=None,
            approved_at=None,
            rejection_reason=None,
            execution_result=None,
            execution_error=None,
            execution_duration_seconds=None,
            impact_analysis=self._analyze_impact(
                action, target, resource_type, namespace, parameters
            ),
            rollback_capability=self._determine_rollback(
                action, target, resource_type, namespace, parameters
            ),
            rollback_executed=False,
            rollback_result=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            completed_at=None,
        )

        # Step 3: MANDATORY dry-run
        self.logger.info("dry_run_start", action_id=action_id)
        result.status = ActionStatus.DRY_RUN

        dry_run = await self._perform_dry_run(
            action=action,
            target=target,
            resource_type=resource_type,
            namespace=namespace,
            parameters=parameters,
        )

        result.dry_run_result = dry_run
        result.dry_run_completed = True

        if not dry_run.success or not dry_run.would_succeed:
            result.status = ActionStatus.FAILED
            result.execution_error = f"Dry-run failed: {dry_run.errors}"
            result.completed_at = datetime.utcnow()

            self.logger.error(
                "dry_run_failed",
                action_id=action_id,
                errors=dry_run.errors,
            )
            return result

        self.logger.info("dry_run_success", action_id=action_id)

        # Step 4: MANDATORY approval request
        result.status = ActionStatus.AWAITING_APPROVAL
        approval_id = await self._create_approval_request(result, requested_by)
        result.approval_id = approval_id

        self.logger.info(
            "approval_requested",
            action_id=action_id,
            approval_id=approval_id,
        )

        # Store for later retrieval
        self._pending_actions[action_id] = result

        return result

    async def approve_action(
        self,
        action_id: str,
        approved_by: str,
        notes: Optional[str] = None,
    ) -> ActionResult:
        """
        Approve and execute a pending action.

        This method is called after human approval is granted.
        Only then will the actual execution occur.

        Args:
            action_id: The action ID to approve
            approved_by: User ID of approver
            notes: Optional approval notes

        Returns:
            Updated ActionResult with execution results
        """
        if action_id not in self._pending_actions:
            raise ValueError(f"Action {action_id} not found or already processed")

        result = self._pending_actions[action_id]

        if result.status != ActionStatus.AWAITING_APPROVAL:
            raise ValueError(
                f"Action {action_id} is not awaiting approval (status: {result.status})"
            )

        self.logger.info(
            "approval_received",
            action_id=action_id,
            approved_by=approved_by,
        )

        # Update approval info
        result.approved_by = approved_by
        result.approved_at = datetime.utcnow()
        result.status = ActionStatus.APPROVED
        result.updated_at = datetime.utcnow()

        # Step 5: EXECUTE the action (only after approval!)
        self.logger.info("execution_start", action_id=action_id)
        result.status = ActionStatus.EXECUTING

        start_time = datetime.utcnow()

        try:
            execution_result = await self._execute_with_safety(
                action=result.action,
                target=result.target,
                resource_type=result.resource_type,
                namespace=result.namespace,
                dry_run_result=result.dry_run_result,
            )

            execution_duration = int((datetime.utcnow() - start_time).total_seconds())

            result.execution_result = execution_result
            result.execution_duration_seconds = execution_duration
            result.status = ActionStatus.COMPLETED
            result.completed_at = datetime.utcnow()

            self.logger.info(
                "execution_success",
                action_id=action_id,
                duration_seconds=execution_duration,
            )

        except Exception as e:
            execution_duration = int((datetime.utcnow() - start_time).total_seconds())
            result.execution_error = str(e)
            result.execution_duration_seconds = execution_duration
            result.status = ActionStatus.FAILED
            result.completed_at = datetime.utcnow()

            self.logger.error(
                "execution_failed",
                action_id=action_id,
                error=str(e),
            )

            # Attempt rollback if available and safe
            if (
                result.rollback_capability.can_rollback
                and result.rollback_capability.automatic_rollback_available
            ):
                self.logger.info("attempting_rollback", action_id=action_id)
                try:
                    rollback_result = await self._execute_rollback(result)
                    result.rollback_executed = True
                    result.rollback_result = rollback_result
                    result.status = ActionStatus.ROLLED_BACK

                    self.logger.info("rollback_success", action_id=action_id)
                except Exception as rollback_error:
                    self.logger.error(
                        "rollback_failed",
                        action_id=action_id,
                        error=str(rollback_error),
                    )

        # Remove from pending
        del self._pending_actions[action_id]

        # Record in history
        self._action_history.append(
            {
                "action_id": action_id,
                "action": result.action,
                "target": result.target,
                "status": result.status.value,
                "approved_by": approved_by,
                "executed_at": datetime.utcnow().isoformat(),
            }
        )

        return result

    async def reject_action(
        self,
        action_id: str,
        rejected_by: str,
        reason: str,
    ) -> ActionResult:
        """
        Reject a pending action.

        Args:
            action_id: The action ID to reject
            rejected_by: User ID of rejector
            reason: Rejection reason

        Returns:
            Updated ActionResult
        """
        if action_id not in self._pending_actions:
            raise ValueError(f"Action {action_id} not found")

        result = self._pending_actions[action_id]
        result.status = ActionStatus.REJECTED
        result.rejection_reason = reason
        result.completed_at = datetime.utcnow()
        result.updated_at = datetime.utcnow()

        del self._pending_actions[action_id]

        self.logger.info(
            "action_rejected",
            action_id=action_id,
            rejected_by=rejected_by,
            reason=reason,
        )

        return result

    def _is_blocked_action(self, action: str) -> bool:
        """Check if action is permanently blocked."""
        return action.lower() in self.BLOCKED_ACTIONS

    async def _perform_dry_run(
        self,
        action: str,
        target: str,
        resource_type: str,
        namespace: str,
        parameters: Dict[str, Any],
    ) -> DryRunResult:
        """
        Perform dry-run simulation of the action.

        This simulates the action without making actual changes.
        """
        changes_preview = []
        warnings = []
        errors = []
        affected_resources = [f"{namespace}/{resource_type}/{target}"]

        try:
            # Simulate the action based on type
            if action == "scale":
                replicas = parameters.get("replicas", 1)
                changes_preview.append(
                    {
                        "type": "replica_change",
                        "resource": f"{namespace}/deployment/{target}",
                        "from": "current",
                        "to": replicas,
                        "description": f"Scale deployment to {replicas} replicas",
                    }
                )

                # Estimate affected pods
                current_pods = await self._get_current_pod_count(target, namespace)
                pod_change = replicas - current_pods
                if pod_change > 0:
                    warnings.append(f"Will create {pod_change} new pods")
                elif pod_change < 0:
                    warnings.append(f"Will terminate {abs(pod_change)} pods")

            elif action == "restart":
                changes_preview.append(
                    {
                        "type": "pod_restart",
                        "resource": f"{namespace}/{resource_type}/{target}",
                        "description": f"Restart all pods in {resource_type}/{target}",
                    }
                )
                warnings.append("This will cause temporary downtime for the service")
                warnings.append("Active connections will be dropped")

            elif action == "update":
                changes_preview.append(
                    {
                        "type": "resource_update",
                        "resource": f"{namespace}/{resource_type}/{target}",
                        "description": "Update resource configuration",
                        "changes": parameters,
                    }
                )
                warnings.append("Configuration change will trigger rolling update")

            elif action == "delete":
                changes_preview.append(
                    {
                        "type": "resource_deletion",
                        "resource": f"{namespace}/{resource_type}/{target}",
                        "description": f"Permanently delete {resource_type}/{target}",
                    }
                )
                warnings.append("THIS ACTION IS IRREVERSIBLE")
                errors.append("Data loss will occur if resource contains data")

                if namespace in self.CRITICAL_NAMESPACES:
                    errors.append(
                        f"Cannot delete resources in protected namespace: {namespace}"
                    )

            else:
                changes_preview.append(
                    {
                        "type": "generic_action",
                        "resource": f"{namespace}/{resource_type}/{target}",
                        "description": f"Execute {action} on {resource_type}/{target}",
                    }
                )

            # Check for critical namespace
            if namespace in self.CRITICAL_NAMESPACES:
                warnings.append(f"Operating in critical namespace: {namespace}")

            return DryRunResult(
                success=True,
                would_succeed=len(errors) == 0,
                changes_preview=changes_preview,
                warnings=warnings,
                errors=errors,
                affected_resources=affected_resources,
                estimated_duration_seconds=self._estimate_duration(
                    action, resource_type
                ),
            )

        except Exception as e:
            return DryRunResult(
                success=False,
                would_succeed=False,
                changes_preview=[],
                warnings=[],
                errors=[f"Dry-run simulation failed: {str(e)}"],
                affected_resources=affected_resources,
                estimated_duration_seconds=0,
            )

    async def _get_current_pod_count(self, deployment: str, namespace: str) -> int:
        """Get current pod count for a deployment."""
        # This would query Kubernetes API
        # For now, return a placeholder
        return 3  # Placeholder

    def _analyze_impact(
        self,
        action: str,
        target: str,
        resource_type: str,
        namespace: str,
        parameters: Dict[str, Any],
    ) -> ImpactAnalysis:
        """
        Analyze the impact of an action.

        Returns comprehensive impact analysis.
        """
        affected_resources = [f"{namespace}/{resource_type}/{target}"]
        affected_services = []
        potential_downtime = None
        data_impact = "none"
        security_impact = "none"
        performance_impact = "none"

        # Analyze based on action type
        if action == "delete":
            data_impact = "complete data loss if resource contains data"
            security_impact = "access policies will be removed"

        elif action == "restart":
            potential_downtime = "30-60 seconds during rolling restart"
            performance_impact = "temporary performance degradation during restart"

        elif action == "scale":
            replicas = parameters.get("replicas", 1)
            current = 3  # Would be queried
            if replicas < current:
                performance_impact = f"reduced capacity ({replicas}/{current} pods)"
            elif replicas > current:
                performance_impact = "increased capacity, higher resource usage"

        elif action == "update":
            potential_downtime = "minimal during rolling update"

        # Check for dependencies (would query service mesh or config)
        if resource_type in ["deployment", "service"]:
            affected_services.append(f"services depending on {target}")

        return ImpactAnalysis(
            affected_resources=affected_resources,
            affected_services=affected_services,
            potential_downtime=potential_downtime,
            data_impact=data_impact,
            security_impact=security_impact,
            performance_impact=performance_impact,
        )

    def _determine_rollback(
        self,
        action: str,
        target: str,
        resource_type: str,
        namespace: str,
        parameters: Dict[str, Any],
    ) -> RollbackCapability:
        """
        Determine rollback capability for an action.
        """
        can_rollback = action.lower() in self.ROLLBACK_SUPPORTED

        rollback_steps = []
        rollback_window = 300  # 5 minutes default
        automatic = False
        rollback_risks = []

        if can_rollback:
            if action == "scale":
                current_replicas = 3  # Would be queried
                rollback_steps.append(
                    {
                        "action": "scale",
                        "description": f"Scale back to {current_replicas} replicas",
                        "parameters": {"replicas": current_replicas},
                    }
                )
                automatic = True

            elif action == "update":
                rollback_steps.append(
                    {
                        "action": "restore_previous_version",
                        "description": "Restore to previous configuration version",
                    }
                )
                rollback_risks.append("May lose data written during update window")

            elif action == "restart":
                rollback_steps.append(
                    {
                        "action": "none",
                        "description": "Restart cannot be rolled back",
                    }
                )
                rollback_risks.append("Restart is immediate and cannot be undone")
                automatic = False

        if action == "delete":
            can_rollback = False
            rollback_risks.append("Deletion is permanent and cannot be rolled back")

        return RollbackCapability(
            can_rollback=can_rollback,
            rollback_steps=rollback_steps,
            rollback_window_seconds=rollback_window,
            automatic_rollback_available=automatic,
            rollback_risks=rollback_risks,
        )

    async def _create_approval_request(
        self,
        result: ActionResult,
        requested_by: str,
    ) -> str:
        """
        Create an approval request.

        Returns approval ID for tracking.
        """
        approval_id = str(uuid.uuid4())

        # In production, this would:
        # 1. Store in database
        # 2. Send notification to approvers
        # 3. Create approval workflow entry

        self.logger.info(
            "approval_request_created",
            approval_id=approval_id,
            action_id=result.action_id,
            action=result.action,
            target=result.target,
        )

        return approval_id

    async def _execute_with_safety(
        self,
        action: str,
        target: str,
        resource_type: str,
        namespace: str,
        dry_run_result: DryRunResult,
    ) -> Dict[str, Any]:
        """
        Execute the action with safety checks.

        This performs the actual infrastructure modification.
        """
        # Final safety check: verify dry-run passed
        if not dry_run_result or not dry_run_result.would_succeed:
            raise RuntimeError("Cannot execute: dry-run did not pass")

        # In production, this would:
        # 1. Call Kubernetes API
        # 2. Monitor execution
        # 3. Verify result
        # 4. Handle errors

        self.logger.info(
            "executing_action",
            action=action,
            target=target,
            resource_type=resource_type,
            namespace=namespace,
        )

        # Simulate execution for now
        # In production, this would make actual API calls
        return {
            "action": action,
            "target": target,
            "namespace": namespace,
            "status": "completed",
            "message": f"Successfully executed {action} on {resource_type}/{target}",
        }

    async def _execute_rollback(self, result: ActionResult) -> Dict[str, Any]:
        """
        Execute rollback for a failed action.
        """
        self.logger.info(
            "executing_rollback",
            action_id=result.action_id,
            action=result.action,
            target=result.target,
        )

        # In production, this would execute rollback steps
        return {
            "status": "rolled_back",
            "message": f"Rolled back {result.action} on {result.target}",
        }

    def _estimate_duration(self, action: str, resource_type: str) -> int:
        """Estimate execution duration in seconds."""
        base_durations = {
            "scale": 30,
            "restart": 60,
            "update": 45,
            "patch": 20,
            "delete": 15,
        }
        return base_durations.get(action.lower(), 30)

    def get_pending_actions(self) -> List[ActionResult]:
        """Get list of actions awaiting approval."""
        return list(self._pending_actions.values())

    def get_action(self, action_id: str) -> Optional[ActionResult]:
        """Get a specific action by ID."""
        return self._pending_actions.get(action_id)

    def get_capabilities(self) -> Dict[str, Any]:
        """Get agent capabilities and restrictions."""
        return {
            "supports_auto_execution": False,  # NEVER
            "requires_dry_run": True,  # ALWAYS
            "requires_approval": True,  # ALWAYS
            "supports_rollback": True,
            "blocked_actions": list(self.BLOCKED_ACTIONS),
            "supported_actions": list(self.ROLLBACK_SUPPORTED) + ["delete"],
            "approval_workflow": "mandatory",
            "safety_level": "maximum",
        }


# Global agent instance
_action_agent: Optional[ActionAgent] = None


def get_action_agent(registry: Optional[ToolRegistry] = None) -> ActionAgent:
    """Get or create the global action agent instance."""
    global _action_agent
    if _action_agent is None:
        _action_agent = ActionAgent(registry)
    return _action_agent
