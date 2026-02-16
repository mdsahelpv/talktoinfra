"""
Workflow Event Publisher

Publishes workflow events to NATS for real-time updates.
"""

from typing import Any, Dict, Optional
from nats_client import NATSClient
from events import (
    workflow_started_subject,
    workflow_completed_subject,
    workflow_failed_subject,
    step_started_subject,
    step_completed_subject,
    step_failed_subject,
    EVENT_WORKFLOW_STARTED,
    EVENT_WORKFLOW_COMPLETED,
    EVENT_WORKFLOW_FAILED,
    EVENT_STEP_STARTED,
    EVENT_STEP_COMPLETED,
    EVENT_STEP_FAILED,
    create_event_payload,
)


class WorkflowEventPublisher:
    """Publish workflow events to NATS."""

    def __init__(self, nats_client: Optional[NATSClient] = None):
        """Initialize the event publisher.

        Args:
            nats_client: Optional NATS client instance
        """
        self._nats = nats_client

    def set_nats_client(self, nats_client: NATSClient) -> None:
        """Set the NATS client instance.

        Args:
            nats_client: The NATS client to use
        """
        self._nats = nats_client

    async def _publish(self, subject: str, payload: Dict[str, Any]) -> None:
        """Internal method to publish an event.

        Args:
            subject: NATS subject to publish to
            payload: Event payload to send
        """
        if self._nats is None:
            return

        await self._nats.publish(subject, payload)

    async def publish_workflow_started(
        self, workflow_id: str, execution_id: str
    ) -> None:
        """Publish workflow execution started event.

        Args:
            workflow_id: The workflow ID
            execution_id: The execution ID
        """
        subject = workflow_started_subject(workflow_id)
        payload = create_event_payload(
            event_type=EVENT_WORKFLOW_STARTED,
            workflow_id=workflow_id,
            execution_id=execution_id,
        )
        await self._publish(subject, payload)

    async def publish_workflow_completed(
        self, workflow_id: str, execution_id: str, duration_seconds: float
    ) -> None:
        """Publish workflow completed event.

        Args:
            workflow_id: The workflow ID
            execution_id: The execution ID
            duration_seconds: Total execution duration in seconds
        """
        subject = workflow_completed_subject(workflow_id)
        payload = create_event_payload(
            event_type=EVENT_WORKFLOW_COMPLETED,
            workflow_id=workflow_id,
            execution_id=execution_id,
            additional_data={"duration_seconds": duration_seconds},
        )
        await self._publish(subject, payload)

    async def publish_workflow_failed(
        self, workflow_id: str, execution_id: str, error: str
    ) -> None:
        """Publish workflow failed event.

        Args:
            workflow_id: The workflow ID
            execution_id: The execution ID
            error: Error message
        """
        subject = workflow_failed_subject(workflow_id)
        payload = create_event_payload(
            event_type=EVENT_WORKFLOW_FAILED,
            workflow_id=workflow_id,
            execution_id=execution_id,
            additional_data={"error": error},
        )
        await self._publish(subject, payload)

    async def publish_step_started(
        self,
        workflow_id: str,
        execution_id: str,
        step_id: str,
        step_name: str,
    ) -> None:
        """Publish step started event.

        Args:
            workflow_id: The workflow ID
            execution_id: The execution ID
            step_id: The step ID
            step_name: The step name
        """
        subject = step_started_subject(workflow_id, step_id)
        payload = create_event_payload(
            event_type=EVENT_STEP_STARTED,
            workflow_id=workflow_id,
            execution_id=execution_id,
            additional_data={"step_id": step_id, "step_name": step_name},
        )
        await self._publish(subject, payload)

    async def publish_step_completed(
        self,
        workflow_id: str,
        execution_id: str,
        step_id: str,
        result: Dict[str, Any],
    ) -> None:
        """Publish step completed event.

        Args:
            workflow_id: The workflow ID
            execution_id: The execution ID
            step_id: The step ID
            result: Step execution result
        """
        subject = step_completed_subject(workflow_id, step_id)
        payload = create_event_payload(
            event_type=EVENT_STEP_COMPLETED,
            workflow_id=workflow_id,
            execution_id=execution_id,
            additional_data={"step_id": step_id, "result": result},
        )
        await self._publish(subject, payload)

    async def publish_step_failed(
        self,
        workflow_id: str,
        execution_id: str,
        step_id: str,
        error: str,
    ) -> None:
        """Publish step failed event.

        Args:
            workflow_id: The workflow ID
            execution_id: The execution ID
            step_id: The step ID
            error: Error message
        """
        subject = step_failed_subject(workflow_id, step_id)
        payload = create_event_payload(
            event_type=EVENT_STEP_FAILED,
            workflow_id=workflow_id,
            execution_id=execution_id,
            additional_data={"step_id": step_id, "error": error},
        )
        await self._publish(subject, payload)


# Global event publisher instance
_event_publisher: Optional[WorkflowEventPublisher] = None


def get_event_publisher() -> WorkflowEventPublisher:
    """Get or create the global event publisher instance.

    Returns:
        WorkflowEventPublisher instance
    """
    global _event_publisher
    if _event_publisher is None:
        _event_publisher = WorkflowEventPublisher()
    return _event_publisher


def set_event_publisher(publisher: WorkflowEventPublisher) -> None:
    """Set the global event publisher instance.

    Args:
        publisher: The event publisher to set
    """
    global _event_publisher
    _event_publisher = publisher
