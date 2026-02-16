"""
Celery Tasks for Workflow Execution

Provides async workflow and step execution through Celery workers.
"""

import asyncio
import time
import structlog
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from celery_app import celery_app
from event_publisher import (
    get_event_publisher,
    WorkflowEventPublisher,
)
from step_handlers import get_step_handlers, StepHandler
from config import get_settings


logger = structlog.get_logger()

# Global storage references (will be set from main.py)
workflow_executions: Dict[str, Any] = {}
workflow_definitions: Dict[str, Any] = {}

# Global event publisher reference
_event_publisher: Optional[WorkflowEventPublisher] = None

# Global step handlers registry
_step_handlers: Optional[Dict[str, StepHandler]] = None


def get_step_handlers_registry() -> Dict[str, StepHandler]:
    """Get or create step handlers registry."""
    global _step_handlers
    if _step_handlers is None:
        settings = get_settings()
        _step_handlers = get_step_handlers(
            action_engine_url=settings.action_engine_url,
            notification_url=settings.notification_url,
        )
    return _step_handlers


def set_storage_refs(executions: Dict[str, Any], definitions: Dict[str, Any]):
    """Set references to the main storage dictionaries."""
    global workflow_executions, workflow_definitions
    workflow_executions = executions
    workflow_definitions = definitions


def set_event_publisher(publisher: WorkflowEventPublisher):
    """Set the event publisher instance."""
    global _event_publisher
    _event_publisher = publisher


def get_event_publisher_instance() -> WorkflowEventPublisher:
    """Get the event publisher instance."""
    global _event_publisher
    if _event_publisher is None:
        _event_publisher = get_event_publisher()
    return _event_publisher


async def _async_publish_nats_event(event_type: str, data: Dict[str, Any]):
    """Async implementation of NATS event publishing."""
    publisher = get_event_publisher_instance()
    await publisher._publish(
        f"workflow.events.{data.get('execution_id', 'unknown')}.{event_type}",
        {"event_type": event_type, **data},
    )


def publish_nats_event(event_type: str, data: Dict[str, Any]):
    """Publish event to NATS (sync wrapper for Celery tasks)."""
    try:
        asyncio.run(_async_publish_nats_event(event_type, data))
    except RuntimeError:
        # Already in an event loop, use ensure_future
        asyncio.get_event_loop().create_task(
            _async_publish_nats_event(event_type, data)
        )


def update_redis_cache(execution_id: str, status: str, progress: Dict[str, Any]):
    """Update execution state in Redis cache (placeholder - implement when Redis is configured)."""
    # TODO: Implement Redis caching when redis-py client is configured
    logger.info(
        "redis_cache_update",
        execution_id=execution_id,
        status=status,
        progress=progress,
    )


