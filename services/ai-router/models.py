"""
Pydantic models for AI Router service.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field


class IntentType(str, Enum):
    """Intent classification types."""

    QUERY = "QUERY"
    ACTION = "ACTION"
    ANALYSIS = "ANALYSIS"
    HELP = "HELP"
    UNKNOWN = "UNKNOWN"


class MessageRole(str, Enum):
    """Message role types."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class IntentClassification(BaseModel):
    """Intent classification result."""

    intent: IntentType = Field(..., description="Classified intent type")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    entities: List[Dict[str, Any]] = Field(default=[], description="Extracted entities")
    action_type: Optional[str] = Field(None, description="Detected action type")
    target_resource: Optional[str] = Field(
        None, description="Target resource reference"
    )


class ConversationMessage(BaseModel):
    """Individual conversation message."""

    role: MessageRole = Field(..., description="Message role")
    content: str = Field(..., min_length=1, description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default={}, description="Additional metadata")


class ConversationContext(BaseModel):
    """Conversation context information."""

    id: str = Field(..., description="Conversation unique identifier")
    user_id: str = Field(..., description="User identifier")
    title: Optional[str] = Field(None, description="Conversation title")
    messages: List[ConversationMessage] = Field(
        default=[], description="Message history"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default={}, description="Additional metadata")


class QueryRequest(BaseModel):
    """Query request model."""

    query: str = Field(..., min_length=1, max_length=10000, description="User query")
    conversation_id: Optional[str] = Field(None, description="Existing conversation ID")
    user_id: str = Field(..., description="User identifier")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


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
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    metadata: Dict[str, Any] = Field(default={}, description="Additional metadata")


class QueryResponse(BaseModel):
    """Query response model."""

    response: str = Field(..., description="Generated response text")
    conversation_id: str = Field(..., description="Conversation identifier")
    sources: List[QuerySource] = Field(default=[], description="Information sources")
    metadata: Dict[str, Any] = Field(default={}, description="Response metadata")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class RAGDocument(BaseModel):
    """RAG retrieved document."""

    id: str = Field(..., description="Document identifier")
    score: float = Field(..., ge=0.0, le=1.0, description="Similarity score")
    payload: Dict[str, Any] = Field(default={}, description="Document payload")
    resource_type: Optional[str] = Field(None, description="Resource type")


class LLMResponse(BaseModel):
    """LLM generation response."""

    text: str = Field(..., description="Generated text")
    model: str = Field(..., description="Model used for generation")
    tokens_used: Optional[int] = Field(None, description="Tokens consumed")
    finish_reason: Optional[str] = Field(None, description="Reason for completion")


class HealthStatus(BaseModel):
    """Health check status."""

    status: str = Field(..., description="Health status")
    service: str = Field(..., description="Service name")
    timestamp: float = Field(..., description="Timestamp")
    components: Dict[str, str] = Field(default={}, description="Component statuses")
