"""
Step Execution Handlers

Provides handlers for each workflow step type: action, condition, wait, approval,
parallel, and notification.
"""

import asyncio
import httpx
from typing import Any, Dict, Optional
from abc import ABC, abstractmethod

import structlog

logger = structlog.get_logger()


class StepHandler(ABC):
    """Base class for step handlers."""

    @abstractmethod
    async def execute(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the step with the given configuration and context.

        Args:
            step: Step configuration dictionary
            context: Execution context dictionary

        Returns:
            Step execution result dictionary
        """

    @abstractmethod
    async def validate(self, step: Dict[str, Any]) -> bool:
        """Validate step configuration.

        Args:
            step: Step configuration dictionary

        Returns:
            True if step configuration is valid
        """


class ActionStepHandler(StepHandler):
    """Handler for action steps - calls action-engine service."""

    def __init__(self, action_engine_url: str):
        """Initialize action step handler.

        Args:
            action_engine_url: Base URL for the action engine service
        """
        self.action_engine_url = action_engine_url

    async def execute(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute action step by calling the action engine.

        Args:
            step: Step configuration
            context: Execution context

        Returns:
            Action execution result
        """
        action_config = step.get("config", {})
        action_type = action_config.get("action_type")

        logger.info(
            "action_step_executing",
            step_id=step.get("id"),
            action_type=action_type,
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.action_engine_url}/api/v1/execute",
                json={
                    "action_type": action_type,
                    "parameters": action_config.get("parameters", {}),
                    "context": context,
                    "dry_run": action_config.get("dry_run", False),
                },
                timeout=60.0,
            )
            response.raise_for_status()
            result = response.json()

        logger.info(
            "action_step_completed",
            step_id=step.get("id"),
            action_type=action_type,
        )

        return result

    async def validate(self, step: Dict[str, Any]) -> bool:
        """Validate action step configuration.

        Args:
            step: Step configuration

        Returns:
            True if valid
        """
        config = step.get("config", {})
        return "action_type" in config


