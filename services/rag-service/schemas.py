"""
Pydantic schemas for RAG Service.

This module defines request/response schemas for API endpoints
following the project's naming conventions and validation rules.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Document Schemas
# ============================================================================


class DocumentCreate(BaseModel):
    """Schema for creating a new RAG document."""

    document_id: str = Field(..., description="Unique document identifier")
    document_type: str = Field(
        default="infrastructure",
        description="Document type: infrastructure, log, doc, k8s_resource",
    )
    source_id: Optional[str] = Field(None, description="Source system ID")
    source_type: Optional[str] = Field(
        None, description="Source: discovery, k8s, manual")
    title: Optional[str] = Field(None, max_length=500)
    content: str = Field(..., description="Document text content")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    resource_type: Optional[str] = None
    resource_name: Optional[str] = None
    namespace: Optional[str] = None
    cluster_id: Optional[str] = None


class DocumentResponse(BaseModel):
    """Schema for document response."""

    id: str
    document_id: str
    document_type: str
    source_id: Optional[str]
    source_type: Optional[str]
    title: Optional[str]
    is_indexed: bool
    indexed_at: Optional[datetime]
    last_seen_at: Optional[datetime]
    metadata: Dict[str, Any]

    class Config:
        from_attributes = True


class DocumentUpdate(BaseModel):
    """Schema for updating a document."""

    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    resource_type: Optional[str] = None
    resource_name: Optional[str] = None
    namespace: Optional[str] = None


# ============================================================================
# RAG Search Schemas
# ============================================================================


class SearchRequest(BaseModel):
    """Schema for RAG search request."""

    query: str = Field(..., min_length=1, max_length=5000,
                       description="Search query")
    top_k: int = Field(default=10, ge=1, le=100,
                       description="Number of results")
    filter_conditions: Optional[Dict[str, Any]] = Field(
        None, description="Qdrant filters")
    document_types: Optional[List[str]] = Field(
        None, description="Filter by document types")
    namespaces: Optional[List[str]] = Field(
        None, description="Filter by namespaces")
    cluster_ids: Optional[List[str]] = Field(
        None, description="Filter by cluster IDs")
    min_score: float = Field(default=0.0, ge=0.0, le=1.0,
                             description="Minimum similarity score")


class SearchResult(BaseModel):
    """Schema for a single search result."""

    id: str
    document_id: str
    score: float
    content: Optional[str] = None
    title: Optional[str] = None
    document_type: str
    source_type: Optional[str]
    source_id: Optional[str]
    resource_type: Optional[str]
    resource_name: Optional[str]
    namespace: Optional[str]
    cluster_id: Optional[str]
    metadata: Dict[str, Any]

    class Config:
        from_attributes = True


class SearchResponse(BaseModel):
    """Schema for RAG search response."""

    query: str
    results: List[SearchResult]
    total_results: int
    search_time_ms: float
    has_more: bool


class RAGContextResponse(BaseModel):
    """Schema for RAG context with citations."""

    query: str
    context_text: str
    citations: List[Dict[str, Any]]
    sources: List[Dict[str, Any]]


# ============================================================================
# Index Management Schemas
# ============================================================================


class IndexCreateRequest(BaseModel):
    """Schema for creating an index operation."""

    source_type: str = Field(...,
                             description="Source type: discovery, k8s, manual")
    source_id: Optional[str] = Field(
        None, description="Specific source ID to index")
    document_types: Optional[List[str]] = Field(
        None, description="Document types to index")
    namespaces: Optional[List[str]] = Field(
        None, description="Filter by namespaces")
    cluster_ids: Optional[List[str]] = Field(
        None, description="Filter by clusters")
    force_reindex: bool = Field(default=False, description="Force reindexing")


class IndexStatusResponse(BaseModel):
    """Schema for indexing status."""

    job_id: str
    status: str
    progress: int
    documents_processed: int
    documents_indexed: int
    documents_failed: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]


class CollectionInfo(BaseModel):
    """Schema for collection information."""

    name: str
    vector_size: int
    distance: str
    points_count: int
    status: str


class HealthResponse(BaseModel):
    """Schema for health check response."""

    status: str
    qdrant_connected: bool
    qdrant_collections: List[str]
    postgres_connected: bool
    redis_connected: bool
    elasticsearch_connected: Optional[bool]


# ============================================================================
# K8s Resource Schemas
# ============================================================================


class K8sPodCreate(BaseModel):
    """Schema for creating K8s pod record."""

    cluster_id: str
    name: str
    namespace: str
    uid: Optional[str] = None
    status: str
    phase: Optional[str] = None
    node_name: Optional[str] = None
    images: List[str] = Field(default_factory=list)
    containers: List[Dict[str, Any]] = Field(default_factory=list)
    labels: Dict[str, str] = Field(default_factory=dict)
    annotations: Dict[str, str] = Field(default_factory=dict)


class K8sPodResponse(BaseModel):
    """Schema for K8s pod response."""

    id: str
    cluster_id: str
    name: str
    namespace: str
    status: str
    phase: Optional[str]
    node_name: Optional[str]
    images: List[str]
    labels: Dict[str, str]
    last_seen_at: Optional[datetime]
    updated_at: datetime

    class Config:
        from_attributes = True


class K8sDeploymentCreate(BaseModel):
    """Schema for creating K8s deployment record."""

    cluster_id: str
    name: str
    namespace: str
    uid: Optional[str] = None
    replicas: int = 1
    ready_replicas: int = 0
    strategy_type: Optional[str] = None
    selector_match_labels: Dict[str, str] = Field(default_factory=dict)


class K8sDeploymentResponse(BaseModel):
    """Schema for K8s deployment response."""

    id: str
    cluster_id: str
    name: str
    namespace: str
    replicas: int
    ready_replicas: int
    strategy_type: Optional[str]
    last_seen_at: Optional[datetime]
    updated_at: datetime

    class Config:
        from_attributes = True


class K8sServiceCreate(BaseModel):
    """Schema for creating K8s service record."""

    cluster_id: str
    name: str
    namespace: str
    uid: Optional[str] = None
    type: str
    cluster_ip: Optional[str] = None
    ports: List[Dict[str, Any]] = Field(default_factory=list)
    selector: Dict[str, str] = Field(default_factory=dict)


class K8sServiceResponse(BaseModel):
    """Schema for K8s service response."""

    id: str
    cluster_id: str
    name: str
    namespace: str
    type: str
    cluster_ip: Optional[str]
    ports: List[Dict[str, Any]]
    last_seen_at: Optional[datetime]
    updated_at: datetime

    class Config:
        from_attributes = True


class K8sNodeCreate(BaseModel):
    """Schema for creating K8s node record."""

    cluster_id: str
    name: str
    uid: Optional[str] = None
    status: str
    conditions: List[Dict[str, Any]] = Field(default_factory=list)
    capacity: Dict[str, Any] = Field(default_factory=dict)
    allocatable: Dict[str, Any] = Field(default_factory=dict)
    labels: Dict[str, str] = Field(default_factory=dict)
    taints: List[Dict[str, Any]] = Field(default_factory=list)


class K8sNodeResponse(BaseModel):
    """Schema for K8s node response."""

    id: str
    cluster_id: str
    name: str
    status: str
    capacity: Dict[str, Any]
    allocatable: Dict[str, Any]
    labels: Dict[str, str]
    last_seen_at: Optional[datetime]
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Citation Schemas
# ============================================================================


class CitationCreate(BaseModel):
    """Schema for creating a citation."""

    citation_key: str
    query_hash: str
    source_type: str
    source_id: str
    source_name: Optional[str]
    source_location: Optional[str]
    content_snippet: Optional[str]
    relevance_score: Optional[int]
    line_number: Optional[int]
    expires_at: Optional[datetime] = None


class CitationResponse(BaseModel):
    """Schema for citation response."""

    id: str
    citation_key: str
    query_hash: str
    source_type: str
    source_id: str
    source_name: Optional[str]
    content_snippet: Optional[str]
    relevance_score: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Indexing Job Schemas
# ============================================================================


class IndexingJobResponse(BaseModel):
    """Schema for indexing job response."""

    id: str
    job_type: str
    source_type: Optional[str]
    source_id: Optional[str]
    status: str
    progress: int
    documents_processed: int
    documents_indexed: int
    documents_failed: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]

    class Config:
        from_attributes = True
