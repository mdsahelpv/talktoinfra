"""
Planning Agent for creating execution plans with risk assessment.
Generates plans only - safe for auto-execution.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from app.tools.registry import ToolRegistry, get_registry


class PlanStepType(str, Enum):
    """Types of planning steps."""

    PRE_CHECK = "pre_check"  # Pre-execution validation
    ACTION = "action"  # Main action step
    VERIFY = "verify"  # Post-action verification
    ROLLBACK = "rollback"  # Rollback if needed
    NOTIFY = "notify"  # Notification step


@dataclass
class PlanStep:
    """Single step in an execution plan."""

    step_number: int
    step_type: PlanStepType
    description: str
    tool_name: Optional[str]
    operation: str
    parameters: Dict[str, Any]
    risk_level: str
    requires_approval: bool
    dry_run_first: bool
    estimated_duration_seconds: int
    can_rollback: bool
    rollback_step: Optional[int] = None  # Step number to rollback to
    dependencies: Optional[List[int]] = None


@dataclass
class PlanRisk:
    """Risk assessment for a plan."""

    overall_risk: str
    risk_score: int  # 0-100
    factors: List[Dict[str, Any]]
    mitigations: List[str]
    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_risk": self.overall_risk,
            "risk_score": self.risk_score,
            "factors": self.factors,
            "mitigations": self.mitigations,
            "warnings": self.warnings,
        }


@dataclass
class PlanResult:
    """Result of planning operation."""

    plan_id: str
    title: str
    description: str
    steps: List[PlanStep]
    risk_assessment: PlanRisk
    estimated_duration_seconds: int
    total_steps: int
    requires_approval_count: int
    can_auto_execute: bool
    rollback_available: bool
    created_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "title": self.title,
            "description": self.description,
            "steps": [
                {
                    "step_number": s.step_number,
                    "step_type": s.step_type.value,
                    "description": s.description,
                    "tool_name": s.tool_name,
                    "operation": s.operation,
                    "parameters": s.parameters,
                    "risk_level": s.risk_level,
                    "requires_approval": s.requires_approval,
                    "dry_run_first": s.dry_run_first,
                    "estimated_duration_seconds": s.estimated_duration_seconds,
                    "can_rollback": s.can_rollback,
                    "rollback_step": s.rollback_step,
                    "dependencies": s.dependencies,
                }
                for s in self.steps
            ],
            "risk_assessment": self.risk_assessment.to_dict(),
            "estimated_duration_seconds": self.estimated_duration_seconds,
            "total_steps": self.total_steps,
            "requires_approval_count": self.requires_approval_count,
            "can_auto_execute": self.can_auto_execute,
            "rollback_available": self.rollback_available,
            "created_at": self.created_at.isoformat(),
        }


class PlanningAgent:
    """
    Planning Agent for creating execution plans with risk assessment.

    This agent ONLY generates plans - it does NOT execute them.
    This makes it safe for auto-execution (plan generation only).

    Capabilities:
    - Create step-by-step execution plans
    - Risk assessment for each step
    - Dry-run planning
    - Rollback plan generation
    - Step dependency management
    """

    # High-risk operations that always require approval
    HIGH_RISK_OPERATIONS = {
        "delete",
        "remove",
        "terminate",
        "destroy",
        "purge",
        "scale_down",
        "stop",
        "restart",
        "recreate",
    }

    # Critical operations that need extra scrutiny
    CRITICAL_OPERATIONS = {
        "delete_namespace",
        "delete_all",
        "terminate_all",
        "restart_all",
        "stop_all",
    }

    # Operations that can rollback
    ROLLBACK_SUPPORTED = {
        "scale",
        "update",
        "patch",
        "restart",
    }

    def __init__(self, registry: Optional[ToolRegistry] = None):
        """
        Initialize the Planning Agent.

        Args:
            registry: Optional tool registry to use
        """
        self.registry = registry or get_registry()
        self._plan_counter = 0

    async def create_plan(
        self,
        action: str,
        target: str,
        resource_type: str,
        namespace: str = "default",
        parameters: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> PlanResult:
        """
        Create an execution plan for an action.

        Args:
            action: The action to perform (e.g., "scale", "restart", "update")
            target: Target resource name
            resource_type: Type of resource (pod, deployment, service, etc.)
            namespace: Kubernetes namespace
            parameters: Additional parameters for the action
            context: Additional context for planning

        Returns:
            PlanResult with detailed execution plan and risk assessment
        """
        context = context or {}
        parameters = parameters or {}

        # Generate unique plan ID
        self._plan_counter += 1
        plan_id = (
            f"plan-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{self._plan_counter}"
        )

        # Create plan title and description
        title = f"Execute {action} on {resource_type}/{target}"
        description = self._generate_description(
            action, resource_type, target, namespace, parameters
        )

        # Build plan steps
        steps = []
        step_number = 0

        # Step 1: Pre-check - validate target exists
        step_number += 1
        steps.append(
            self._create_pre_check_step(
                step_number=step_number,
                resource_type=resource_type,
                target=target,
                namespace=namespace,
            )
        )

        # Step 2: Dry-run simulation
        step_number += 1
        dry_run_step = self._create_dry_run_step(
            step_number=step_number,
            action=action,
            resource_type=resource_type,
            target=target,
            namespace=namespace,
            parameters=parameters,
            dependencies=[step_number - 1],
        )
        steps.append(dry_run_step)

        # Step 3: Main action
        step_number += 1
        action_step = self._create_action_step(
            step_number=step_number,
            action=action,
            resource_type=resource_type,
            target=target,
            namespace=namespace,
            parameters=parameters,
            dependencies=[step_number - 1],
        )
        steps.append(action_step)

        # Step 4: Verification
        step_number += 1
        steps.append(
            self._create_verify_step(
                step_number=step_number,
                resource_type=resource_type,
                target=target,
                namespace=namespace,
                action=action,
                dependencies=[step_number - 1],
            )
        )

        # Step 5: Rollback step (if supported)
        if self._is_rollback_supported(action):
            step_number += 1
            steps.append(
                self._create_rollback_step(
                    step_number=step_number,
                    action=action,
                    resource_type=resource_type,
                    target=target,
                    namespace=namespace,
                    parameters=parameters,
                    dependencies=[step_number - 2],  # Depends on action step
                )
            )
            # Link action step to rollback
            action_step.rollback_step = step_number

        # Perform risk assessment
        risk_assessment = self._assess_risk(
            action=action,
            resource_type=resource_type,
            target=target,
            namespace=namespace,
            steps=steps,
            context=context,
        )

        # Calculate plan metrics
        total_steps = len(steps)
        requires_approval_count = sum(1 for s in steps if s.requires_approval)
        estimated_duration = sum(s.estimated_duration_seconds for s in steps)

        # Determine if plan can auto-execute
        can_auto_execute = (
            risk_assessment.risk_score < 30
            and requires_approval_count == 0
            and not self._is_critical_operation(action, resource_type)
        )

        return PlanResult(
            plan_id=plan_id,
            title=title,
            description=description,
            steps=steps,
            risk_assessment=risk_assessment,
            estimated_duration_seconds=estimated_duration,
            total_steps=total_steps,
            requires_approval_count=requires_approval_count,
            can_auto_execute=can_auto_execute,
            rollback_available=self._is_rollback_supported(action),
            created_at=datetime.utcnow(),
        )

    def _generate_description(
        self,
        action: str,
        resource_type: str,
        target: str,
        namespace: str,
        parameters: Dict[str, Any],
    ) -> str:
        """Generate human-readable description of the plan."""
        desc = f"Plan to {action} {resource_type} '{target}' in namespace '{namespace}'"

        if parameters:
            param_desc = []
            if "replicas" in parameters:
                param_desc.append(f"replicas={parameters['replicas']}")
            if "image" in parameters:
                param_desc.append(f"image={parameters['image']}")
            if "config" in parameters:
                param_desc.append("config updates")

            if param_desc:
                desc += f" with parameters: {', '.join(param_desc)}"

        return desc

    def _create_pre_check_step(
        self,
        step_number: int,
        resource_type: str,
        target: str,
        namespace: str,
    ) -> PlanStep:
        """Create pre-check validation step."""
        return PlanStep(
            step_number=step_number,
            step_type=PlanStepType.PRE_CHECK,
            description=f"Validate {resource_type} '{target}' exists in namespace '{namespace}'",
            tool_name="describe_resource",
            operation="read",
            parameters={
                "resource_type": resource_type,
                "resource_name": target,
                "namespace": namespace,
            },
            risk_level="read_only",
            requires_approval=False,
            dry_run_first=False,
            estimated_duration_seconds=5,
            can_rollback=False,
            dependencies=None,
        )

    def _create_dry_run_step(
        self,
        step_number: int,
        action: str,
        resource_type: str,
        target: str,
        namespace: str,
        parameters: Dict[str, Any],
        dependencies: Optional[List[int]],
    ) -> PlanStep:
        """Create dry-run simulation step."""
        return PlanStep(
            step_number=step_number,
            step_type=PlanStepType.PRE_CHECK,
            description=f"Perform dry-run of {action} on {resource_type}/{target}",
            tool_name=f"{action}_{resource_type}",
            operation=f"{action}_dry_run",
            parameters={
                "resource_name": target,
                "namespace": namespace,
                "dry_run": True,
                **parameters,
            },
            risk_level="low",
            requires_approval=False,
            dry_run_first=True,
            estimated_duration_seconds=10,
            can_rollback=False,
            dependencies=dependencies,
        )

    def _create_action_step(
        self,
        step_number: int,
        action: str,
        resource_type: str,
        target: str,
        namespace: str,
        parameters: Dict[str, Any],
        dependencies: Optional[List[int]],
    ) -> PlanStep:
        """Create main action execution step."""
        # Determine risk level
        risk_level = self._determine_risk_level(action, resource_type)

        # Determine if approval is required
        requires_approval = self._requires_approval(action, resource_type, namespace)

        # Determine if rollback is supported
        can_rollback = self._is_rollback_supported(action)

        return PlanStep(
            step_number=step_number,
            step_type=PlanStepType.ACTION,
            description=f"Execute {action} on {resource_type}/{target}",
            tool_name=f"{action}_{resource_type}",
            operation=action,
            parameters={
                "resource_name": target,
                "namespace": namespace,
                **parameters,
            },
            risk_level=risk_level,
            requires_approval=requires_approval,
            dry_run_first=True,
            estimated_duration_seconds=self._estimate_duration(action, resource_type),
            can_rollback=can_rollback,
            dependencies=dependencies,
        )

    def _create_verify_step(
        self,
        step_number: int,
        resource_type: str,
        target: str,
        namespace: str,
        action: str,
        dependencies: Optional[List[int]],
    ) -> PlanStep:
        """Create verification step."""
        return PlanStep(
            step_number=step_number,
            step_type=PlanStepType.VERIFY,
            description=f"Verify {action} completed successfully on {resource_type}/{target}",
            tool_name="describe_resource",
            operation="read",
            parameters={
                "resource_type": resource_type,
                "resource_name": target,
                "namespace": namespace,
            },
            risk_level="read_only",
            requires_approval=False,
            dry_run_first=False,
            estimated_duration_seconds=5,
            can_rollback=False,
            dependencies=dependencies,
        )

    def _create_rollback_step(
        self,
        step_number: int,
        action: str,
        resource_type: str,
        target: str,
        namespace: str,
        parameters: Dict[str, Any],
        dependencies: Optional[List[int]],
    ) -> PlanStep:
        """Create rollback step."""
        rollback_action = self._get_rollback_action(action)

        return PlanStep(
            step_number=step_number,
            step_type=PlanStepType.ROLLBACK,
            description=f"Rollback {action} on {resource_type}/{target} if needed",
            tool_name=f"{rollback_action}_{resource_type}",
            operation=rollback_action,
            parameters={
                "resource_name": target,
                "namespace": namespace,
                "rollback": True,
                **parameters,
            },
            risk_level="medium",
            requires_approval=True,
            dry_run_first=True,
            estimated_duration_seconds=self._estimate_duration(action, resource_type),
            can_rollback=False,
            dependencies=dependencies,
        )

    def _determine_risk_level(self, action: str, resource_type: str) -> str:
        """Determine risk level for an action."""
        action_lower = action.lower()

        # Check for critical operations
        if action_lower in self.CRITICAL_OPERATIONS:
            return "critical"

        # Check for high-risk operations
        if any(op in action_lower for op in self.HIGH_RISK_OPERATIONS):
            return "high"

        # Check resource type risk
        high_risk_resources = {"namespace", "node", "cluster"}
        if resource_type.lower() in high_risk_resources:
            return "high"

        # Default to medium for modifications
        return "medium"

    def _requires_approval(
        self, action: str, resource_type: str, namespace: str
    ) -> bool:
        """Determine if approval is required for an action."""
        action_lower = action.lower()

        # Always require approval for critical/high-risk
        if action_lower in self.CRITICAL_OPERATIONS:
            return True

        if any(op in action_lower for op in self.HIGH_RISK_OPERATIONS):
            return True

        # Require approval for production namespaces
        protected_namespaces = {"production", "prod", "kube-system"}
        if namespace.lower() in protected_namespaces:
            return True

        # Require approval for high-risk resources
        high_risk_resources = {"namespace", "node", "cluster"}
        if resource_type.lower() in high_risk_resources:
            return True

        return False

    def _is_rollback_supported(self, action: str) -> bool:
        """Check if action supports rollback."""
        action_lower = action.lower()
        return any(op in action_lower for op in self.ROLLBACK_SUPPORTED)

    def _is_critical_operation(self, action: str, resource_type: str) -> bool:
        """Check if this is a critical operation."""
        action_lower = action.lower()
        if action_lower in self.CRITICAL_OPERATIONS:
            return True

        if resource_type.lower() in {"namespace", "cluster"}:
            return True

        return False

    def _get_rollback_action(self, action: str) -> str:
        """Get the rollback action for a given action."""
        rollback_map = {
            "scale": "scale",
            "update": "update",
            "patch": "patch",
            "restart": "restart",
        }
        return rollback_map.get(action.lower(), "restore")

    def _estimate_duration(self, action: str, resource_type: str) -> int:
        """Estimate duration for an action in seconds."""
        # Base durations
        base_durations = {
            "scale": 30,
            "restart": 60,
            "update": 45,
            "patch": 20,
            "delete": 15,
            "create": 30,
        }

        # Resource multipliers
        resource_multipliers = {
            "pod": 1.0,
            "deployment": 2.0,
            "service": 1.5,
            "namespace": 3.0,
            "node": 5.0,
        }

        base = base_durations.get(action.lower(), 30)
        multiplier = resource_multipliers.get(resource_type.lower(), 1.0)

        return int(base * multiplier)

    def _assess_risk(
        self,
        action: str,
        resource_type: str,
        target: str,
        namespace: str,
        steps: List[PlanStep],
        context: Dict[str, Any],
    ) -> PlanRisk:
        """
        Perform comprehensive risk assessment.

        Returns PlanRisk with detailed risk analysis.
        """
        factors = []
        mitigations = []
        warnings = []
        risk_score = 0

        # Factor 1: Action type risk
        action_risk = self._get_action_risk_score(action)
        factors.append(
            {
                "factor": "action_type",
                "description": f"Action '{action}' has inherent risk",
                "score": action_risk,
                "weight": 0.3,
            }
        )
        risk_score += action_risk * 0.3

        # Factor 2: Resource type risk
        resource_risk = self._get_resource_risk_score(resource_type)
        factors.append(
            {
                "factor": "resource_type",
                "description": f"Resource type '{resource_type}' risk level",
                "score": resource_risk,
                "weight": 0.25,
            }
        )
        risk_score += resource_risk * 0.25

        # Factor 3: Environment risk
        env_risk = self._get_environment_risk_score(namespace)
        factors.append(
            {
                "factor": "environment",
                "description": f"Namespace '{namespace}' environment risk",
                "score": env_risk,
                "weight": 0.25,
            }
        )
        risk_score += env_risk * 0.25

        # Factor 4: Step count risk (complexity)
        step_count = len(steps)
        complexity_risk = min(step_count * 5, 30)  # Max 30 points
        factors.append(
            {
                "factor": "complexity",
                "description": f"Plan has {step_count} steps",
                "score": complexity_risk,
                "weight": 0.2,
            }
        )
        risk_score += complexity_risk * 0.2

        # Generate mitigations based on risks
        if action_risk > 50:
            mitigations.append("Dry-run will be performed before actual execution")
            mitigations.append("Approval required before execution")

        if resource_risk > 50:
            mitigations.append("Pre-check validation of resource state")
            mitigations.append("Post-execution verification step")

        if env_risk > 50:
            mitigations.append("Extra caution in production environment")
            mitigations.append("Extended approval workflow")

        # Check for rollback capability
        if self._is_rollback_supported(action):
            mitigations.append("Rollback capability available if needed")
        else:
            warnings.append("No automatic rollback available for this operation")

        # Generate warnings
        if action.lower() in self.HIGH_RISK_OPERATIONS:
            warnings.append(f"High-risk operation: {action}")

        if namespace.lower() in {"production", "prod"}:
            warnings.append("Target is production namespace")

        # Determine overall risk level
        if risk_score >= 70:
            overall_risk = "critical"
        elif risk_score >= 50:
            overall_risk = "high"
        elif risk_score >= 30:
            overall_risk = "medium"
        elif risk_score >= 10:
            overall_risk = "low"
        else:
            overall_risk = "minimal"

        return PlanRisk(
            overall_risk=overall_risk,
            risk_score=int(risk_score),
            factors=factors,
            mitigations=mitigations,
            warnings=warnings,
        )

    def _get_action_risk_score(self, action: str) -> int:
        """Get risk score for an action (0-100)."""
        action_lower = action.lower()

        if action_lower in self.CRITICAL_OPERATIONS:
            return 90

        if action_lower in {"delete", "terminate", "destroy"}:
            return 80

        if action_lower in {"stop", "restart", "recreate"}:
            return 60

        if action_lower in {"scale", "update", "patch"}:
            return 40

        if action_lower in {"create", "deploy"}:
            return 30

        return 50

    def _get_resource_risk_score(self, resource_type: str) -> int:
        """Get risk score for a resource type (0-100)."""
        resource_lower = resource_type.lower()

        risk_scores = {
            "cluster": 90,
            "namespace": 85,
            "node": 80,
            "deployment": 60,
            "statefulset": 65,
            "daemonset": 70,
            "service": 50,
            "configmap": 40,
            "secret": 45,
            "pod": 30,
            "job": 35,
            "cronjob": 40,
        }

        return risk_scores.get(resource_lower, 50)

    def _get_environment_risk_score(self, namespace: str) -> int:
        """Get risk score for environment (0-100)."""
        namespace_lower = namespace.lower()

        if namespace_lower in {"production", "prod"}:
            return 80

        if namespace_lower in {"staging", "preprod"}:
            return 50

        if namespace_lower in {"development", "dev", "test"}:
            return 20

        if namespace_lower in {"kube-system", "kube-public"}:
            return 90

        return 30

    def get_capabilities(self) -> Dict[str, Any]:
        """Get planning agent capabilities."""
        return {
            "supported_actions": list(self.HIGH_RISK_OPERATIONS)
            + ["scale", "update", "patch", "create", "deploy"],
            "risk_assessment": True,
            "rollback_planning": True,
            "step_dependencies": True,
            "dry_run_integration": True,
            "plan_format": "structured_steps",
        }


# Global agent instance
_planning_agent: Optional[PlanningAgent] = None


def get_planning_agent(registry: Optional[ToolRegistry] = None) -> PlanningAgent:
    """Get or create the global planning agent instance."""
    global _planning_agent
    if _planning_agent is None:
        _planning_agent = PlanningAgent(registry)
    return _planning_agent
