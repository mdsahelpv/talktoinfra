"""
RAG search API endpoints.

This module provides REST API endpoints for performing semantic
search using the RAG pipeline with source citations.
"""

import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from schemas import (
    RAGContextResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
)
from services.pipeline import get_pipeline

router = APIRouter(prefix="/search", tags=["RAG Search"])


@router.post("/", response_model=SearchResponse)
async def search_rag(request: SearchRequest) -> SearchResponse:
    """Perform semantic search using RAG pipeline.

    Args:
        request: Search request with query and parameters

    Returns:
        Search results with scores and metadata
    """
    start_time = time.time()

    pipeline = get_pipeline()

    try:
        results = await pipeline.search(
            query=request.query,
            top_k=request.top_k,
            document_types=request.document_types,
            namespaces=request.namespaces,
            cluster_ids=request.cluster_ids,
            min_score=request.min_score,
        )

        # Format results
        search_results = []
        for result in results:
            search_results.append(
                SearchResult(
                    id=result.get("id", ""),
                    document_id=result.get(
                        "payload", {}).get("document_id", ""),
                    score=result.get("score", 0.0),
                    content=result.get("payload", {}).get("content"),
                    title=result.get("payload", {}).get("title"),
                    document_type=result.get(
                        "payload", {}).get("document_type", ""),
                    source_type=result.get("payload", {}).get("source_type"),
                    source_id=result.get("payload", {}).get("source_id"),
                    resource_type=result.get("payload", {}).get(
                        "metadata", {}).get("resource_type"),
                    resource_name=result.get("payload", {}).get(
                        "metadata", {}).get("resource_name"),
                    namespace=result.get("payload", {}).get(
                        "metadata", {}).get("namespace"),
                    cluster_id=result.get("payload", {}).get(
                        "metadata", {}).get("cluster_id"),
                    metadata=result.get("payload", {}).get("metadata", {}),
                )
            )

        elapsed_ms = (time.time() - start_time) * 1000

        return SearchResponse(
            query=request.query,
            results=search_results,
            total_results=len(search_results),
            search_time_ms=elapsed_ms,
            has_more=False,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}",
        )


@router.post("/context", response_model=RAGContextResponse)
async def get_rag_context(request: SearchRequest) -> RAGContextResponse:
    """Get RAG context with citations for AI consumption.

    Args:
        request: Search request with query

    Returns:
        Context text with source citations
    """
    start_time = time.time()

    pipeline = get_pipeline()

    try:
        results = await pipeline.search(
            query=request.query,
            top_k=request.top_k,
            document_types=request.document_types,
            namespaces=request.namespaces,
            cluster_ids=request.cluster_ids,
            min_score=request.min_score,
        )

        # Build context text from results
        context_parts = []
        citations = []

        for i, result in enumerate(results):
            content = result.get("payload", {}).get("content", "")
            title = result.get("payload", {}).get("title", "")
            source_type = result.get("payload", {}).get(
                "source_type", "unknown")
            source_id = result.get("payload", {}).get("source_id", "")

            # Add to context
            context_parts.append(f"[Source {i+1}] {title}\n{content}")

            # Create citation
            citations.append({
                "source_num": i + 1,
                "source_type": source_type,
                "source_id": source_id,
                "title": title,
                "score": result.get("score", 0.0),
            })

        context_text = "\n\n".join(context_parts)

        # Build unique sources list
        sources = []
        seen_ids = set()
        for cit in citations:
            if cit["source_id"] not in seen_ids:
                seen_ids.add(cit["source_id"])
                sources.append({
                    "id": cit["source_id"],
                    "type": cit["source_type"],
                    "title": cit["title"],
                })

        elapsed_ms = (time.time() - start_time) * 1000

        return RAGContextResponse(
            query=request.query,
            context_text=context_text,
            citations=citations,
            sources=sources,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Context generation failed: {str(e)}",
        )


@router.get("/", response_model=SearchResponse)
async def search_simple(
    q: str = Query(..., min_length=1, max_length=5000,
                   description="Search query"),
    top_k: int = Query(default=10, ge=1, le=100),
    document_types: Optional[str] = Query(
        default=None, description="Comma-separated document types"),
    namespaces: Optional[str] = Query(
        default=None, description="Comma-separated namespaces"),
    cluster_ids: Optional[str] = Query(
        default=None, description="Comma-separated cluster IDs"),
    min_score: float = Query(default=0.0, ge=0.0, le=1.0),
) -> SearchResponse:
    """Simple GET endpoint for search.

    Args:
        q: Search query
        top_k: Number of results
        document_types: Comma-separated document types
        namespaces: Comma-separated namespaces
        cluster_ids: Comma-separated cluster IDs
        min_score: Minimum similarity score

    Returns:
        Search results
    """
    # Parse comma-separated lists
    doc_types = document_types.split(",") if document_types else None
    ns_list = namespaces.split(",") if namespaces else None
    cluster_list = cluster_ids.split(",") if cluster_ids else None

    request = SearchRequest(
        query=q,
        top_k=top_k,
        document_types=doc_types,
        namespaces=ns_list,
        cluster_ids=cluster_list,
        min_score=min_score,
    )

    return await search_rag(request)


@router.post("/batch", response_model=List[SearchResponse])
async def search_batch(requests: List[SearchRequest]) -> List[SearchResponse]:
    """Perform multiple searches in batch.

    Args:
        requests: List of search requests

    Returns:
        List of search responses

    Raises:
        HTTPException: If batch is empty
    """
    if not requests:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Batch cannot be empty",
        )

    responses = []
    for request in requests:
        response = await search_rag(request)
        responses.append(response)

    return responses
