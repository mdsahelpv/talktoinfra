"""
Shared Pydantic schemas for all microservices.
Provides type safety and API consistency across the platform.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class IntentType(str, Enum):
    """Classification of user query intents."""

    QUERY = "QUERY"  # Information retrieval
    ACTION = "ACTION"  # Infrastructure modification
    ANALYSIS = "ANALYSIS"  # Data analysis/insights
    HELP = "HELP"  # Help/documentation
    UNKNOWN = "UNKNOWN"  # Unclassified


class ActionType(str, Enum):
    """Types of infrastructure actions."""

    RESTART = "restart"
    SCALE = "scale"
    DELETE = "delete"
    CREATE = "create"
    UPDATE = "update"
    PATCH = "patch"
    ROLLBACK = "rollback"
    DEPLOY = "deploy"


class ResourceType(str, Enum):
    """Types of infrastructure resources."""

    POD = "pod"
    DEPLOYMENT = "deployment"
    SERVICE = "service"
    NODE = "node"
    NAMESPACE = "namespace"
    CONFIGMAP = "configmap"
    SECRET = "secret"
    INGRESS = "ingress"
    JOB = "job"
    CRONJOB = "cronjob"
    STATEFULSET = "statefulset"
    DAEMONSET = "daemonset"


class Role(str, Enum):
    """RBAC roles."""

    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    SENIOR_ENGINEER = "senior_engineer"
    ENGINEER = "engineer"
    READ_ONLY = "read_only"
    AUDITOR = "auditor"


class ApprovalStatus(str, Enum):
    """Approval workflow statuses."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ActionStatus(str, Enum):
    """Action execution statuses."""

    PENDING = "pending"
    DRY_RUN = "dry_run"
    APPROVAL_REQUIRED = "approval_required"
    APPROVED = "approved"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


# User & Auth Models


class UserBase(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str
    roles: List[Role] = [Role.ENGINEER]


class User(UserBase):
    id: str
    roles: List[Role]
    is_active: bool = True
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# Query Models


class QueryRequest(BaseModel):
    query: str = Field(
        ..., min_length=1, max_length=10000, description="Natural language query"
    )
    conversation_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class QuerySource(BaseModel):
    type: str  # vector_search, k8s_api, etc.
    resource_id: Optional[str] = None
    resource_type: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    metadata: Dict[str, Any] = {}


class QueryResponse(BaseModel):
    response: str
    conversation_id: str
    sources: List[QuerySource] = []
    intent: IntentType
    confidence: float
    metadata: Dict[str, Any] = {}
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Intent Classification Models


class Entity(BaseModel):
    type: str
    value: str
    start: Optional[int] = None
    end: Optional[int] = None
    confidence: float = 0.8


class IntentClassification(BaseModel):
    intent: IntentType
    confidence: float = Field(..., ge=0.0, le=1.0)
    entities: List[Entity] = []
    action_type: Optional[ActionType] = None
    target_resource: Optional[str] = None
    target_resource_type: Optional[ResourceType] = None


# Action Models


class ActionRequest(BaseModel):
    action: str = Field(..., min_length=1, max_length=1000)
    target: str = Field(..., min_length=1, max_length=500)
    resource_type: ResourceType
    namespace: Optional[str] = "default"
    parameters: Dict[str, Any] = {}
    dry_run: bool = True
    justification: Optional[str] = None


class DryRunResult(BaseModel):
    success: bool
    changes: List[Dict[str, Any]] = []
    warnings: List[str] = []
    errors: List[str] = []
    preview: Optional[str] = None
    affected_resources: List[str] = []
    estimated_impact: Optional[str] = None


class ActionResponse(BaseModel):
    action_id: str
    status: ActionStatus
    dry_run_result: Optional[DryRunResult] = None
    requires_approval: bool = False
    approval_id: Optional[str] = None
    approvers: List[str] = []
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    executed_by: Optional[str] = None
    executed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Approval Models


class ApprovalRequest(BaseModel):
    action_id: str
    notes: Optional[str] = None


class ApprovalResponse(BaseModel):
    approval_id: str
    action_id: str
    status: ApprovalStatus
    requested_by: str
    requester_roles: List[Role]
    approvers: List[str]
    approved_by: Optional[str] = None
    rejected_by: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    decided_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


# RBAC Models


class PermissionCheckRequest(BaseModel):
    user_id: str
    user_roles: List[Role]
    action: ActionType
    resource_type: ResourceType
    resource_id: Optional[str] = None
    namespace: Optional[str] = None


class PermissionCheckResponse(BaseModel):
    allowed: bool
    reason: Optional[str] = None
    requires_approval: bool = False
    min_approval_level: int = 0


# Audit Models


class AuditEvent(BaseModel):
    event_id: str
    timestamp: datetime
    event_type: str  # query, action, approval, login, etc.
    user_id: str
    user_roles: List[Role]
    action: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    details: Dict[str, Any] = {}
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None


class AuditQueryRequest(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    user_id: Optional[str] = None
    event_type: Optional[str] = None
    resource_type: Optional[str] = None
    limit: int = 100
    offset: int = 0


class AuditQueryResponse(BaseModel):
    events: List[AuditEvent]
    total: int
    limit: int
    offset: int


# Resource Models


class Resource(BaseModel):
    id: str
    name: str
    resource_type: ResourceType
    namespace: Optional[str] = None
    cluster: Optional[str] = None
    labels: Dict[str, str] = {}
    annotations: Dict[str, str] = {}
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    spec: Optional[Dict[str, Any]] = None
    raw_manifest: Optional[Dict[str, Any]] = None


class ResourceSearchRequest(BaseModel):
    query: str
    resource_types: Optional[List[ResourceType]] = None
    namespaces: Optional[List[str]] = None
    limit: int = 10


class ResourceSearchResult(BaseModel):
    resource: Resource
    score: float
    matched_fields: List[str] = []


# Conversation Models


class Message(BaseModel):
    role: str  # user, assistant, system
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None


class Conversation(BaseModel):
    id: str
    user_id: str
    title: Optional[str] = None
    messages: List[Message] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = {}


# Health & System Models


class HealthStatus(BaseModel):
    status: str  # healthy, degraded, unhealthy
    service: str
    version: str
    timestamp: float
    components: Dict[str, str] = {}
    latency_ms: Optional[float] = None


class ServiceMetrics(BaseModel):
    service: str
    requests_total: int
    requests_per_minute: float
    avg_response_time_ms: float
    error_rate: float
    active_connections: int
