"""
Pydantic models for Policy Engine service.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ApprovalStatus(str, Enum):
    """Approval status types."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class PolicyCheckRequest(BaseModel):
    """Policy check request."""

    action: str = Field(..., description="Action to check")
    target: str = Field(..., description="Target resource")
    user_id: str = Field(..., description="User ID")
    user_roles: List[str] = Field(default=[], description="User roles")
    parameters: Dict[str, Any] = Field(default={}, description="Action parameters")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class PolicyCheckResponse(BaseModel):
    """Policy check response."""

    allowed: bool = Field(..., description="Whether action is allowed")
    reason: Optional[str] = Field(None, description="Reason if not allowed")
    requires_approval: bool = Field(
        default=False, description="Whether approval is required"
    )
    approvers: List[str] = Field(default=[], description="List of required approvers")
    policy_version: str = Field(default="1.0", description="Policy version used")
    metadata: Dict[str, Any] = Field(default={}, description="Additional metadata")


class ApprovalResponse(BaseModel):
    """Approval request response."""

    approval_id: str = Field(..., description="Approval unique identifier")
    action_id: str = Field(..., description="Related action ID")
    action: str = Field(..., description="Action type")
    target: str = Field(..., description="Target resource")
    status: ApprovalStatus = Field(..., description="Current approval status")
    requested_by: str = Field(..., description="User who requested approval")
    approvers: List[str] = Field(default=[], description="List of potential approvers")
    approver_roles: List[str] = Field(default=[], description="Roles that can approve")
    approved_by: Optional[str] = Field(None, description="User who approved")
    approved_at: Optional[datetime] = Field(None, description="Approval timestamp")
    rejected_by: Optional[str] = Field(None, description="User who rejected")
    rejected_at: Optional[datetime] = Field(None, description="Rejection timestamp")
    rejection_reason: Optional[str] = Field(None, description="Rejection reason")
    notes: Optional[str] = Field(None, description="Additional notes")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(None, description="Approval expiration")


class ApprovalRequest(BaseModel):
    """Request to create an approval."""

    action_id: str = Field(..., description="Action to approve")
    approver_notes: Optional[str] = Field(None, description="Notes from approver")


class Permission(BaseModel):
    """Permission definition."""

    name: str = Field(..., description="Permission name")
    resource_type: str = Field(..., description="Type of resource")
    actions: List[str] = Field(..., description="Allowed actions")
    conditions: Dict[str, Any] = Field(default={}, description="Permission conditions")
    description: Optional[str] = Field(None, description="Permission description")


class Role(BaseModel):
    """Role definition."""

    name: str = Field(..., description="Role name")
    description: Optional[str] = Field(None, description="Role description")
    permissions: List[str] = Field(default=[], description="Permission names")
    level: int = Field(
        default=1, description="Role hierarchy level (higher = more privileged)"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UserRoleAssignment(BaseModel):
    """User role assignment."""

    user_id: str = Field(..., description="User ID")
    roles: List[str] = Field(default=[], description="Assigned roles")
    assigned_by: str = Field(..., description="Who assigned the roles")
    assigned_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(None, description="Role expiration")


class ApprovalChain(BaseModel):
    """Multi-level approval chain definition."""

    chain_id: str = Field(..., description="Chain unique identifier")
    name: str = Field(..., description="Chain name")
    description: Optional[str] = Field(None, description="Chain description")
    levels: List[Dict[str, Any]] = Field(..., description="Approval levels")
    conditions: Dict[str, Any] = Field(
        default={}, description="When to apply this chain"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ApprovalChainLevel(BaseModel):
    """Single level in an approval chain."""

    level: int = Field(..., description="Level number")
    required_approvals: int = Field(
        default=1, description="Required approvals at this level"
    )
    approvers: List[str] = Field(default=[], description="Specific approvers")
    approver_roles: List[str] = Field(default=[], description="Roles that can approve")
    any_of_roles: bool = Field(
        default=True, description="If True, any role can approve"
    )
    all_roles_required: bool = Field(
        default=False, description="If True, all listed roles must approve"
    )


class ResourcePolicy(BaseModel):
    """Policy for a specific resource or resource type."""

    policy_id: str = Field(..., description="Policy unique identifier")
    resource_type: str = Field(..., description="Resource type")
    resource_id: Optional[str] = Field(
        None, description="Specific resource ID (if applicable)"
    )
    environment: str = Field(..., description="Environment (dev, staging, production)")
    rules: List[Dict[str, Any]] = Field(..., description="Policy rules")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