@celery_app.task(bind=True, max_retries=3, acks_late=True)
def execute_workflow_task(self, workflow_id: str, execution_id: str) -> Dict[str, Any]:
    """Execute a workflow asynchronously.

    Args:
        workflow_id: The workflow definition ID
        execution_id: The execution instance ID

    Returns:
        Dictionary containing execution results
    """
    logger.info(
        "workflow_task_started",
        task_id=self.request.id,
        workflow_id=workflow_id,
        execution_id=execution_id,
    )

    try:
        # Get workflow from storage
        if workflow_id not in workflow_definitions:
            raise ValueError(f"Workflow {workflow_id} not found")

        workflow = workflow_definitions[workflow_id]

        # Get execution from storage
        if execution_id not in workflow_executions:
            raise ValueError(f"Execution {execution_id} not found")

        execution = workflow_executions[execution_id]

        # Update execution status to running
        execution.status = "running"
        execution.started_at = datetime.utcnow().isoformat()

        # Update cache and publish event
        update_redis_cache(execution_id, "running", {"current_step": None})
        publish_nats_event(
            "workflow.started",
            {
                "execution_id": execution_id,
                "workflow_id": workflow_id,
            },
        )

        # Execute steps sequentially
        results: Dict[str, Any] = {}
        errors: list = []

        for step in workflow.steps:
            try:
                # Execute step
                step_result = execute_step_sync(step, execution)

                # Update step status in results
                results[step.id] = {
                    "status": "completed",
                    "result": step_result,
                }

                # Update execution progress
                execution.current_step_id = step.id
                execution.context[step.id] = step_result

                # Update cache and publish event
                update_redis_cache(
                    execution_id,
                    "running",
                    {
                        "current_step": step.id,
                        "step_status": "completed",
                    },
                )
                publish_nats_event(
                    "workflow.step.completed",
                    {
                        "execution_id": execution_id,
                        "step_id": step.id,
                        "step_name": step.name,
                    },
                )

            except Exception as step_error:
                error_msg = str(step_error)
                errors.append({step.id: error_msg})

                results[step.id] = {
                    "status": "failed",
                    "error": error_msg,
                }

                # Handle step failure
                if step.on_failure == "stop":
                    execution.status = "failed"
                    execution.errors = errors
                    execution.results = results
                    execution.completed_at = datetime.utcnow().isoformat()

                    update_redis_cache(
                        execution_id,
                        "failed",
                        {
                            "current_step": step.id,
                            "step_status": "failed",
                        },
                    )
                    publish_nats_event(
                        "workflow.failed",
                        {
                            "execution_id": execution_id,
                            "step_id": step.id,
                            "error": error_msg,
                        },
                    )

                    return {
                        "status": "failed",
                        "execution_id": execution_id,
                        "failed_at_step": step.id,
                        "errors": errors,
                    }

                elif step.on_failure == "continue":
                    # Continue to next step
                    continue

                elif step.on_failure == "rollback":
                    # Trigger rollback
                    execution.status = "rolling_back"
                    execution.errors = errors
                    update_redis_cache(
                        execution_id,
                        "rolling_back",
                        {
                            "current_step": step.id,
                            "step_status": "failed",
                            "rollback_triggered": True,
                        },
                    )
                    publish_nats_event(
                        "workflow.rollback_started",
                        {
                            "execution_id": execution_id,
                            "step_id": step.id,
                        },
                    )

                    return {
                        "status": "rolling_back",
                        "execution_id": execution_id,
                        "rollback_triggered": True,
                    }

        # Check if all steps completed
        if errors:
            # Some steps failed but execution continued
            execution.status = "failed"
        else:
            execution.status = "completed"

        execution.results = results
        execution.completed_at = datetime.utcnow().isoformat()

        # Final update
        update_redis_cache(
            execution_id,
            execution.status,
            {
                "current_step": None,
                "completed": True,
            },
        )
        publish_nats_event(
            "workflow.completed",
            {
                "execution_id": execution_id,
                "workflow_id": workflow_id,
                "status": execution.status,
            },
        )

        logger.info(
            "workflow_task_completed",
            task_id=self.request.id,
            execution_id=execution_id,
            status=execution.status,
        )

        return {
            "status": execution.status,
            "execution_id": execution_id,
            "results": results,
            "errors": errors,
        }

    except Exception as e:
        logger.error(
            "workflow_task_failed",
            task_id=self.request.id,
            error=str(e),
        )

        # Retry with exponential backoff
        retry_delay = 2**self.request.retries * 60
        raise self.retry(exc=e, countdown=retry_delay)


