"""
Shared Event Schemas for TalkAI Platform

Defines event types and subjects for cross-service communication via NATS.
"""

from typing import Dict, Optional, Any
from datetime import datetime
from enum import Enum


# Event type constants
class EventType(str, Enum):
    """Event types for the platform."""
    # Workflow events
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"
    WORKFLOW_STEP_STARTED = "workflow.step.started"
    WORKFLOW_STEP_COMPLETED = "workflow.step.completed"
    WORKFLOW_STEP_FAILED = "workflow.step.failed"
    
    # Discovery events
    DISCOVERY_SCAN_STARTED = "discovery.scan.started"
    DISCOVERY_SCAN_COMPLETED = "discovery.scan.completed"
    DISCOVERY_SCAN_FAILED = "discovery.scan.failed"
    RESOURCE_DISCOVERED = "resource.discovered"
    RESOURCE_UPDATED = "resource.updated"
    RESOURCE_DELETED = "resource.deleted"
    
    # Infrastructure events
    INFRASTRUCTURE_CREATED = "infrastructure.created"
    INFRASTRUCTURE_UPDATED = "infrastructure.updated"
    INFRASTRUCTURE_DELETED = "infrastructure.deleted"
    
    # Monitoring events
    METRICS_COLLECTED = "metrics.collected"
    ALERT_TRIGGERED = "alert.triggered"
    ALERT_RESOLVED = "alert.resolved"
    HEALTH_CHECK_FAILED = "health.check.failed"
    
    # RAG events
    RAG_INDEX_STARTED = "rag.index.started"
    RAG_INDEX_COMPLETED = "rag.index.completed"
    RAG_INDEX_FAILED = "rag.index.failed"
    
    # Action events
    ACTION_STARTED = "action.started"
    ACTION_COMPLETED = "action.completed"
    ACTION_FAILED = "action.failed"
    ACTION_APPROVAL_REQUIRED = "action.approval.required"
    ACTION_APPROVED = "action.approved"
    ACTION_REJECTED = "action.rejected"
    
    # Onboarding events
    CLUSTER_ONBOARDED = "cluster.onboarded"
    CLUSTER_REMOVED = "cluster.removed"
    CONNECTION_TESTED = "connection.tested"


# NATS subject patterns
class EventSubjects:
    """NATS subject patterns for events."""
    # Workflow subjects
    WORKFLOW_EVENTS = "workflow.events.{workflow_id}"
    WORKFLOW_STARTED = "workflow.events.{workflow_id}.started"
    WORKFLOW_COMPLETED = "workflow.events.{workflow_id}.completed"
    WORKFLOW_FAILED = "workflow.events.{workflow_id}.failed"
    STEP_EVENTS = "workflow.events.{workflow_id}.step.{step_id}"
    STEP_STARTED = "workflow.events.{workflow_id}.step.{step_id}.started"
    STEP_COMPLETED = "workflow.events.{workflow_id}.step.{step_id}.completed"
    STEP_FAILED = "workflow.events.{workflow_id}.step.{step_id}.failed"
    WORKFLOW_EXECUTION = "workflow.executions"
    
    # Discovery subjects
    DISCOVERY_SCAN = "discovery.scan"
    DISCOVERY_SCAN_STARTED = "discovery.scan.started"
    DISCOVERY_SCAN_COMPLETED = "discovery.scan.completed"
    DISCOVERY_SCAN_FAILED = "discovery.scan.failed"
    RESOURCE_DISCOVERED = "resource.discovered"
    RESOURCE_UPDATED = "resource.updated"
    RESOURCE_DELETED = "resource.deleted"
    
    # Infrastructure subjects
    INFRASTRUCTURE = "infrastructure"
    INFRASTRUCTURE_CREATED = "infrastructure.created"
    INFRASTRUCTURE_UPDATED = "infrastructure.updated"
    INFRASTRUCTURE_DELETED = "infrastructure.deleted"
    
    # Monitoring subjects
    METRICS = "monitoring.metrics"
    METRICS_COLLECTED = "monitoring.metrics.collected"
    ALERTS = "monitoring.alerts"
    ALERT_TRIGGERED = "monitoring.alerts.triggered"
    ALERT_RESOLVED = "monitoring.alerts.resolved"
    HEALTH = "monitoring.health"
    HEALTH_CHECK_FAILED = "monitoring.health.check.failed"
    
    # RAG subjects
    RAG_INDEX = "rag.index"
    RAG_INDEX_STARTED = "rag.index.started"
    RAG_INDEX_COMPLETED = "rag.index.completed"
    RAG_INDEX_FAILED = "rag.index.failed"
    
    # Action subjects
    ACTIONS = "actions"
    ACTION_STARTED = "actions.started"
    ACTION_COMPLETED = "actions.completed"
    ACTION_FAILED = "actions.failed"
    ACTION_APPROVAL = "actions.approval"
    ACTION_APPROVAL_REQUIRED = "actions.approval.required"
    ACTION_APPROVED = "actions.approved"
    ACTION_REJECTED = "actions.rejected"
    
    # Onboarding subjects
    ONBOARDING = "onboarding"
    CLUSTER_ONBOARDED = "onboarding.cluster.onboarded"
    CLUSTER_REMOVED = "onboarding.cluster.removed"
    CONNECTION_TESTED = "onboarding.connection.tested"


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


def create_event_payload(
    event_type: str,
    source_service: str,
    data: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a standardized event payload.

    Args:
        event_type: Type of event
        source_service: Service that generated the event
        data: Event data
        correlation_id: Optional correlation ID for tracing

    Returns:
        Event payload dictionary
    """
    payload: Dict[str, Any] = {
        "event_type": event_type,
        "source_service": source_service,
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    if correlation_id:
        payload["correlation_id"] = correlation_id
    
    if data:
        payload["data"] = data
    
    return payload


# Workflow event helpers
def workflow_started_subject(workflow_id: str) -> str:
    """Get subject for workflow started event."""
    return format_subject(EventSubjects.WORKFLOW_STARTED, workflow_id=workflow_id)


def workflow_completed_subject(workflow_id: str) -> str:
    """Get subject for workflow completed event."""
    return format_subject(EventSubjects.WORKFLOW_COMPLETED, workflow_id=workflow_id)


def workflow_failed_subject(workflow_id: str) -> str:
    """Get subject for workflow failed event."""
    return format_subject(EventSubjects.WORKFLOW_FAILED, workflow_id=workflow_id)


def step_started_subject(workflow_id: str, step_id: str) -> str:
    """Get subject for step started event."""
    return format_subject(EventSubjects.STEP_STARTED, workflow_id=workflow_id, step_id=step_id)


def step_completed_subject(workflow_id: str, step_id: str) -> str:
    """Get subject for step completed event."""
    return format_subject(EventSubjects.STEP_COMPLETED, workflow_id=workflow_id, step_id=step_id)


def step_failed_subject(workflow_id: str, step_id: str) -> str:
    """Get subject for step failed event."""
    return format_subject(EventSubjects.STEP_FAILED, workflow_id=workflow_id, step_id=step_id)
