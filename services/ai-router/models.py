"""
Pydantic models for AI Router service.
Extended with conversation and workflow models.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field


class IntentType(str, Enum):
    """Intent classification types - extended for infrastructure operations."""

    QUERY = "QUERY"
    ACTION = "ACTION"
    DISCOVERY = "DISCOVERY"
    ONBOARDING = "ONBOARDING"
    MANAGEMENT = "MANAGEMENT"
    ANALYSIS = "ANALYSIS"
    HELP = "HELP"
    UNKNOWN = "UNKNOWN"


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


class MessageRole(str, Enum):
    """Message role types."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class IntentClassification(BaseModel):
    """Intent classification result - extended."""

    intent: IntentType = Field(..., description="Classified intent type")
    confidence: float = Field(..., ge=0.0, le=1.0,
                              description="Confidence score")
    entities: List[Dict[str, Any]] = Field(
        default=[], description="Extracted entities")
    action_type: Optional[str] = Field(
        None, description="Detected action type")
    target_resource: Optional[str] = Field(
        None, description="Target resource reference")
    requires_approval: bool = Field(
        default=False, description="Requires approval")
    risk_level: Optional[RiskLevel] = Field(None, description="Risk level")


class ConversationMessage(BaseModel):
    """Individual conversation message."""

    id: str = Field(..., description="Message unique ID")
    role: MessageRole = Field(..., description="Message role")
    content: str = Field(..., min_length=1, description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(
        default={}, description="Additional metadata")


class ConversationBase(BaseModel):
    """Conversation base model."""

    id: str = Field(..., description="Conversation unique identifier")
    user_id: str = Field(..., description="User identifier")
    title: Optional[str] = Field(None, description="Conversation title")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Conversation(ConversationBase):
    """Full conversation model with messages."""

    messages: List[ConversationMessage] = Field(
        default=[], description="Message history")
    state: ConversationState = Field(default=ConversationState.NEW)
    metadata: Dict[str, Any] = Field(
        default={}, description="Additional metadata")


class ConversationListItem(BaseModel):
    """Conversation list item (without messages)."""

    id: str
    user_id: str
    title: Optional[str]
    message_count: int = Field(0, description="Number of messages")
    state: ConversationState
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConversationCreateRequest(BaseModel):
    """Request to create a new conversation."""

    user_id: str = Field(..., description="User identifier")
    title: Optional[str] = Field(None, description="Optional title")
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Optional metadata")


class QueryRequest(BaseModel):
    """Query request model."""

    query: str = Field(..., min_length=1, max_length=10000,
                       description="User query")
    conversation_id: Optional[str] = Field(
        None, description="Existing conversation ID")
    user_id: str = Field(..., description="User identifier")
    context: Optional[Dict[str, Any]] = Field(
        None, description="Additional context")


class SourceType(str, Enum):
    """Source type for retrieved information."""

    VECTOR_SEARCH = "vector_search"
    K8S_API = "k8s_api"
    CLOUD_API = "cloud_api"
    INTENT_CLASSIFICATION = "intent_classification"
    CONVERSATION_HISTORY = "conversation_history"


class QuerySource(BaseModel):
    """Source of information for query response."""

    type: SourceType = Field(..., description="Source type")
    resource_id: Optional[str] = Field(None, description="Resource identifier")
    resource_type: Optional[str] = Field(None, description="Resource type")
    confidence: float = Field(..., ge=0.0, le=1.0,
                              description="Confidence score")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata")


class QueryResponse(BaseModel):
    """Query response model."""

    response: str = Field(..., description="Generated response text")
    conversation_id: str = Field(..., description="Conversation identifier")
    intent: IntentClassification = Field(...,
                                         description="Intent classification")
    sources: List[QuerySource] = Field(
        default=[], description="Information sources")
    workflow_state: Optional[str] = Field(
        None, description="Workflow state if applicable")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Response metadata")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ActionApprovalRequest(BaseModel):
    """Request to create an approval for an action."""

    conversation_id: str = Field(..., description="Related conversation ID")
    user_id: str = Field(..., description="Requesting user")
    action_type: str = Field(..., description="Type of action")
    target_resources: List[str] = Field(
        default=[], description="Target resources")
    description: str = Field(..., description="Human-readable description")
    risk_level: RiskLevel = Field(..., description="Risk assessment")
    impact_summary: str = Field(..., description="Expected impact")
    rollback_plan: Optional[str] = Field(
        None, description="Rollback instructions")
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional metadata")


class ApprovalResponse(BaseModel):
    """Approval response model."""

    id: str = Field(..., description="Approval ID")
    conversation_id: str
    user_id: str
    action_type: str
    target_resources: List[str]
    description: str
    risk_level: RiskLevel
    impact_summary: str
    status: ApprovalStatus
    created_at: datetime
    expires_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ApprovalActionRequest(BaseModel):
    """Request to approve or reject an action."""

    approval_id: str = Field(..., description="Approval ID")
    action: str = Field(..., description="Action: approve or reject")
    reason: Optional[str] = Field(None, description="Reason for decision")


class ConversationWithMessages(BaseModel):
    """Conversation with messages for frontend."""

    id: str
    user_id: str
    title: Optional[str]
    messages: List[ConversationMessage]
    state: ConversationState
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StreamChunk(BaseModel):
    """Streaming response chunk."""

    chunk: str
    done: bool = False


class RAGDocument(BaseModel):
    """RAG retrieved document."""

    id: str = Field(..., description="Document identifier")
    score: float = Field(..., ge=0.0, le=1.0, description="Similarity score")
    payload: Dict[str, Any] = Field(
        default_factory=dict, description="Document payload")
    resource_type: Optional[str] = Field(None, description="Resource type")


class LLMResponse(BaseModel):
    """LLM generation response."""

    text: str = Field(..., description="Generated text")
    model: str = Field(..., description="Model used for generation")
    tokens_used: Optional[int] = Field(None, description="Tokens consumed")
    finish_reason: Optional[str] = Field(
        None, description="Reason for completion")


class HealthStatus(BaseModel):
    """Health check status."""

    status: str = Field(..., description="Health status")
    service: str = Field(..., description="Service name")
    timestamp: float = Field(..., description="Timestamp")
    components: Dict[str, str] = Field(
        default_factory=dict, description="Component statuses")