@celery_app.task(bind=True, max_retries=3, acks_late=True)
def execute_step_task(self, step_id: str, execution_id: str) -> Dict[str, Any]:
    """Execute a single workflow step.

    Args:
        step_id: The step ID to execute
        execution_id: The execution context ID

    Returns:
        Dictionary containing step execution result
    """
    logger.info(
        "step_task_started",
        task_id=self.request.id,
        step_id=step_id,
        execution_id=execution_id,
    )

    try:
        # Find the step in any workflow definition
        step = None

        for wf in workflow_definitions.values():
            for s in wf.steps:
                if s.id == step_id:
                    step = s
                    break

        if step is None:
            raise ValueError(f"Step {step_id} not found")

        # Execute step synchronously
        result = execute_step_sync(step, workflow_executions.get(execution_id))

        logger.info(
            "step_task_completed",
            task_id=self.request.id,
            step_id=step_id,
            result=result,
        )

        return {
            "status": "completed",
            "step_id": step_id,
            "execution_id": execution_id,
            "result": result,
        }

    except Exception as e:
        logger.error(
            "step_task_failed",
            task_id=self.request.id,
            step_id=step_id,
            error=str(e),
        )

        # Retry with exponential backoff
        retry_delay = 2**self.request.retries * 60
        raise self.retry(exc=e, countdown=retry_delay)


def execute_step_sync(step: Any, execution: Any) -> Dict[str, Any]:
    """Execute a single step synchronously using step handlers.

    Args:
        step: The step configuration
        execution: The execution context

    Returns:
        Step execution result
    """
    step_type = step.type
    config = step.config
    context = execution.context if execution else {}

    logger.info(
        "executing_step",
        step_id=step.id,
        step_type=step_type,
        step_name=step.name,
    )

    # Get step handlers
    handlers = get_step_handlers_registry()
    handler = handlers.get(step_type)

    if handler is None:
        raise ValueError(f"Unknown step type: {step_type}")

    # Validate step configuration
    if not asyncio.run(handler.validate(step)):
        raise ValueError(f"Invalid step configuration for type: {step_type}")

    # Execute step using handler
    step_dict = {
        "id": step.id,
        "type": step.type,
        "name": step.name,
        "config": config,
    }

    try:
        result = asyncio.run(handler.execute(step_dict, context))
        return result
    except Exception as e:
        logger.error(
            "step_execution_failed",
            step_id=step.id,
            step_type=step_type,
            error=str(e),
        )
        raise


@celery_app.task
def cleanup_stale_executions() -> Dict[str, Any]:
    """Clean up executions stuck in running state for more than 1 hour.

    Returns:
        Dictionary containing cleanup results
    """
    logger.info("cleanup_stale_executions_started")

    stale_threshold = datetime.utcnow() - timedelta(hours=1)
    stale_count = 0
    cleaned: list = []

    for execution_id, execution in workflow_executions.items():
        if execution.status == "running":
            started_at = execution.started_at
            if isinstance(started_at, str):
                started_at = datetime.fromisoformat(started_at)

            if started_at < stale_threshold:
                # Mark as failed with timeout
                execution.status = "failed"
                execution.errors = execution.errors or []
                execution.errors.append(
                    {
                        "type": "timeout",
                        "message": "Execution timed out after 1 hour",
                    }
                )
                execution.completed_at = datetime.utcnow().isoformat()

                stale_count += 1
                cleaned.append(execution_id)

                logger.info(
                    "stale_execution_cleaned",
                    execution_id=execution_id,
                    started_at=str(started_at),
                )

    # Publish cleanup event
    publish_nats_event(
        "workflow.cleanup.completed",
        {
            "stale_count": stale_count,
            "cleaned_executions": cleaned,
        },
    )

    logger.info(
        "cleanup_stale_executions_completed",
        stale_count=stale_count,
    )

    return {
        "stale_count": stale_count,
        "cleaned_executions": cleaned,
    }


@celery_app.task
def get_task_status(task_id: str) -> Dict[str, Any]:
    """Get the status of a Celery task.

    Args:
        task_id: The Celery task ID

    Returns:
        Dictionary containing task status
    """
    task = celery_app.AsyncResult(task_id)

    return {
        "task_id": task_id,
        "status": task.status,
        "result": task.result if task.ready() else None,
        "traceback": task.traceback if task.failed() else None,
    }
