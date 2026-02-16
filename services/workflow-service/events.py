"""
NATS Event Subjects for Workflow Events

Defines NATS subject patterns for workflow event publishing.
"""

from typing import Dict, Optional


# NATS subject patterns for workflow events
WORKFLOW_EVENTS = "workflow.events.{workflow_id}"
WORKFLOW_STARTED = "workflow.events.{workflow_id}.started"
WORKFLOW_COMPLETED = "workflow.events.{workflow_id}.completed"
WORKFLOW_FAILED = "workflow.events.{workflow_id}.failed"
STEP_EVENTS = "workflow.events.{workflow_id}.step.{step_id}"
STEP_STARTED = "workflow.events.{workflow_id}.step.{step_id}.started"
STEP_COMPLETED = "workflow.events.{workflow_id}.step.{step_id}.completed"
STEP_FAILED = "workflow.events.{workflow_id}.step.{step_id}.failed"
EXECUTION_EVENTS = "workflow.executions"


def format_subject(subject: str, **kwargs: str) -> str:
    """Format a subject pattern with values.

    Args:
        subject: Subject pattern with placeholders
        **kwargs: Values to substitute into placeholders

    Returns:
        Formatted subject string
    """
    result = subject
    for key, value in kwargs.items():
        result = result.replace(f"{{{key}}}", value)
    return result


def workflow_started_subject(workflow_id: str) -> str:
    """Get subject for workflow started event.

    Args:
        workflow_id: The workflow ID

    Returns:
        Formatted subject string
    """
    return format_subject(WORKFLOW_STARTED, workflow_id=workflow_id)


def workflow_completed_subject(workflow_id: str) -> str:
    """Get subject for workflow completed event.

    Args:
        workflow_id: The workflow ID

    Returns:
        Formatted subject string
    """
    return format_subject(WORKFLOW_COMPLETED, workflow_id=workflow_id)


def workflow_failed_subject(workflow_id: str) -> str:
    """Get subject for workflow failed event.

    Args:
        workflow_id: The workflow ID

    Returns:
        Formatted subject string
    """
    return format_subject(WORKFLOW_FAILED, workflow_id=workflow_id)


def step_started_subject(workflow_id: str, step_id: str) -> str:
    """Get subject for step started event.

    Args:
        workflow_id: The workflow ID
        step_id: The step ID

    Returns:
        Formatted subject string
    """
    return format_subject(STEP_STARTED, workflow_id=workflow_id, step_id=step_id)


def step_completed_subject(workflow_id: str, step_id: str) -> str:
    """Get subject for step completed event.

    Args:
        workflow_id: The workflow ID
        step_id: The step ID

    Returns:
        Formatted subject string
    """
    return format_subject(STEP_COMPLETED, workflow_id=workflow_id, step_id=step_id)


def step_failed_subject(workflow_id: str, step_id: str) -> str:
    """Get subject for step failed event.

    Args:
        workflow_id: The workflow ID
        step_id: The step ID

    Returns:
        Formatted subject string
    """
    return format_subject(STEP_FAILED, workflow_id=workflow_id, step_id=step_id)


# Event type constants
EVENT_WORKFLOW_STARTED = "workflow.started"
EVENT_WORKFLOW_COMPLETED = "workflow.completed"
EVENT_WORKFLOW_FAILED = "workflow.failed"
EVENT_STEP_STARTED = "workflow.step.started"
EVENT_STEP_COMPLETED = "workflow.step.completed"
EVENT_STEP_FAILED = "workflow.step.failed"


def create_event_payload(
    event_type: str,
    workflow_id: str,
    execution_id: str,
    additional_data: Optional[Dict[str, object]] = None,
) -> Dict[str, object]:
    """Create an event payload.

    Args:
        event_type: Type of event
        workflow_id: The workflow ID
        execution_id: The execution ID
        additional_data: Additional data to include

    Returns:
        Event payload dictionary
    """
    payload: Dict[str, object] = {
        "event_type": event_type,
        "workflow_id": workflow_id,
        "execution_id": execution_id,
    }
    if additional_data:
        payload.update(additional_data)
    return payload
