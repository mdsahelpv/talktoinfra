"""
Base Agent class for Agent Service.
Abstract base that defines the common interface and safety patterns.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime
import structlog
import asyncio

from ...app.config import Settings
from ...models import (
    Task,
    TaskResult,
    TaskStatus,
    ExecutionPlan,
    ExecutionStep,
    AgentType,
    RiskLevel,
    SafetyResult,
)
from ...app.core.safety import SafetyEngine
from ...app.core.audit_logger import AuditLogger

logger = structlog.get_logger()


class BaseAgent(ABC):
    """
    Abstract base class for all agents.
    Implements common safety patterns and execution flow.
    """

    agent_type: AgentType
    risk_level: RiskLevel
    requires_approval: bool

    def __init__(
        self,
        settings: Settings,
        safety_engine: SafetyEngine,
        audit_logger: AuditLogger,
        tool_registry: Any,
        llm_client: Any,
    ):
        self.settings = settings
        self.safety = safety_engine
        self.audit = audit_logger
        self.tools = tool_registry
        self.llm = llm_client
        self.logger = logger.bind(agent_type=self.agent_type.value)

    async def execute(self, task: Task) -> TaskResult:
        """
        Execute a task with full safety checks.

        Flow:
        1. Plan execution
        2. Validate safety for each step
        3. Execute with approval if required
        4. Verify results
        5. Return response
        """
        self.logger.info(
            "task_started",
            task_id=task.id,
            query=task.query[:100],  # Truncate for logging
        )

        start_time = datetime.utcnow()

        try:
            # 1. Parse and plan
            await self._update_task_status(task, TaskStatus.PLANNING)
            plan = await self.plan(task)

            if not plan or not plan.steps:
                return TaskResult.failed("No execution plan generated")

            # Store plan
            await self._store_plan(task, plan)

            # 2. Execute plan with safety checks
            step_results = []
            for i, step in enumerate(plan.steps):
                self.logger.info(
                    "executing_step",
                    task_id=task.id,
                    step_number=i + 1,
                    tool=step.tool_name,
                )

                # Safety validation
                safety_result = await self._validate_step_safety(step, task)

                if not safety_result.allowed:
                    await self.audit.log_task_failed(task, safety_result.reason)
                    return TaskResult.failed(
                        reason=f"Safety check failed: {safety_result.reason}",
                        safety_result=safety_result.to_dict()
                        if hasattr(safety_result, "to_dict")
                        else {},
                    )

                # Check if approval required
                if safety_result.requires_approval:
                    approval = await self._request_approval(
                        task=task,
                        step=step,
                        safety_result=safety_result,
                        step_number=i + 1,
                    )

                    if not approval or approval.status != "approved":
                        reason = f"Step {i + 1} not approved"
                        await self.audit.log_task_failed(task, reason)
                        return TaskResult.failed(
                            reason=reason, approval_id=approval.id if approval else None
                        )

                # Execute step
                await self._update_task_status(task, TaskStatus.EXECUTING)
                result = await self.execute_step(step)
                step_results.append(result)

                # Log tool execution
                await self.audit.log_tool_called(task.id, result)

                # Verify result
                if not await self.verify_step(step, result):
                    error_msg = f"Step {i + 1} verification failed"
                    await self.audit.log_task_failed(task, error_msg)
                    return TaskResult.failed(
                        reason=error_msg, step_results=step_results
                    )

                # Check if we need to replan
                if result.requires_replanning:
                    self.logger.info("replanning_required", task_id=task.id)
                    plan = await self.replan(plan, result, task)

            # 3. Synthesize final response
            execution_time = int(
                (datetime.utcnow() - start_time).total_seconds() * 1000
            )
            response = await self.synthesize_response(step_results, task)

            # 4. Mark complete
            await self._update_task_status(task, TaskStatus.COMPLETED)

            self.logger.info(
                "task_completed",
                task_id=task.id,
                execution_time_ms=execution_time,
                steps_executed=len(step_results),
            )

            await self.audit.log_task_completed(task, TaskResult.success(""))

            return TaskResult.success(
                response=response,
                plan=plan,
                step_results=step_results,
                execution_time_ms=execution_time,
            )

        except Exception as e:
            self.logger.error("task_failed", task_id=task.id, error=str(e))
            await self._update_task_status(task, TaskStatus.FAILED)
            await self.audit.log_task_failed(task, str(e))
            return TaskResult.failed(reason=str(e))

    @abstractmethod
    async def plan(self, task: Task) -> ExecutionPlan:
        """
        Create execution plan for the task.
        Override in subclass.
        """
        pass

    @abstractmethod
    async def execute_step(self, step: ExecutionStep) -> Any:
        """
        Execute a single step of the plan.
        Override in subclass.
        """
        pass

    @abstractmethod
    async def verify_step(self, step: ExecutionStep, result: Any) -> bool:
        """
        Verify step execution was successful.
        Override in subclass.
        """
        pass

    @abstractmethod
    async def synthesize_response(self, results: List[Any], task: Task) -> str:
        """
        Synthesize final response from step results.
        Override in subclass.
        """
        pass

    async def replan(
        self, plan: ExecutionPlan, failed_result: Any, task: Task
    ) -> ExecutionPlan:
        """
        Replan based on failed step.
        Default implementation returns original plan.
        Override for adaptive behavior.
        """
        return plan

    async def _validate_step_safety(
        self, step: ExecutionStep, task: Task
    ) -> SafetyResult:
        """
        Validate step safety.
        """
        action = {
            "tool": step.tool_name,
            "operation": step.operation,
            "parameters": step.parameters,
            "target": step.parameters.get("name", "unknown"),
        }

        context = {
            "user_id": task.user_id,
            "environment": task.environment,
            "task_id": task.id,
            "agent_type": self.agent_type.value,
        }

        return await self.safety.validate(action, context)

    async def _request_approval(
        self,
        task: Task,
        step: ExecutionStep,
        safety_result: SafetyResult,
        step_number: int,
    ) -> Any:
        """
        Create approval request and wait for human decision.
        """
        from ...models import Approval

        approval = await self.safety.create_approval_request(
            task_id=task.id, step=step, safety_result=safety_result
        )

        await self.audit.log_approval_requested(approval)

        # Wait for approval (blocking with timeout)
        result = await self.safety.wait_for_approval(
            approval_id=approval.id, timeout=self.settings.approval_timeout_seconds
        )

        await self.audit.log_approval_decision(
            approval=approval,
            decision=result.status,
            decided_by=result.approved_by or result.rejected_by or "system",
        )

        return result

    async def _update_task_status(self, task: Task, status: TaskStatus) -> None:
        """Update task status in database."""
        # In production, update via database
        task.status = status
        task.updated_at = datetime.utcnow()

    async def _store_plan(self, task: Task, plan: ExecutionPlan) -> None:
        """Store execution plan."""
        task.plan = {
            "steps": [
                {
                    "step_number": s.step_number,
                    "tool_name": s.tool_name,
                    "description": s.description,
                    "risk_level": s.risk_level.value,
                    "requires_approval": s.requires_approval,
                }
                for s in plan.steps
            ],
            "estimated_duration": plan.estimated_duration_seconds,
            "warnings": plan.warnings,
        }
