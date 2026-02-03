"""
Pydantic models for Ingestion Service.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class IngestionJobStatus(str, Enum):
    """Ingestion job status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class IngestRequest(BaseModel):
    """Request to ingest Kubernetes resources."""

    namespaces: List[str] = Field(
        default=["default"],
        description="Kubernetes namespaces to ingest",
    )
    resource_types: List[str] = Field(
        default=["pod", "deployment", "service", "configmap"],
        description="Resource types to ingest",
    )
    labels_filter: Optional[Dict[str, str]] = Field(
        None,
        description="Filter by labels",
    )
    force_refresh: bool = Field(
        default=False,
        description="Force refresh even if recently ingested",
    )


class IngestResponse(BaseModel):
    """Response for ingestion request."""

    job_id: str = Field(..., description="Ingestion job ID")
    status: IngestionJobStatus = Field(..., description="Job status")
    message: str = Field(..., description="Status message")
    documents_processed: Optional[int] = Field(
        None,
        description="Number of documents processed",
    )
    estimated_completion: Optional[str] = Field(
        None,
        description="Estimated time to completion",
    )


class IngestionJob(BaseModel):
    """Ingestion job details."""

    job_id: str = Field(..., description="Job unique identifier")
    source_type: str = Field(..., description="Source type (kubernetes, etc.)")
    status: IngestionJobStatus = Field(..., description="Current status")
    namespaces: List[str] = Field(default=[], description="Target namespaces")
    resource_types: List[str] = Field(default=[], description="Resource types")
    documents_processed: int = Field(default=0, description="Documents processed")
    error_message: Optional[str] = Field(None, description="Error if failed")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = Field(None, description="Start time")
    completed_at: Optional[datetime] = Field(None, description="Completion time")


class ResourceDocument(BaseModel):
    """Resource document for vector storage."""

    id: str = Field(..., description="Document unique identifier")
    resource_type: str = Field(..., description="Type of resource")
    name: str = Field(..., description="Resource name")
    namespace: Optional[str] = Field(None, description="Kubernetes namespace")
    description: str = Field(default="", description="Human-readable description")
    content: str = Field(..., description="Full resource content (JSON)")
    metadata: Dict[str, Any] = Field(default={}, description="Additional metadata")
    embedding: Optional[List[float]] = Field(None, description="Vector embedding")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SearchRequest(BaseModel):
    """Semantic search request."""

    query: str = Field(..., min_length=1, max_length=1000, description="Search query")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of results")
    namespace: Optional[str] = Field(None, description="Filter by namespace")
    resource_type: Optional[str] = Field(None, description="Filter by resource type")
    min_score: float = Field(
        default=0.7, ge=0.0, le=1.0, description="Minimum similarity score"
    )


class SearchResult(BaseModel):
    """Individual search result."""

    id: str = Field(..., description="Document ID")
    score: float = Field(..., ge=0.0, le=1.0, description="Similarity score")
    resource_type: str = Field(..., description="Resource type")
    name: str = Field(..., description="Resource name")
    namespace: Optional[str] = Field(None, description="Namespace")
    description: str = Field(default="", description="Description")
    metadata: Dict[str, Any] = Field(default={}, description="Additional metadata")


class SearchResponse(BaseModel):
    """Semantic search response."""

    query: str = Field(..., description="Search query")
    results: List[SearchResult] = Field(default=[], description="Search results")
    total_results: int = Field(..., description="Total number of results")
    search_time_ms: Optional[float] = Field(
        None, description="Search time in milliseconds"
    )


class EmbeddingResponse(BaseModel):
    """Embedding generation response."""

    text: str = Field(..., description="Original text")
    embedding: List[float] = Field(..., description="Generated embedding vector")
    model: str = Field(..., description="Model used")
    dimensions: int = Field(..., description="Embedding dimensions")


class VectorStoreStatus(BaseModel):
    """Vector store status."""

    collection_name: str = Field(..., description="Collection name")
    vector_count: int = Field(..., description="Number of vectors stored")
    dimensions: int = Field(..., description="Vector dimensions")
    indexed: bool = Field(..., description="Whether collection is indexed")
    last_updated: Optional[datetime] = Field(None, description="Last update time")
