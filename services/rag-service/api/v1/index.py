"""
Index management API endpoints.

This module provides REST API endpoints for managing RAG indices,
including indexing operations and collection management.
"""

from services.indexer import get_indexer
from schemas import (
    CollectionInfo,
    HealthResponse,
    IndexCreateRequest,
    IndexStatusResponse,
)
from database import get_db
from config import get_settings
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

import sys
sys.path.insert(0, "/home/ubuntu/talktoinfra/services/rag-service")


router = APIRouter(prefix="/index", tags=["Index Management"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check health of RAG service dependencies.

    Returns:
        Health status of Qdrant, PostgreSQL, Redis
    """
    indexer = get_indexer()

    # Check Qdrant
    qdrant_connected = False
    qdrant_collections = []
    try:
        qdrant_collections = await indexer.get_all_collections()
        qdrant_connected = True
    except Exception as e:
        print(f"Qdrant health check failed: {e}")

    # Check PostgreSQL
    postgres_connected = False
    try:
        db = await get_db()
        await db.execute("SELECT 1")
        postgres_connected = True
    except Exception as e:
        print(f"PostgreSQL health check failed: {e}")

    # Check Redis (simplified)
    redis_connected = False
    try:
        from redis.asyncio import Redis
        settings = get_settings()
        redis = Redis.from_url(settings.redis_url)
        await redis.ping()
        redis_connected = True
        await redis.close()
    except Exception as e:
        print(f"Redis health check failed: {e}")

    # Elasticsearch (optional)
    elasticsearch_connected = None
    try:
        if settings.elasticsearch_url:
            from elasticsearch import AsyncElasticsearch
            es = AsyncElasticsearch(hosts=[settings.elasticsearch_url])
            await es.ping()
            elasticsearch_connected = True
            await es.close()
    except Exception as e:
        print(f"Elasticsearch health check failed: {e}")
        elasticsearch_connected = False

    overall_status = "healthy"
    if not qdrant_connected:
        overall_status = "degraded"
    if not postgres_connected:
        overall_status = "unhealthy"

    return HealthResponse(
        status=overall_status,
        qdrant_connected=qdrant_connected,
        qdrant_collections=qdrant_collections,
        postgres_connected=postgres_connected,
        redis_connected=redis_connected,
        elasticsearch_connected=elasticsearch_connected,
    )


@router.get("/collections", response_model=List[CollectionInfo])
async def list_collections() -> List[CollectionInfo]:
    """List all Qdrant collections.

    Returns:
        List of collection information
    """
    indexer = get_indexer()
    collections = await indexer.get_all_collections()

    collection_infos = []
    for name in collections:
        try:
            info = await indexer.get_collection_info(name)
            collection_infos.append(CollectionInfo(**info))
        except Exception:
            collection_infos.append(
                CollectionInfo(
                    name=name,
                    vector_size=0,
                    distance="COSINE",
                    points_count=0,
                    status="unknown",
                )
            )

    return collection_infos


@router.get("/collections/{collection_name}", response_model=CollectionInfo)
async def get_collection(collection_name: str) -> CollectionInfo:
    """Get information about a specific collection.

    Args:
        collection_name: Name of collection

    Returns:
        Collection information

    Raises:
        HTTPException: If collection not found
    """
    indexer = get_indexer()

    if not await indexer.collection_exists(collection_name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection '{collection_name}' not found",
        )

    info = await indexer.get_collection_info(collection_name)
    return CollectionInfo(**info)


@router.post("/collections/{collection_name}/create")
async def create_collection(collection_name: str) -> Dict[str, Any]:
    """Create a new collection.

    Args:
        collection_name: Name of collection to create

    Returns:
        Creation status
    """
    indexer = get_indexer()

    if await indexer.collection_exists(collection_name):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Collection '{collection_name}' already exists",
        )

    await indexer.create_collection(collection_name)

    return {
        "status": "created",
        "collection": collection_name,
    }


@router.delete("/collections/{collection_name}")
async def delete_collection(collection_name: str) -> Dict[str, Any]:
    """Delete a collection.

    Args:
        collection_name: Name of collection to delete

    Returns:
        Deletion status
    """
    indexer = get_indexer()

    if not await indexer.collection_exists(collection_name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection '{collection_name}' not found",
        )

    await indexer.delete_collection(collection_name)

    return {
        "status": "deleted",
        "collection": collection_name,
    }


@router.post("/index", status_code=status.HTTP_202_ACCEPTED)
async def create_index(request: IndexCreateRequest) -> Dict[str, Any]:
    """Trigger a new indexing job.

    Args:
        request: Indexing request parameters

    Returns:
        Job ID for tracking
    """
    # This is a simplified implementation
    # In production, this would queue a Celery task

    job_id = f"index_{int(time.time())}_{request.source_type}"

    return {
        "job_id": job_id,
        "status": "queued",
        "message": f"Indexing job queued for source_type: {request.source_type}",
        "request": request.model_dump(),
    }


@router.get("/jobs/{job_id}", response_model=IndexStatusResponse)
async def get_index_status(job_id: str) -> IndexStatusResponse:
    """Get status of an indexing job.

    Args:
        job_id: Job ID to check

    Returns:
        Job status

    Raises:
        HTTPException: If job not found
    """
    # Simplified implementation - would query database in production
    if not job_id.startswith("index_"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found",
        )

    return IndexStatusResponse(
        job_id=job_id,
        status="completed",
        progress=100,
        documents_processed=0,
        documents_indexed=0,
        documents_failed=0,
        started_at=None,
        completed_at=None,
        error_message=None,
    )


@router.post("/collections/{collection_name}/ensure")
async def ensure_collection(collection_name: str) -> Dict[str, Any]:
    """Ensure collection exists, create if missing.

    Args:
        collection_name: Name of collection

    Returns:
        Collection status
    """
    indexer = get_indexer()
    existed = await indexer.collection_exists(collection_name)

    if not existed:
        await indexer.create_collection(collection_name)
        return {
            "status": "created",
            "collection": collection_name,
        }

    return {
        "status": "exists",
        "collection": collection_name,
    }
