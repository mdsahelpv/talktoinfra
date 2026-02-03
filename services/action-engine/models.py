"""
Pydantic models for Action Engine service.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ActionStatus(str, Enum):
    """Action execution status."""

    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ActionRequest(BaseModel):
    """Action execution request."""

    action: str = Field(..., min_length=1, max_length=1000, description="Action type")
    target: str = Field(
        ..., min_length=1, max_length=500, description="Target resource"
    )
    parameters: Dict[str, Any] = Field(default={}, description="Action parameters")
    user_id: str = Field(..., description="Requesting user ID")
    user_roles: List[str] = Field(default=[], description="User roles")
    justification: Optional[str] = Field(None, description="Business justification")


class DryRunChange(BaseModel):
    """A single change predicted by dry-run."""

    operation: str = Field(..., description="Operation type (create, update, delete)")
    resource_type: str = Field(..., description="Type of resource")
    resource_id: str = Field(..., description="Resource identifier")
    before: Optional[Dict[str, Any]] = Field(None, description="State before change")
    after: Optional[Dict[str, Any]] = Field(None, description="State after change")
    field_changes: List[Dict[str, Any]] = Field(
        default=[], description="Detailed field changes"
    )


class DryRunResult(BaseModel):
    """Result of dry-run execution."""

    success: bool = Field(..., description="Whether dry-run succeeded")
    changes: List[DryRunChange] = Field(default=[], description="Predicted changes")
    warnings: List[str] = Field(default=[], description="Warning messages")
    errors: List[str] = Field(default=[], description="Error messages")
    preview: Optional[str] = Field(None, description="Human-readable preview")
    estimated_duration: Optional[float] = Field(
        None, description="Estimated execution time in seconds"
    )
    resources_affected: int = Field(
        default=0, description="Number of resources affected"
    )


class ActionExecutionResult(BaseModel):
    """Result of action execution."""

    success: bool = Field(..., description="Whether execution succeeded")
    output: Optional[str] = Field(None, description="Command output")
    exit_code: Optional[int] = Field(None, description="Exit code")
    duration_seconds: float = Field(..., description="Execution duration")
    resources_modified: List[Dict[str, Any]] = Field(
        default=[], description="Modified resources"
    )
    logs: List[str] = Field(default=[], description="Execution logs")
    metadata: Dict[str, Any] = Field(default={}, description="Additional metadata")


class RollbackResult(BaseModel):
    """Result of rollback operation."""

    success: bool = Field(..., description="Whether rollback succeeded")
    rollback_point_id: str = Field(..., description="Rollback point identifier")
    restored_resources: List[Dict[str, Any]] = Field(
        default=[], description="Restored resources"
    )
    errors: List[str] = Field(default=[], description="Rollback errors")
    duration_seconds: float = Field(..., description="Rollback duration")


class ActionResponse(BaseModel):
    """Action response model."""

    action_id: str = Field(..., description="Unique action identifier")
    status: ActionStatus = Field(..., description="Current action status")
    action: str = Field(..., description="Action type")
    target: str = Field(..., description="Target resource")
    parameters: Dict[str, Any] = Field(default={}, description="Action parameters")
    dry_run_result: Optional[DryRunResult] = Field(None, description="Dry-run results")
    requires_approval: bool = Field(
        default=False, description="Whether approval is required"
    )
    approvers: List[str] = Field(default=[], description="List of required approvers")
    approved_by: Optional[str] = Field(None, description="User who approved")
    approved_at: Optional[datetime] = Field(None, description="Approval timestamp")
    requested_by: str = Field(..., description="User who requested")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = Field(None, description="Execution start time")
    completed_at: Optional[datetime] = Field(
        None, description="Execution completion time"
    )
    result: Optional[ActionExecutionResult] = Field(
        None, description="Execution result"
    )
    error: Optional[str] = Field(None, description="Error message if failed")
    rollback_point_id: Optional[str] = Field(None, description="Rollback point ID")
    rolled_back_at: Optional[datetime] = Field(None, description="Rollback timestamp")
    rolled_back_by: Optional[str] = Field(
        None, description="User who performed rollback"
    )
    justification: Optional[str] = Field(None, description="Business justification")


class SandboxExecutionResult(BaseModel):
    """Result of sandbox execution."""

    success: bool = Field(..., description="Whether sandbox execution succeeded")
    output: str = Field(default="", description="Execution output")
    errors: List[str] = Field(default=[], description="Execution errors")
    isolated: bool = Field(default=True, description="Whether execution was isolated")
    resources_used: Dict[str, Any] = Field(
        default={}, description="Resource usage stats"
    )
