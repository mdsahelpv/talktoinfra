"""
Conversation state machine models.
Defines workflow states and transitions for chat conversations.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field


class ConversationState(str, Enum):
    """Conversation workflow states."""

    NEW = "NEW"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    PROCESSING = "PROCESSING"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class RiskLevel(str, Enum):
    """Risk assessment levels for actions."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ApprovalStatus(str, Enum):
    """Approval workflow status."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class TransitionResult(BaseModel):
    """Result of a state transition."""

    from_state: ConversationState
    to_state: ConversationState
    success: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    reason: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ActionApproval(BaseModel):
    """Action approval request."""

    id: str = Field(..., description="Approval request ID")
    conversation_id: str = Field(..., description="Related conversation ID")
    user_id: str = Field(..., description="Requesting user")
    action_type: str = Field(..., description="Type of action")
    target_resources: List[str] = Field(default=[], description="Target resource names")
    description: str = Field(..., description="Human-readable description")
    risk_level: RiskLevel = Field(..., description="Risk assessment")
    impact_summary: str = Field(..., description="Expected impact")
    rollback_plan: Optional[str] = Field(None, description="Rollback instructions")
    status: ApprovalStatus = Field(default=ApprovalStatus.PENDING)
    approver_id: Optional[str] = Field(None, description="Approver user ID")
    approved_at: Optional[datetime] = Field(None)
    rejected_at: Optional[datetime] = Field(None)
    rejection_reason: Optional[str] = Field(None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(..., description="Approval expiration")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConversationWorkflow(BaseModel):
    """Full conversation workflow state."""

    conversation_id: str
    current_state: ConversationState = Field(default=ConversationState.NEW)
    intent_type: Optional[str] = None
    target_resources: List[str] = Field(default=[])
    approval_id: Optional[str] = None
    retry_count: int = Field(default=0)
    max_retries: int = Field(default=3)
    error_message: Optional[str] = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def transition(
        self, new_state: ConversationState, reason: Optional[str] = None
    ) -> TransitionResult:
        """Attempt state transition."""
        valid_transitions = {
            ConversationState.NEW: [
                ConversationState.ACKNOWLEDGED,
                ConversationState.CANCELLED,
            ],
            ConversationState.ACKNOWLEDGED: [
                ConversationState.PROCESSING,
                ConversationState.CANCELLED,
            ],
            ConversationState.PROCESSING: [
                ConversationState.PENDING_APPROVAL,
                ConversationState.EXECUTING,
                ConversationState.COMPLETED,
                ConversationState.FAILED,
                ConversationState.CANCELLED,
            ],
            ConversationState.PENDING_APPROVAL: [
                ConversationState.EXECUTING,
                ConversationState.CANCELLED,
                ConversationState.FAILED,
            ],
            ConversationState.EXECUTING: [
                ConversationState.COMPLETED,
                ConversationState.FAILED,
            ],
            ConversationState.FAILED: [ConversationState.NEW],  # Allow retry
        }

        from_state = self.current_state

        if new_state not in valid_transitions.get(from_state, []):
            return TransitionResult(
                from_state=from_state,
                to_state=new_state,
                success=False,
                reason=f"Invalid transition from {from_state.value} to {new_state.value}",
            )

        self.current_state = new_state

        if new_state in [
            ConversationState.COMPLETED,
            ConversationState.FAILED,
            ConversationState.CANCELLED,
        ]:
            self.completed_at = datetime.utcnow()

        return TransitionResult(
            from_state=from_state,
            to_state=new_state,
            success=True,
            reason=reason,
        )

    def can_proceed(self) -> bool:
        """Check if conversation can proceed to next state."""
        return self.current_state not in [
            ConversationState.COMPLETED,
            ConversationState.FAILED,
            ConversationState.CANCELLED,
        ]

    def needs_approval(self) -> bool:
        """Check if current state requires approval."""
        return self.current_state == ConversationState.PENDING_APPROVAL


class QueryContext(BaseModel):
    """Context for query processing."""

    conversation_id: str
    intent_type: str
    original_query: str
    entities: List[Dict[str, Any]] = Field(default=[])
    retrieved_documents: List[Dict[str, Any]] = Field(default=[])
    confidence_score: float = Field(default=0.0)
    suggested_actions: List[str] = Field(default=[])
    requires_approval: bool = Field(default=False)
    risk_level: Optional[RiskLevel] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkflowEvent(BaseModel):
    """Workflow event for audit trail."""

    id: str
    conversation_id: str
    event_type: str
    state: ConversationState
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    actor_id: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
