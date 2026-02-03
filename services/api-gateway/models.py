"""
Pydantic models for API requests and responses.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

# User Models


class UserLogin(BaseModel):
    username: str
    password: str


class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    roles: List[str] = ["engineer"]


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    roles: List[str]
    created_at: datetime
    last_login: Optional[datetime]


# Conversation Models


class ConversationCreate(BaseModel):
    title: Optional[str] = None
    metadata: Dict[str, Any] = {}


class ConversationResponse(BaseModel):
    id: str
    title: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]


# Query Models


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=10000)
    conversation_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class QuerySource(BaseModel):
    type: str  # "vector_search", "k8s_api", "cloud_api", etc.
    resource_id: Optional[str] = None
    resource_type: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    metadata: Dict[str, Any] = {}


class QueryResponse(BaseModel):
    response: str
    conversation_id: str
    sources: List[QuerySource] = []
    metadata: Dict[str, Any] = {}
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Action Models


class ActionRequest(BaseModel):
    action: str = Field(..., min_length=1, max_length=1000)
    target: str = Field(..., min_length=1, max_length=500)
    parameters: Dict[str, Any] = {}
    dry_run: bool = True
    justification: Optional[str] = None


class DryRunResult(BaseModel):
    success: bool
    changes: List[Dict[str, Any]] = []
    warnings: List[str] = []
    errors: List[str] = []
    preview: Optional[str] = None


class ActionResponse(BaseModel):
    action_id: str
    status: str  # "pending", "approved", "rejected", "executing", "completed", "failed"
    dry_run_result: Optional[DryRunResult] = None
    requires_approval: bool = False
    approvers: List[str] = []
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


# Approval Models


class ApprovalRequest(BaseModel):
    action_id: str
    approver_notes: Optional[str] = None


class ApprovalResponse(BaseModel):
    approval_id: str
    action_id: str
    status: str  # "pending", "approved", "rejected"
    requested_by: str
    approvers: List[str]
    approved_by: Optional[str] = None
    rejected_by: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    decided_at: Optional[datetime] = None


# Audit Models


class AuditLogEntry(BaseModel):
    id: str
    timestamp: datetime
    user_id: str
    action: str
    resource_type: str
    resource_id: Optional[str]
    details: Dict[str, Any]
    ip_address: Optional[str]
    user_agent: Optional[str]


# Infrastructure Discovery Models


class ScanPort(BaseModel):
    port: int
    status: str = Field(..., pattern="^(open|closed|filtered)$")
    service: Optional[str] = None
    banner: Optional[str] = None


class DiscoveredHost(BaseModel):
    id: str
    ip_address: str
    hostname: Optional[str] = None
    ports: List[ScanPort] = []
    status: str = Field(..., pattern="^(alive|unreachable)$")
    response_time_ms: Optional[int] = None
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    added_to_hosts: bool = False


class ManagedHost(BaseModel):
    id: str
    name: str
    ip_address: str
    ports: List[int]
    services: List[str] = []
    status: str = Field(default="unknown", pattern="^(online|offline|unknown)$")
    last_checked_at: Optional[datetime] = None
    added_at: datetime = Field(default_factory=datetime.utcnow)
    added_by: str


class ScanRequest(BaseModel):
    ip_range: str = Field(
        ...,
        min_length=7,
        max_length=50,
        description="CIDR notation (e.g., 192.168.1.0/24)",
    )
    ports: List[int] = Field(
        ..., min_length=1, max_length=100, description="Ports to scan"
    )
    timeout: float = Field(
        default=2.0, ge=0.5, le=10.0, description="Timeout per host in seconds"
    )
    concurrent_limit: int = Field(
        default=50, ge=10, le=100, description="Max concurrent connections"
    )
    service_detection: bool = Field(
        default=True, description="Enable service banner grabbing"
    )

    @field_validator("ip_range")
    @classmethod
    def validate_cidr(cls, v: str) -> str:
        import ipaddress

        try:
            ipaddress.ip_network(v, strict=False)
            return v
        except ValueError:
            raise ValueError("Invalid CIDR notation. Use format: 192.168.1.0/24")


class ScanJob(BaseModel):
    id: str
    status: str = Field(..., pattern="^(pending|running|completed|failed)$")
    progress: int = Field(default=0, ge=0, le=100)
    total_hosts: int = 0
    scanned_hosts: int = 0
    found_hosts: int = 0
    started_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    created_by: str


class ScanJobResponse(BaseModel):
    job_id: str
    status: str
    message: str


class ScanStatus(BaseModel):
    job_id: str
    status: str
    progress: int
    total_hosts: int
    scanned_hosts: int
    found_hosts: int
    current_ip: Optional[str] = None
    estimated_time_remaining: Optional[int] = None  # seconds


class HostCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    ip_address: str = Field(..., pattern=r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
    ports: List[int] = []
    services: List[str] = []
