"""
Pydantic schemas for Discovered Infrastructure API.

This module defines request/response schemas for the unified discovered
infrastructure management endpoints.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ==================== Enums ====================


class InfrastructureType(str, Enum):
    """Types of discovered infrastructure."""

    KUBERNETES_CLUSTER = "kubernetes_cluster"
    CLOUD_RESOURCE = "cloud_resource"
    DATABASE = "database"
    LOAD_BALANCER = "load_balancer"
    SERVICE = "service"
    NETWORK_DEVICE = "network_device"
    HOST = "host"
    UNKNOWN = "unknown"


class DiscoveredState(str, Enum):
    """State machine states for discovered infrastructure."""

    DISCOVERED = "discovered"
    ANALYZED = "analyzed"
    SUGGESTED = "suggested"
    PENDING_ONBOARDING = "pending_onboarding"
    ONBOARDING = "onboarding"
    ONBOARDED = "onboarded"
    FAILED = "failed"
    IGNORED = "ignored"


# ==================== Port Schemas ====================


class PortInfoSchema(BaseModel):
    """Information about an open port."""

    port: int = Field(..., ge=1, le=65535)
    status: str = Field(..., pattern="^(open|closed|filtered)$")
    service: Optional[str] = None
    service_version: Optional[str] = None
    banner: Optional[str] = None
    protocol: str = Field(default="tcp")
    response_time_ms: Optional[int] = None


# ==================== SSL/TLS Schemas ====================


class SSLInfoSchema(BaseModel):
    """SSL/TLS certificate information."""

    version: Optional[str] = None
    subject: Optional[str] = None
    issuer: Optional[str] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    days_remaining: Optional[int] = None
    serial_number: Optional[str] = None
    signature_algorithm: Optional[str] = None
    is_valid: bool = True


# ==================== Cloud Metadata Schemas ====================


class CloudMetadataSchema(BaseModel):
    """Cloud provider metadata."""

    provider: Optional[str] = None
    account_id: Optional[str] = None
    region: Optional[str] = None
    availability_zone: Optional[str] = None
    instance_id: Optional[str] = None
    instance_type: Optional[str] = None
    vpc_id: Optional[str] = None
    subnet_id: Optional[str] = None
    ami_id: Optional[str] = None
    tags: Dict[str, str] = {}


# ==================== Kubernetes Info Schemas ====================


class KubernetesInfoSchema(BaseModel):
    """Kubernetes cluster/node information."""

    is_master: bool = False
    node_name: Optional[str] = None
    node_role: Optional[str] = None
    cluster_name: Optional[str] = None
    kubelet_version: Optional[str] = None
    container_runtime: Optional[str] = None
    cpu_capacity: Optional[int] = None
    memory_capacity_bytes: Optional[int] = None
    pod_capacity: Optional[int] = None
    labels: Dict[str, str] = {}
    taints: List[str] = []


# ==================== Base Schemas ====================


class DiscoveredInfrastructureBase(BaseModel):
    """Base schema for discovered infrastructure."""

    ip_address: Optional[str] = None
    hostname: Optional[str] = None
    fqdn: Optional[str] = None
    mac_address: Optional[str] = None
    infra_type: InfrastructureType = InfrastructureType.UNKNOWN
    service_type: Optional[str] = None
    service_version: Optional[str] = None
    confidence_score: int = Field(default=0, ge=0, le=100)
    port: Optional[int] = None
    protocol: str = Field(default="tcp")
    open_ports: List[PortInfoSchema] = []
    service_banner: Optional[str] = None
    ssl_info: Optional[SSLInfoSchema] = None
    headers: Optional[Dict[str, str]] = None
    cloud_provider: Optional[str] = None
    cloud_metadata: Optional[CloudMetadataSchema] = None
    k8s_info: Optional[KubernetesInfoSchema] = None
    location: Optional[str] = None
    vpc_id: Optional[str] = None
    subnet_id: Optional[str] = None
    response_time_ms: Optional[int] = None
    availability_score: int = Field(default=100, ge=0, le=100)
    suggested_action: Optional[str] = None
    tags: List[str] = []


# ==================== Response Schemas ====================


class DiscoveredInfrastructureResponse(DiscoveredInfrastructureBase):
    """Response schema for discovered infrastructure item."""

    id: UUID
    state: DiscoveredState
    previous_state: Optional[DiscoveredState] = None
    scan_job_id: Optional[UUID] = None
    discovered_at: datetime
    last_seen_at: datetime
    onboarding_id: Optional[UUID] = None
    managed_host_id: Optional[UUID] = None
    ignored_at: Optional[datetime] = None
    ignored_by: Optional[str] = None
    ignore_reason: Optional[str] = None
    created_by: str
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class StateHistoryEntry(BaseModel):
    """State change history entry."""

    id: UUID
    from_state: Optional[str] = None
    to_state: str
    triggered_by: str
    trigger_reason: Optional[str] = None
    created_at: datetime
    metadata: Dict[str, Any] = {}


class DiscoveredInfrastructureDetail(DiscoveredInfrastructureResponse):
    """Detailed response with all information."""

    state_history: List[StateHistoryEntry] = []
    raw_scan_data: Optional[Dict[str, Any]] = None


class PaginatedDiscoveredResponse(BaseModel):
    """Paginated list of discovered infrastructure."""

    items: List[DiscoveredInfrastructureResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ==================== Statistics Schemas ====================


class DiscoveredStatsSchema(BaseModel):
    """Statistics for discovered infrastructure."""

    total_items: int
    by_type: Dict[str, int]
    by_state: Dict[str, int]
    by_state_detailed: Dict[str, Dict[str, int]]
    recently_discovered: int
    pending_onboarding: int
    onboarded: int
    ignored: int


# ==================== Suggestion Schemas ====================


class OnboardingSuggestionSchema(BaseModel):
    """Smart onboarding suggestion for an item."""

    item_id: UUID
    suggested_action: str
    action_label: str
    confidence: int
    reason: str
    prerequisites: List[str] = []
    estimated_effort: str


class SuggestionsResponse(BaseModel):
    """Response with smart suggestions."""

    suggestions: List[OnboardingSuggestionSchema]
    total_count: int


# ==================== Request Schemas ====================


class DiscoveredFilterRequest(BaseModel):
    """Filter criteria for listing discovered infrastructure."""

    infra_types: List[InfrastructureType] = []
    states: List[DiscoveredState] = []
    scan_job_ids: List[UUID] = []
    search_query: Optional[str] = None
    has_open_ports: Optional[List[int]] = None
    min_confidence: Optional[int] = None
    cloud_providers: List[str] = []
    tags: List[str] = []
    discovered_after: Optional[datetime] = None
    discovered_before: Optional[datetime] = None


class BulkOnboardRequest(BaseModel):
    """Request to onboard multiple items."""

    item_ids: List[UUID]
    action_type: str = Field(..., pattern="^(onboard|add_monitoring|ignore)$")
    options: Dict[str, Any] = {}


class IgnoreRequest(BaseModel):
    """Request to ignore an item."""

    reason: Optional[str] = None


class BulkIgnoreRequest(BaseModel):
    """Request to ignore multiple items."""

    item_ids: List[UUID]
    reason: Optional[str] = None


class UpdateStateRequest(BaseModel):
    """Request to update item state."""

    new_state: DiscoveredState
    reason: Optional[str] = None


class UpdateNotesRequest(BaseModel):
    """Request to update notes on an item."""

    notes: Optional[str] = None
    tags: Optional[List[str]] = None


class ReScanRequest(BaseModel):
    """Request to re-scan a specific item."""

    ports: Optional[List[int]] = None
    service_detection: bool = True


# ==================== Bulk Operation Schemas ====================


class BulkOperationResponse(BaseModel):
    """Response for bulk operation."""

    operation_id: UUID
    status: str
    target_count: int
    created_at: datetime


class BulkOperationStatus(BaseModel):
    """Status of a bulk operation."""

    operation_id: UUID
    operation_type: str
    status: str
    target_count: int
    success_count: int
    failed_count: int
    progress_percent: float
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None


class ExportRequest(BaseModel):
    """Request to export discovered items."""

    item_ids: Optional[List[UUID]] = None
    filters: Optional[DiscoveredFilterRequest] = None
    format: str = Field(default="csv", pattern="^(csv|json)$")
    include_fields: List[str] = []


# ==================== Service Catalog Schemas ====================


class ServiceCatalogEntryResponse(BaseModel):
    """Response for a service catalog entry."""

    id: UUID
    host_id: UUID
    endpoint: str
    path: Optional[str] = None
    method: str
    service_name: Optional[str] = None
    service_type: Optional[str] = None
    api_version: Optional[str] = None
    discovered_at: datetime
    last_checked_at: Optional[datetime] = None
    response_time_ms: Optional[int] = None
    documentation_url: Optional[str] = None
    description: Optional[str] = None
    capabilities: List[str] = []
    auth_required: bool = False
    auth_type: Optional[str] = None


class ServiceCatalogResponse(BaseModel):
    """Response for service catalog listing."""

    services: List[ServiceCatalogEntryResponse]
    total: int
    by_type: Dict[str, int]
