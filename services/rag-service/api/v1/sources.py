"""
Source citations API endpoints.

This module provides REST API endpoints for managing source
citations returned by RAG queries.
"""

import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status

from schemas import CitationCreate, CitationResponse
from services.pipeline import get_pipeline

router = APIRouter(prefix="/sources", tags=["Source Citations"])


# In-memory storage for citations (would use database in production)
_citations: Dict[str, Dict[str, Any]] = {}


@router.post("/cite", response_model=CitationResponse)
async def create_citation(citation: CitationCreate) -> CitationResponse:
    """Create a new source citation.

    Args:
        citation: Citation data

    Returns:
        Created citation
    """
    if citation.citation_key in _citations:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Citation '{citation.citation_key}' already exists",
        )

    citation_id = str(hashlib.md5(
        citation.citation_key.encode()).hexdigest()[:12])

    citation_data = {
        "id": citation_id,
        "citation_key": citation.citation_key,
        "query_hash": citation.query_hash,
        "source_type": citation.source_type,
        "source_id": citation.source_id,
        "source_name": citation.source_name,
        "source_location": citation.source_location,
        "content_snippet": citation.content_snippet,
        "relevance_score": citation.relevance_score,
        "line_number": citation.line_number,
        "created_at": datetime.utcnow(),
        "expires_at": citation.expires_at,
    }

    _citations[citation.citation_key] = citation_data

    return CitationResponse(
        id=citation_id,
        citation_key=citation.citation_key,
        query_hash=citation.query_hash,
        source_type=citation.source_type,
        source_id=citation.source_id,
        source_name=citation.source_name,
        content_snippet=citation.content_snippet,
        relevance_score=citation.relevance_score,
        created_at=citation_data["created_at"],
    )


@router.get("/cite/{citation_key}", response_model=CitationResponse)
async def get_citation(citation_key: str) -> CitationResponse:
    """Get a citation by key.

    Args:
        citation_key: Citation key

    Returns:
        Citation data

    Raises:
        HTTPException: If citation not found
    """
    if citation_key not in _citations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Citation '{citation_key}' not found",
        )

    data = _citations[citation_key]

    return CitationResponse(
        id=data["id"],
        citation_key=data["citation_key"],
        query_hash=data["query_hash"],
        source_type=data["source_type"],
        source_id=data["source_id"],
        source_name=data["source_name"],
        content_snippet=data["content_snippet"],
        relevance_score=data["relevance_score"],
        created_at=data["created_at"],
    )


@router.get("/query/{query_hash}", response_list=List[CitationResponse])
async def get_citations_by_query(query_hash: str) -> List[CitationResponse]:
    """Get all citations for a query.

    Args:
        query_hash: Hash of the query

    Returns:
        List of citations
    """
    results = []
    for data in _citations.values():
        if data.get("query_hash") == query_hash:
            results.append(
                CitationResponse(
                    id=data["id"],
                    citation_key=data["citation_key"],
                    query_hash=data["query_hash"],
                    source_type=data["source_type"],
                    source_id=data["source_id"],
                    source_name=data["source_name"],
                    content_snippet=data["content_snippet"],
                    relevance_score=data["relevance_score"],
                    created_at=data["created_at"],
                )
            )

    return results


@router.get("/source/{source_type}/{source_id}", response_list=List[CitationResponse])
async def get_citations_by_source(
    source_type: str,
    source_id: str,
) -> List[CitationResponse]:
    """Get all citations for a source.

    Args:
        source_type: Type of source
        source_id: Source ID

    Returns:
        List of citations
    """
    results = []
    for data in _citations.values():
        if data.get("source_type") == source_type and data.get("source_id") == source_id:
            results.append(
                CitationResponse(
                    id=data["id"],
                    citation_key=data["citation_key"],
                    query_hash=data["query_hash"],
                    source_type=data["source_type"],
                    source_id=data["source_id"],
                    source_name=data["source_name"],
                    content_snippet=data["content_snippet"],
                    relevance_score=data["relevance_score"],
                    created_at=data["created_at"],
                )
            )

    return results


@router.delete("/cite/{citation_key}")
async def delete_citation(citation_key: str) -> Dict[str, Any]:
    """Delete a citation.

    Args:
        citation_key: Citation key

    Returns:
        Deletion status
    """
    if citation_key not in _citations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Citation '{citation_key}' not found",
        )

    del _citations[citation_key]

    return {
        "status": "deleted",
        "citation_key": citation_key,
    }


@router.get("/stats")
async def get_citation_stats() -> Dict[str, Any]:
    """Get citation statistics.

    Returns:
        Citation statistics
    """
    total = len(_citations)
    by_source_type = {}

    for data in _citations.values():
        source_type = data.get("source_type", "unknown")
        by_source_type[source_type] = by_source_type.get(source_type, 0) + 1

    return {
        "total_citations": total,
        "by_source_type": by_source_type,
    }
