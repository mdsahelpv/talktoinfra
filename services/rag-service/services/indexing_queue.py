"""
Indexing Queue Service for RAG Pipeline.

This module provides Celery-based background task processing for
asynchronous document indexing operations.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from celery import Celery
from celery.result import AsyncResult

from config import get_settings

logger = structlog.get_logger()


# Initialize Celery app
settings = get_settings()

celery_app = Celery(
    "rag_indexing",
    broker=settings.redis_url.replace("redis://", "redis://"),
    backend=settings.redis_url.replace("redis://", "redis://"),
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    task_soft_time_limit=3000,  # 50 minutes soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
)


class IndexingQueue:
    """Celery-based queue for document indexing tasks."""

    def __init__(self, celery_app: Optional[Celery] = None):
        """Initialize the indexing queue.

        Args:
            celery_app: Optional Celery app instance
        """
        self.celery_app = celery_app or celery_app
        self._indexing_tasks: Dict[str, AsyncResult] = {}

    def enqueue_index_document(
        self,
        document_id: str,
        collection: str,
        content: str,
        vector: List[float],
        payload: Dict[str, Any],
    ) -> str:
        """Enqueue a single document for indexing.

        Args:
            document_id: Unique document ID
            collection: Target collection name
            content: Document content
            vector: Embedding vector
            payload: Document metadata

        Returns:
            Task ID
        """
        task = index_document_task.delay(
            document_id=document_id,
            collection=collection,
            content=content,
            vector=vector,
            payload=payload,
        )

        logger.info(
            "document_indexing_enqueued",
            task_id=task.id,
            document_id=document_id,
            collection=collection,
        )

        return task.id

    def enqueue_index_documents_batch(
        self,
        documents: List[Dict[str, Any]],
        collection: str,
    ) -> str:
        """Enqueue a batch of documents for indexing.

        Args:
            documents: List of documents to index
            collection: Target collection name

        Returns:
            Task ID
        """
        task = index_documents_batch_task.delay(
            documents=documents,
            collection=collection,
        )

        logger.info(
            "batch_indexing_enqueued",
            task_id=task.id,
            document_count=len(documents),
            collection=collection,
        )

        return task.id

    def enqueue_index_from_discovery(
        self,
        scan_id: str,
        host_ids: List[int],
    ) -> str:
        """Enqueue indexing of discovered hosts.

        Args:
            scan_id: Discovery scan ID
            host_ids: List of host IDs to index

        Returns:
            Task ID
        """
        task = index_from_discovery_task.delay(
            scan_id=scan_id,
            host_ids=host_ids,
        )

        logger.info(
            "discovery_indexing_enqueued",
            task_id=task.id,
            scan_id=scan_id,
            host_count=len(host_ids),
        )

        return task.id

    def enqueue_index_from_k8s(
        self,
        cluster_id: str,
        resource_type: str,
        namespace: Optional[str] = None,
    ) -> str:
        """Enqueue indexing of Kubernetes resources.

        Args:
            cluster_id: Kubernetes cluster ID
            resource_type: Type of resource (pod, deployment, service, etc.)
            namespace: Optional namespace filter

        Returns:
            Task ID
        """
        task = index_from_k8s_task.delay(
            cluster_id=cluster_id,
            resource_type=resource_type,
            namespace=namespace,
        )

        logger.info(
            "k8s_indexing_enqueued",
            task_id=task.id,
            cluster_id=cluster_id,
            resource_type=resource_type,
            namespace=namespace,
        )

        return task.id

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of an indexing task.

        Args:
            task_id: Task ID

        Returns:
            Task status information
        """
        result = AsyncResult(task_id, app=self.celery_app)

        return {
            "task_id": task_id,
            "status": result.state,
            "ready": result.ready(),
            "successful": result.successful() if result.ready() else None,
            "result": result.result if result.ready() else None,
            "info": str(result.info) if result.info else None,
        }

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running indexing task.

        Args:
            task_id: Task ID to cancel

        Returns:
            True if cancelled successfully
        """
        result = AsyncResult(task_id, app=self.celery_app)
        result.revoke(terminate=True)

        logger.info(
            "task_cancelled",
            task_id=task_id,
        )

        return True

    def get_queue_stats(self) -> Dict[str, Any]:
        """Get indexing queue statistics.

        Returns:
            Queue statistics
        """
        inspect = self.celery_app.control.inspect()

        stats = inspect.stats() or {}
        active = inspect.active() or {}
        reserved = inspect.reserved() or {}

        return {
            "workers": list(stats.keys()),
            "active_tasks": sum(len(tasks) for tasks in active.values()),
            "reserved_tasks": sum(len(tasks) for tasks in reserved.values()),
        }


# Celery tasks (defined at module level for worker import)


@celery_app.task(bind=True, max_retries=3)
def index_document_task(
    self,
    document_id: str,
    collection: str,
    content: str,
    vector: List[float],
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """Index a single document.

    Args:
        document_id: Unique document ID
        collection: Target collection name
        content: Document content
        vector: Embedding vector
        payload: Document metadata

    Returns:
        Indexing result
    """
    from services.indexer import get_indexer

    async def _index():
        indexer = get_indexer()
        await indexer.index_document(
            collection_name=collection,
            document_id=document_id,
            vector=vector,
            payload=payload,
        )

    try:
        asyncio.run(_index())

        logger.info(
            "document_indexed",
            task_id=self.request.id,
            document_id=document_id,
            collection=collection,
        )

        return {
            "status": "success",
            "document_id": document_id,
            "collection": collection,
        }

    except Exception as e:
        logger.error(
            "document_indexing_failed",
            task_id=self.request.id,
            document_id=document_id,
            error=str(e),
        )
        raise self.retry(exc=e, countdown=60)


@celery_app.task(bind=True, max_retries=3)
def index_documents_batch_task(
    self,
    documents: List[Dict[str, Any]],
    collection: str,
) -> Dict[str, Any]:
    """Index a batch of documents.

    Args:
        documents: List of documents to index
        collection: Target collection name

    Returns:
        Indexing result
    """
    from services.indexer import get_indexer

    async def _index_batch():
        indexer = get_indexer()
        await indexer.index_documents_batch(
            collection_name=collection,
            documents=documents,
        )

    try:
        count = asyncio.run(_index_batch())

        logger.info(
            "batch_indexed",
            task_id=self.request.id,
            count=count,
            collection=collection,
        )

        return {
            "status": "success",
            "indexed_count": count,
            "collection": collection,
        }

    except Exception as e:
        logger.error(
            "batch_indexing_failed",
            task_id=self.request.id,
            error=str(e),
        )
        raise self.retry(exc=e, countdown=120)


@celery_app.task(bind=True, max_retries=2)
def index_from_discovery_task(
    self,
    scan_id: str,
    host_ids: List[int],
) -> Dict[str, Any]:
    """Index discovered hosts from a scan.

    Args:
        scan_id: Discovery scan ID
        host_ids: List of host IDs to index

    Returns:
        Indexing result
    """
    from services.pipeline import get_rag_pipeline

    async def _index():
        pipeline = get_rag_pipeline()
        indexed_count = 0

        for host_id in host_ids:
            # Transform and index each host
            # This would fetch from database in real implementation
            host_data = {"id": host_id, "ip_address": f"192.168.1.{host_id}"}
            ports_data = []

            doc = await pipeline.transform_discovery_host(host_data, ports_data)
            if doc:
                indexed_count += 1

        return indexed_count

    try:
        count = asyncio.run(_index())

        logger.info(
            "discovery_indexed",
            task_id=self.request.id,
            scan_id=scan_id,
            indexed_count=count,
        )

        return {
            "status": "success",
            "scan_id": scan_id,
            "indexed_count": count,
        }

    except Exception as e:
        logger.error(
            "discovery_indexing_failed",
            task_id=self.request.id,
            scan_id=scan_id,
            error=str(e),
        )
        raise self.retry(exc=e, countdown=180)


@celery_app.task(bind=True, max_retries=2)
def index_from_k8s_task(
    self,
    cluster_id: str,
    resource_type: str,
    namespace: Optional[str] = None,
) -> Dict[str, Any]:
    """Index Kubernetes resources.

    Args:
        cluster_id: Kubernetes cluster ID
        resource_type: Type of resource
        namespace: Optional namespace filter

    Returns:
        Indexing result
    """
    from services.pipeline import get_rag_pipeline

    async def _index():
        pipeline = get_rag_pipeline()
        # This would fetch from K8s API in real implementation
        indexed_count = 0
        return indexed_count

    try:
        count = asyncio.run(_index())

        logger.info(
            "k8s_indexed",
            task_id=self.request.id,
            cluster_id=cluster_id,
            resource_type=resource_type,
            indexed_count=count,
        )

        return {
            "status": "success",
            "cluster_id": cluster_id,
            "resource_type": resource_type,
            "indexed_count": count,
        }

    except Exception as e:
        logger.error(
            "k8s_indexing_failed",
            task_id=self.request.id,
            cluster_id=cluster_id,
            error=str(e),
        )
        raise self.retry(exc=e, countdown=180)


# Singleton instance
_indexing_queue: Optional[IndexingQueue] = None


def get_indexing_queue() -> IndexingQueue:
    """Get the singleton indexing queue instance."""
    global _indexing_queue
    if _indexing_queue is None:
        _indexing_queue = IndexingQueue(celery_app=celery_app)
    return _indexing_queue
