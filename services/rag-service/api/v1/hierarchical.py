"""
Hierarchical RAG API endpoints.

This module provides REST API endpoints for hierarchical RAG search
with automatic query classification and multi-level retrieval.
"""

import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from schemas import SearchRequest, SearchResult
from services.hierarchical_rag import get_hierarchical_rag

router = APIRouter(prefix="/hierarchical", tags=["Hierarchical RAG"])


@router.post("/search", response_model=Dict[str, Any])
async def hierarchical_search(request: SearchRequest) -> Dict[str, Any]:
    """Perform hierarchical RAG search with automatic query classification.

    The system automatically determines the best retrieval strategy:
    - Level 1: Semantic vector search (default)
    - Level 2: Structured query fallback (for "list all" queries)
    - Level 3: Hybrid search (semantic + knowledge graph)

    Args:
        request: Search request with query and parameters

    Returns:
        Search results with level information and context
    """
    start_time = time.time()

    hierarchical_rag = get_hierarchical_rag()

    try:
        result = await hierarchical_rag.search(
            query=request.query,
            top_k=request.top_k,
            document_types=request.document_types,
            namespaces=request.namespaces,
            cluster_ids=request.cluster_ids,
            min_score=request.min_score,
        )

        elapsed_ms = (time.time() - start_time) * 1000

        return {
            "query": request.query,
            "level": result.get("level", 1),
            "query_type": result.get("query_type", "semantic"),
            "strategy": result.get("strategy", "unknown"),
            "results": result.get("results", []),
            "total_results": result.get("total_results", 0),
            "context_text": result.get("context_text", ""),
            "search_time_ms": elapsed_ms,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Hierarchical search failed: {str(e)}",
        )


@router.post("/context", response_model=Dict[str, Any])
async def get_hierarchical_context(request: SearchRequest) -> Dict[str, Any]:
    """Get formatted context for LLM consumption with hierarchical RAG.

    Args:
        request: Search request with query

    Returns:
        Context response with citations and quality metrics
    """
    start_time = time.time()

    hierarchical_rag = get_hierarchical_rag()

    try:
        result = await hierarchical_rag.get_context_for_llm(
            query=request.query,
            top_k=request.top_k,
        )

        elapsed_ms = (time.time() - start_time) * 1000

        return {
            **result,
            "generation_time_ms": elapsed_ms,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Context generation failed: {str(e)}",
        )


@router.get("/search", response_model=Dict[str, Any])
async def hierarchical_search_simple(
    q: str = Query(..., min_length=1, max_length=5000,
                   description="Search query"),
    top_k: int = Query(default=10, ge=1, le=100),
    document_types: Optional[str] = Query(
        default=None, description="Comma-separated document types"
    ),
    namespaces: Optional[str] = Query(
        default=None, description="Comma-separated namespaces"
    ),
    cluster_ids: Optional[str] = Query(
        default=None, description="Comma-separated cluster IDs"
    ),
    min_score: float = Query(default=0.0, ge=0.0, le=1.0),
    level: Optional[int] = Query(
        default=None, ge=1, le=3, description="Force specific RAG level (1, 2, or 3)"
    ),
) -> Dict[str, Any]:
    """Simple GET endpoint for hierarchical search.

    Args:
        q: Search query
        top_k: Number of results
        document_types: Comma-separated document types
        namespaces: Comma-separated namespaces
        cluster_ids: Comma-separated cluster IDs
        min_score: Minimum similarity score
        level: Force specific RAG level

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

    hierarchical_rag = get_hierarchical_rag()

    try:
        result = await hierarchical_rag.search(
            query=request.query,
            top_k=request.top_k,
            document_types=request.document_types,
            namespaces=request.namespaces,
            cluster_ids=request.cluster_ids,
            min_score=request.min_score,
            force_level=level,
        )

        return {
            "query": request.query,
            "level": result.get("level", 1),
            "query_type": result.get("query_type", "semantic"),
            "strategy": result.get("strategy", "unknown"),
            "results": result.get("results", []),
            "total_results": result.get("total_results", 0),
            "context_text": result.get("context_text", ""),
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}",
        )