class ConditionStepHandler(StepHandler):
    """Handler for condition steps - evaluates conditions."""

    async def execute(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute condition step by evaluating conditions.

        Args:
            step: Step configuration
            context: Execution context

        Returns:
            Condition evaluation result with next step
        """
        config = step.get("config", {})
        conditions = config.get("conditions", [])

        logger.info(
            "condition_step_evaluating",
            step_id=step.get("id"),
            conditions_count=len(conditions),
        )

        for condition in conditions:
            if await self._evaluate_condition(condition, context):
                result = {
                    "result": True,
                    "next_step": condition.get("next_step"),
                    "matched_condition": condition.get("name"),
                }
                logger.info(
                    "condition_matched",
                    step_id=step.get("id"),
                    condition=condition.get("name"),
                    next_step=condition.get("next_step"),
                )
                return result

        result = {
            "result": False,
            "next_step": config.get("default_next"),
            "matched_condition": None,
        }

        logger.info(
            "condition_no_match",
            step_id=step.get("id"),
            default_next=config.get("default_next"),
        )

        return result

    async def _evaluate_condition(
        self, condition: Dict[str, Any], context: Dict[str, Any]
    ) -> bool:
        """Evaluate a single condition.

        Args:
            condition: Condition configuration
            context: Execution context

        Returns:
            True if condition is met
        """
        var_path = condition.get("variable", "")
        operator = condition.get("operator", "eq")
        expected = condition.get("value")
        actual = self._get_nested_value(context, var_path)

        if operator == "eq":
            return actual == expected
        elif operator == "ne":
            return actual != expected
        elif operator == "gt":
            return actual > expected
        elif operator == "lt":
            return actual < expected
        elif operator == "gte":
            return actual >= expected
        elif operator == "lte":
            return actual <= expected
        elif operator == "contains":
            return expected in actual if actual else False
        elif operator == "exists":
            return actual is not None
        elif operator == "not_exists":
            return actual is None
        return False

    def _get_nested_value(self, data: Dict, path: str) -> Any:
        """Get nested value from dictionary using dot notation.

        Args:
            data: Dictionary to search
            path: Dot-separated path (e.g., "user.id")

        Returns:
            Value at path or None
        """
        if not path:
            return data

        keys = path.split(".")
        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value

    async def validate(self, step: Dict[str, Any]) -> bool:
        """Validate condition step configuration.

        Args:
            step: Step configuration

        Returns:
            True if valid
        """
        config = step.get("config", {})
        return "conditions" in config or "default_next" in config


class WaitStepHandler(StepHandler):
    """Handler for wait steps - pauses execution."""

    async def execute(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute wait step.

        Args:
            step: Step configuration
            context: Execution context

        Returns:
            Wait result
        """
        config = step.get("config", {})
        wait_type = config.get("wait_type", "duration")

        logger.info(
            "wait_step_executing",
            step_id=step.get("id"),
            wait_type=wait_type,
        )

        if wait_type == "duration":
            duration_seconds = config.get("duration_seconds", 0)
            await asyncio.sleep(duration_seconds)
            return {"result": "completed", "waited_seconds": duration_seconds}

        elif wait_type == "condition":
            max_attempts = config.get("max_attempts", 60)
            interval = config.get("interval_seconds", 5)

            for attempt in range(max_attempts):
                condition_met = await self._check_condition(config, context)
                if condition_met:
                    logger.info(
                        "wait_condition_met",
                        step_id=step.get("id"),
                        attempts=attempt + 1,
                    )
                    return {"result": "completed", "attempts": attempt + 1}
                await asyncio.sleep(interval)

            logger.warning(
                "wait_condition_timeout",
                step_id=step.get("id"),
                max_attempts=max_attempts,
            )
            return {"result": "timeout", "attempts": max_attempts}

        elif wait_type == "webhook":
            webhook_url = config.get("webhook_url")
            timeout_seconds = config.get("timeout_seconds", 3600)

            result = await self._wait_for_webhook(webhook_url, timeout_seconds, step.get("id"))
            return result

        return {"result": "unknown_wait_type"}

    async def _check_condition(self, config: Dict, context: Dict) -> bool:
        """Check if wait condition is met.

        Args:
            config: Wait configuration
            context: Execution context

        Returns:
            True if condition is met
        """
        condition_expr = config.get("condition_expression")
        if not condition_expr:
            return False

        # Simple condition evaluation
        condition_handler = ConditionStepHandler()
        for cond in condition_expr.get("conditions", []):
            if await condition_handler._evaluate_condition(cond, context):
                return True

        return False

    async def _wait_for_webhook(
        self, webhook_url: str, timeout_seconds: int, step_id: str
    ) -> Dict[str, Any]:
        """Wait for webhook callback.

        Args:
            webhook_url: URL to call
            timeout_seconds: Maximum wait time
            step_id: Step identifier

        Returns:
            Webhook wait result
        """
        # Placeholder - would need Redis/pub-sub for actual webhook callback
        logger.warning(
            "webhook_wait_not_implemented",
            step_id=step_id,
            webhook_url=webhook_url,
        )
        return {"result": "pending", "message": "Webhook callback not configured"}

    async def validate(self, step: Dict[str, Any]) -> bool:
        """Validate wait step configuration.

        Args:
            step: Step configuration

        Returns:
            True if valid
        """
        config = step.get("config", {})
        return "wait_type" in config


class ApprovalStepHandler(StepHandler):
    """Handler for approval steps - waits for human approval."""

    def __init__(self, notification_url: str):
        """Initialize approval step handler.

        Args:
            notification_url: Base URL for notification service
        """
        self.notification_url = notification_url

    async def execute(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute approval step.

        Args:
            step: Step configuration
            context: Execution context

        Returns:
            Approval request result
        """
        config = step.get("config", {})
        approvers = config.get("approvers", [])
        timeout_hours = config.get("timeout_hours", 24)

        logger.info(
            "approval_step_requested",
            step_id=step.get("id"),
            approvers=approvers,
            timeout_hours=timeout_hours,
        )

        # Send approval request notification
        if approvers and self.notification_url:
            await self._send_approval_request(step, context, approvers)

        return {
            "result": "pending_approval",
            "approvers": approvers,
            "approval_request_id": step.get("id"),
            "timeout_hours": timeout_hours,
        }

    async def _send_approval_request(
        self, step: Dict[str, Any], context: Dict[str, Any], approvers: list
    ):
        """Send approval request notification.

        Args:
            step: Step configuration
            context: Execution context
            approvers: List of approver identifiers
        """
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{self.notification_url}/api/v1/notifications",
                    json={
                        "type": "approval_request",
                        "recipients": approvers,
                        "workflow_id": context.get("workflow_id"),
                        "execution_id": context.get("execution_id"),
                        "step_id": step.get("id"),
                        "step_name": step.get("name"),
                        "message": config.get("message", "Approval required for workflow execution"),
                    },
                    timeout=30.0,
                )
        except Exception as e:
            logger.warning(
                "approval_notification_failed",
                step_id=step.get("id"),
                error=str(e),
            )

    async def validate(self, step: Dict[str, Any]) -> bool:
        """Validate approval step configuration.

        Args:
            step: Step configuration

        Returns:
            True if valid
        """
        config = step.get("config", {})
        return "approvers" in config


class ParallelStepHandler(StepHandler):
    """Handler for parallel steps - executes multiple branches concurrently."""

    def __init__(self, step_handlers: Dict[str, StepHandler]):
        """Initialize parallel step handler.

        Args:
            step_handlers: Registry of step handlers by type
        """
        self.step_handlers = step_handlers

    async def execute(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute parallel step by running branches concurrently.

        Args:
            step: Step configuration
            context: Execution context

        Returns:
            Parallel execution result
        """
        config = step.get("config", {})
        branches = config.get("branches", [])

        logger.info(
            "parallel_step_executing",
            step_id=step.get("id"),
            branches_count=len(branches),
        )

        # Execute all branches concurrently
        tasks = []
        for branch in branches:
            branch_steps = branch.get("steps", [])
            branch_context = {**context, "branch_id": branch.get("id")}

            for branch_step in branch_steps:
                handler = self.step_handlers.get(branch_step.get("type"))
                if handler:
                    tasks.append(
                        self._execute_branch_step(
                            handler, branch_step, branch_context)
                    )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check for failures
        failures = [r for r in results if isinstance(r, Exception)]
        if failures:
            logger.error(
                "parallel_step_failed",
                step_id=step.get("id"),
                failures_count=len(failures),
            )
            return {
                "result": "failed",
                "errors": [str(f) for f in failures],
            }

        successful_results = [
            r for r in results if not isinstance(r, Exception)]

        logger.info(
            "parallel_step_completed",
            step_id=step.get("id"),
            results_count=len(successful_results),
        )

        return {"result": "completed", "branch_results": successful_results}

    async def _execute_branch_step(
        self,
        handler: StepHandler,
        branch_step: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a single step within a branch.

        Args:
            handler: Step handler
            branch_step: Step configuration
            context: Branch context

        Returns:
            Step execution result
        """
        return await handler.execute(branch_step, context)

    async def validate(self, step: Dict[str, Any]) -> bool:
        """Validate parallel step configuration.

        Args:
            step: Step configuration

        Returns:
            True if valid
        """
        config = step.get("config", {})
        return "branches" in config


class NotificationStepHandler(StepHandler):
    """Handler for notification steps - sends alerts/messages."""

    def __init__(self, notification_url: str):
        """Initialize notification step handler.

        Args:
            notification_url: Base URL for notification service
        """
        self.notification_url = notification_url

    async def execute(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute notification step.

        Args:
            step: Step configuration
            context: Execution context

        Returns:
            Notification result
        """
        config = step.get("config", {})
        notification_type = config.get("type", "email")
        recipients = config.get("recipients", [])
        message = config.get("message", "")

        logger.info(
            "notification_step_sending",
            step_id=step.get("id"),
            notification_type=notification_type,
            recipients_count=len(recipients),
        )

        # Send notification via notification service
        if self.notification_url and recipients:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.notification_url}/api/v1/notifications",
                        json={
                            "type": notification_type,
                            "recipients": recipients,
                            "message": message,
                            "workflow_id": context.get("workflow_id"),
                            "execution_id": context.get("execution_id"),
                            "step_id": step.get("id"),
                        },
                        timeout=30.0,
                    )
                    response.raise_for_status()
                    result = response.json()

                logger.info(
                    "notification_sent",
                    step_id=step.get("id"),
                    notification_type=notification_type,
                )

                return {"result": "sent", "recipients": recipients, "type": notification_type}

            except Exception as e:
                logger.error(
                    "notification_failed",
                    step_id=step.get("id"),
                    error=str(e),
                )
                return {
                    "result": "failed",
                    "error": str(e),
                    "recipients": recipients,
                    "type": notification_type,
                }

        # Fallback: return mock result if no notification service configured
        return {"result": "sent", "recipients": recipients, "type": notification_type}

    async def validate(self, step: Dict[str, Any]) -> bool:
        """Validate notification step configuration.

        Args:
            step: Step configuration

        Returns:
            True if valid
        """
        config = step.get("config", {})
        return "recipients" in config and "type" in config


def get_step_handlers(
    action_engine_url: str, notification_url: str
) -> Dict[str, StepHandler]:
    """Create and return step handler registry.

    Args:
        action_engine_url: Base URL for action engine service
        notification_url: Base URL for notification service

    Returns:
        Dictionary mapping step type names to handler instances
    """
    handlers: Dict[str, StepHandler] = {
        "action": ActionStepHandler(action_engine_url),
        "condition": ConditionStepHandler(),
        "wait": WaitStepHandler(),
        "approval": ApprovalStepHandler(notification_url),
        "notification": NotificationStepHandler(notification_url),
    }

    # Parallel handler needs reference to other handlers
    handlers["parallel"] = ParallelStepHandler(handlers)

    return handlers
