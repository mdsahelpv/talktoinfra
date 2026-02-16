"""
Knowledge Graph API endpoints.

This module provides REST API endpoints for knowledge graph operations
including entity extraction, relationship mapping, and graph traversal.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from services.knowledge_graph import get_knowledge_graph

router = APIRouter(prefix="/knowledge-graph", tags=["Knowledge Graph"])


# ============================================================================
# Request/Response Schemas
# ============================================================================


class EntityExtractRequest(BaseModel):
    """Request for extracting entities from resource data."""

    resources: List[Dict[str, Any]] = Field(
        ..., description="List of resource data to extract entities from"
    )


class EntityResponse(BaseModel):
    """Response for a single entity."""

    entity_id: str
    entity_type: str
    name: str
    properties: Dict[str, Any]
    metadata: Dict[str, Any]


class RelationshipResponse(BaseModel):
    """Response for a single relationship."""

    relationship_id: str
    source_id: str
    target_id: str
    relationship_type: str
    properties: Dict[str, Any]


class GraphBuildResponse(BaseModel):
    """Response for graph building operation."""

    entities: List[EntityResponse]
    relationships: List[RelationshipResponse]
    entity_count: int
    relationship_count: int


class GraphTraversalRequest(BaseModel):
    """Request for graph traversal."""

    entity_id: str = Field(..., description="Starting entity ID")
    relationship_types: Optional[List[str]] = Field(
        None, description="Filter by relationship types"
    )
    max_depth: int = Field(default=2, ge=1, le=5,
                           description="Maximum traversal depth")


class GraphTraversalResponse(BaseModel):
    """Response for graph traversal."""

    starting_entity: str
    entities: List[EntityResponse]
    relationships: List[RelationshipResponse]
    paths: List[List[str]]


class PathFindRequest(BaseModel):
    """Request for finding path between entities."""

    source_id: str = Field(..., description="Source entity ID")
    target_id: str = Field(..., description="Target entity ID")
    max_depth: int = Field(default=5, ge=1, le=10,
                           description="Maximum path length")


class PathFindResponse(BaseModel):
    """Response for path finding."""

    source_id: str
    target_id: str
    path: Optional[List[str]]
    path_found: bool


# ============================================================================
# API Endpoints
# ============================================================================


@router.post("/extract", response_model=GraphBuildResponse)
async def extract_entities(request: EntityExtractRequest) -> GraphBuildResponse:
    """Extract entities from resource data.

    Args:
        request: Request with resource data

    Returns:
        Extracted entities and relationships
    """
    kg_service = get_knowledge_graph()

    try:
        entities, relationships = kg_service.build_graph_from_resources(
            request.resources
        )

        return GraphBuildResponse(
            entities=[EntityResponse(**e.to_dict()) for e in entities],
            relationships=[RelationshipResponse(
                **r.to_dict()) for r in relationships],
            entity_count=len(entities),
            relationship_count=len(relationships),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Entity extraction failed: {str(e)}",
        )


@router.post("/traverse", response_model=GraphTraversalResponse)
async def traverse_graph(request: GraphTraversalRequest) -> GraphTraversalResponse:
    """Traverse the knowledge graph from a starting entity.

    Args:
        request: Traversal request

    Returns:
        Traversal results with entities and relationships
    """
    kg_service = get_knowledge_graph()

    try:
        # Get related entities
        related = kg_service.get_related_entities(
            entity_id=request.entity_id,
            relationship_types=request.relationship_types,
            max_depth=request.max_depth,
        )

        # For now, return empty results (would query graph DB in production)
        return GraphTraversalResponse(
            starting_entity=request.entity_id,
            entities=[],
            relationships=[],
            paths=[],
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Graph traversal failed: {str(e)}",
        )


@router.post("/path", response_model=PathFindResponse)
async def find_path(request: PathFindRequest) -> PathFindResponse:
    """Find a path between two entities.

    Args:
        request: Path finding request

    Returns:
        Path between entities if found
    """
    kg_service = get_knowledge_graph()

    try:
        path = kg_service.find_path(
            source_id=request.source_id,
            target_id=request.target_id,
            max_depth=request.max_depth,
        )

        return PathFindResponse(
            source_id=request.source_id,
            target_id=request.target_id,
            path=path,
            path_found=path is not None,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Path finding failed: {str(e)}",
        )


@router.get("/entity-types", response_model=List[str])
async def get_entity_types() -> List[str]:
    """Get list of supported entity types.

    Returns:
        List of entity types
    """
    kg_service = get_knowledge_graph()
    return list(kg_service.ENTITY_TYPES.keys())


@router.get("/relationship-types", response_model=List[str])
async def get_relationship_types() -> List[str]:
    """Get list of supported relationship types.

    Returns:
        List of relationship types
    """
    kg_service = get_knowledge_graph()
    return list(kg_service.RELATIONSHIP_TYPES.keys())


@router.get("/health")
async def kg_health() -> Dict[str, Any]:
    """Check knowledge graph service health.

    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "service": "knowledge_graph",
        "features": [
            "entity_extraction",
            "relationship_inference",
            "graph_traversal",
            "path_finding",
        ],
    }
