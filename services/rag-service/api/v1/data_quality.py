"""
Data Quality API endpoints.

This module provides REST API endpoints for data quality assessment
including freshness validation, confidence scoring, and cross-validation.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from schemas import SearchRequest
from services.data_quality import get_data_quality

router = APIRouter(prefix="/quality", tags=["Data Quality"])


# ============================================================================
# Request/Response Schemas
# ============================================================================


class QualityAssessmentRequest(BaseModel):
    """Request for quality assessment."""

    results: List[Dict[str, Any]] = Field(
        ..., description="Search results to assess"
    )
    query: str = Field(..., description="Original query")
    validate_live: bool = Field(
        default=False, description="Whether to validate against live APIs"
    )


class QualityAssessmentResponse(BaseModel):
    """Response for quality assessment."""

    quality_score: float
    quality_level: str
    confidence: Dict[str, Any]
    fresh_results_count: int
    stale_results_count: int
    total_results: int
    recommendation: str
    uncertainty_phrase: str


class FreshnessResponse(BaseModel):
    """Response for freshness check."""

    freshness: str
    color: str
    icon: str
    label: str
    age_hours: Optional[float]


class ValidationResponse(BaseModel):
    """Response for result validation."""

    results: List[Dict[str, Any]]
    quality: Dict[str, Any]


# ============================================================================
# API Endpoints
# ============================================================================


@router.post("/assess", response_model=QualityAssessmentResponse)
async def assess_quality(request: QualityAssessmentRequest) -> QualityAssessmentResponse:
    """Assess quality of search results.

    Args:
        request: Quality assessment request

    Returns:
        Quality assessment results
    """
    quality_service = get_data_quality()

    try:
        assessment = await quality_service.assess_quality(
            results=request.results,
            query=request.query,
        )

        return QualityAssessmentResponse(**assessment)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Quality assessment failed: {str(e)}",
        )


@router.post("/validate", response_model=ValidationResponse)
async def validate_results(request: QualityAssessmentRequest) -> ValidationResponse:
    """Validate and enrich results with quality metadata.

    Args:
        request: Validation request

    Returns:
        Validated results with quality metadata
    """
    quality_service = get_data_quality()

    try:
        result = await quality_service.validate_and_enrich(
            results=request.results,
            query=request.query,
            validate_live=request.validate_live,
        )

        return ValidationResponse(**result)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {str(e)}",
        )


@router.get("/freshness/{timestamp}", response_model=FreshnessResponse)
async def check_freshness(timestamp: str) -> FreshnessResponse:
    """Check freshness of a timestamp.

    Args:
        timestamp: ISO format timestamp

    Returns:
        Freshness indicator
    """
    quality_service = get_data_quality()

    try:
        indicator = quality_service.get_freshness_indicator(timestamp)
        return FreshnessResponse(**indicator)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Freshness check failed: {str(e)}",
        )


@router.post("/batch-freshness", response_model=List[Dict[str, Any]])
async def batch_check_freshness(
    timestamps: List[str],
) -> List[Dict[str, Any]]:
    """Check freshness of multiple timestamps.

    Args:
        timestamps: List of timestamps

    Returns:
        List of freshness indicators
    """
    quality_service = get_data_quality()

    try:
        results = []
        for ts in timestamps:
            indicator = quality_service.get_freshness_indicator(ts)
            results.append({
                "timestamp": ts,
                **indicator,
            })

        return results

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch freshness check failed: {str(e)}",
        )


@router.get("/health")
async def quality_health() -> Dict[str, Any]:
    """Check data quality service health.

    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "service": "data_quality",
        "features": [
            "timestamp_validation",
            "confidence_scoring",
            "cross_validation",
            "freshness_indicators",
        ],
    }
