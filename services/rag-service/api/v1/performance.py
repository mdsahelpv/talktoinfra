"""
Performance API endpoints for RAG Service.

Provides endpoints for cache management, deduplication, and indexing queue operations.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from services.cache import QueryCache, get_query_cache
from services.deduplication import DeduplicationService, get_deduplication_service
from services.indexing_queue import IndexingQueue, get_indexing_queue

router = APIRouter(prefix="/performance", tags=["Performance"])


# ============ Cache Endpoints ============


class CacheStatsResponse(BaseModel):
    """Response model for cache statistics."""

    total_cached_queries: int
    ttl_seconds: int
    redis_url: str
    error: Optional[str] = None


class CacheInvalidateRequest(BaseModel):
    """Request model for cache invalidation."""

    collection: Optional[str] = None
    pattern: Optional[str] = None


class CacheInvalidateResponse(BaseModel):
    """Response model for cache invalidation."""

    invalidated_count: int
    collection: Optional[str] = None
    pattern: Optional[str] = None


@router.get("/cache/stats", response_model=CacheStatsResponse)
async def get_cache_stats():
    """Get cache statistics.

    Returns:
        Cache statistics including number of cached queries and TTL
    """
    cache = get_query_cache()
    stats = await cache.get_stats()
    return CacheStatsResponse(**stats)


@router.post("/cache/invalidate", response_model=CacheInvalidateResponse)
async def invalidate_cache(request: CacheInvalidateRequest):
    """Invalidate cached query results.

    Args:
        request: Invalidation request with collection or pattern

    Returns:
        Number of cached entries invalidated
    """
    cache = get_query_cache()
    count = await cache.invalidate(
        collection=request.collection,
        pattern=request.pattern,
    )

    return CacheInvalidateResponse(
        invalidated_count=count,
        collection=request.collection,
        pattern=request.pattern,
    )


# ============ Deduplication Endpoints ============


class DeduplicateRequest(BaseModel):
    """Request model for document deduplication."""

    documents: List[Dict[str, Any]]
    strategy: str = Field(
        default="keep_first",
        description="Deduplication strategy: keep_first, keep_newest, keep_oldest",
    )


class DeduplicateResponse(BaseModel):
    """Response model for deduplication."""

    original_count: int
    deduplicated_count: int
    removed_count: int
    documents: List[Dict[str, Any]]


class DuplicateReportResponse(BaseModel):
    """Response model for duplicate report."""

    total_documents: int
    exact_duplicate_groups: int
    exact_duplicate_count: int
    near_duplicate_groups: int
    near_duplicate_count: int
    total_duplicates: int
    unique_documents: int
    similarity_threshold: float


@router.post("/deduplicate", response_model=DeduplicateResponse)
async def deduplicate_documents(request: DeduplicateRequest):
    """Remove duplicate documents from a list.

    Args:
        request: Deduplication request with documents

    Returns:
        Deduplicated document list
    """
    service = get_deduplication_service()

    deduplicated = service.deduplicate_documents(
        documents=request.documents,
        strategy=request.strategy,
    )

    return DeduplicateResponse(
        original_count=len(request.documents),
        deduplicated_count=len(deduplicated),
        removed_count=len(request.documents) - len(deduplicated),
        documents=deduplicated,
    )


@router.post("/deduplicate/report", response_model=DuplicateReportResponse)
async def get_duplicate_report(request: DeduplicateRequest):
    """Generate a duplicate report for documents.

    Args:
        request: Request with documents to analyze

    Returns:
        Detailed duplicate report
    """
    service = get_deduplication_service()
    report = service.get_duplicate_report(documents=request.documents)

    # Remove detailed lists from response (they can be large)
    return DuplicateReportResponse(
        total_documents=report["total_documents"],
        exact_duplicate_groups=report["exact_duplicate_groups"],
        exact_duplicate_count=report["exact_duplicate_count"],
        near_duplicate_groups=report["near_duplicate_groups"],
        near_duplicate_count=report["near_duplicate_count"],
        total_duplicates=report["total_duplicates"],
        unique_documents=report["unique_documents"],
        similarity_threshold=report["similarity_threshold"],
    )


# ============ Indexing Queue Endpoints ============


class IndexDocumentRequest(BaseModel):
    """Request model for indexing a single document."""

    document_id: str
    collection: str
    content: str
    vector: List[float]
    payload: Dict[str, Any] = Field(default_factory=dict)


class IndexDocumentResponse(BaseModel):
    """Response model for document indexing."""

    task_id: str
    document_id: str
    collection: str


class IndexBatchRequest(BaseModel):
    """Request model for indexing a batch of documents."""

    documents: List[Dict[str, Any]]
    collection: str


class IndexBatchResponse(BaseModel):
    """Response model for batch indexing."""

    task_id: str
    document_count: int
    collection: str


class IndexFromDiscoveryRequest(BaseModel):
    """Request model for indexing from discovery scan."""

    scan_id: str
    host_ids: List[int]


class IndexFromDiscoveryResponse(BaseModel):
    """Response model for discovery indexing."""

    task_id: str
    scan_id: str
    host_count: int


class IndexFromK8sRequest(BaseModel):
    """Request model for indexing from Kubernetes."""

    cluster_id: str
    resource_type: str
    namespace: Optional[str] = None


class IndexFromK8sResponse(BaseModel):
    """Response model for K8s indexing."""

    task_id: str
    cluster_id: str
    resource_type: str
    namespace: Optional[str] = None


class TaskStatusResponse(BaseModel):
    """Response model for task status."""

    task_id: str
    status: str
    ready: bool
    successful: Optional[bool] = None
    result: Optional[Dict[str, Any]] = None
    info: Optional[str] = None


class QueueStatsResponse(BaseModel):
    """Response model for queue statistics."""

    workers: List[str]
    active_tasks: int
    reserved_tasks: int


@router.post("/index/document", response_model=IndexDocumentResponse)
async def index_document(request: IndexDocumentRequest):
    """Index a single document asynchronously.

    Args:
        request: Document to index

    Returns:
        Task ID for tracking
    """
    queue = get_indexing_queue()
    task_id = queue.enqueue_index_document(
        document_id=request.document_id,
        collection=request.collection,
        content=request.content,
        vector=request.vector,
        payload=request.payload,
    )

    return IndexDocumentResponse(
        task_id=task_id,
        document_id=request.document_id,
        collection=request.collection,
    )


@router.post("/index/batch", response_model=IndexBatchResponse)
async def index_batch(request: IndexBatchRequest):
    """Index a batch of documents asynchronously.

    Args:
        request: Batch of documents to index

    Returns:
        Task ID for tracking
    """
    queue = get_indexing_queue()
    task_id = queue.enqueue_index_documents_batch(
        documents=request.documents,
        collection=request.collection,
    )

    return IndexBatchResponse(
        task_id=task_id,
        document_count=len(request.documents),
        collection=request.collection,
    )


@router.post("/index/discovery", response_model=IndexFromDiscoveryResponse)
async def index_from_discovery(request: IndexFromDiscoveryRequest):
    """Index discovered hosts from a scan.

    Args:
        request: Discovery indexing request

    Returns:
        Task ID for tracking
    """
    queue = get_indexing_queue()
    task_id = queue.enqueue_index_from_discovery(
        scan_id=request.scan_id,
        host_ids=request.host_ids,
    )

    return IndexFromDiscoveryResponse(
        task_id=task_id,
        scan_id=request.scan_id,
        host_count=len(request.host_ids),
    )


@router.post("/index/k8s", response_model=IndexFromK8sResponse)
async def index_from_k8s(request: IndexFromK8sRequest):
    """Index Kubernetes resources.

    Args:
        request: K8s indexing request

    Returns:
        Task ID for tracking
    """
    queue = get_indexing_queue()
    task_id = queue.enqueue_index_from_k8s(
        cluster_id=request.cluster_id,
        resource_type=request.resource_type,
        namespace=request.namespace,
    )

    return IndexFromK8sResponse(
        task_id=task_id,
        cluster_id=request.cluster_id,
        resource_type=request.resource_type,
        namespace=request.namespace,
    )


@router.get("/index/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """Get status of an indexing task.

    Args:
        task_id: Task ID to check

    Returns:
        Task status information
    """
    queue = get_indexing_queue()
    status = queue.get_task_status(task_id)
    return TaskStatusResponse(**status)


@router.delete("/index/task/{task_id}")
async def cancel_task(task_id: str):
    """Cancel a running indexing task.

    Args:
        task_id: Task ID to cancel

    Returns:
        Confirmation of cancellation
    """
    queue = get_indexing_queue()
    queue.cancel_task(task_id)

    return {"message": "Task cancelled", "task_id": task_id}


@router.get("/queue/stats", response_model=QueueStatsResponse)
async def get_queue_stats():
    """Get indexing queue statistics.

    Returns:
        Queue statistics including active workers and tasks
    """
    queue = get_indexing_queue()
    stats = queue.get_queue_stats()
    return QueueStatsResponse(**stats)
