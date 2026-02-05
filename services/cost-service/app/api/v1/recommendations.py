"""Recommendations API Endpoints.

API endpoints for cost optimization recommendations.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Recommendation, CostRecord
from app.schemas import (
    CloudProvider,
    RecommendationCreate,
    RecommendationPriority,
    RecommendationResponse,
    RecommendationType,
    RecommendationUpdate,
    ResourceType,
)
from app.services.optimizer import CostOptimizationService
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.get("", response_model=List[RecommendationResponse])
async def list_recommendations(
    cloud_provider: Optional[CloudProvider] = Query(
        None, description="Filter by cloud provider"),
    recommendation_type: Optional[RecommendationType] = Query(
        None, description="Filter by type"),
    priority: Optional[RecommendationPriority] = Query(
        None, description="Filter by priority"),
    status: Optional[str] = Query(
        None, description="Filter by status (pending, approved, dismissed, implemented)"),
    cluster_id: Optional[str] = Query(None, description="Filter by cluster"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    db: AsyncSession = Depends(get_db),
) -> List[RecommendationResponse]:
    """List cost optimization recommendations with filters.

    Args:
        cloud_provider: Optional cloud provider filter
        recommendation_type: Optional recommendation type filter
        priority: Optional priority filter
        status: Optional status filter
        cluster_id: Optional cluster ID filter
        limit: Maximum number of results
        db: Database session

    Returns:
        List of recommendations
    """
    conditions = []
    if cloud_provider:
        conditions.append(Recommendation.cloud_provider == cloud_provider)
    if recommendation_type:
        conditions.append(
            Recommendation.recommendation_type == recommendation_type)
    if priority:
        conditions.append(Recommendation.priority == priority)
    if status:
        conditions.append(Recommendation.status == status)
    if cluster_id:
        conditions.append(Recommendation.cluster_id == cluster_id)

    query = (
        select(Recommendation)
        .where(and_(*conditions))
        .order_by(
            Recommendation.priority.desc(),
            Recommendation.estimated_savings.desc(),
            Recommendation.created_at.desc(),
        )
        .limit(limit)
    )

    result = await db.execute(query)
    recommendations = result.scalars().all()

    return [RecommendationResponse.model_validate(r) for r in recommendations]


@router.get("/summary")
async def get_recommendations_summary(
    cloud_provider: Optional[CloudProvider] = Query(
        None, description="Filter by cloud provider"),
    cluster_id: Optional[str] = Query(None, description="Filter by cluster"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get summary of recommendations and potential savings.

    Args:
        cloud_provider: Optional cloud provider filter
        cluster_id: Optional cluster ID filter
        db: Database session

    Returns:
        Summary statistics for recommendations
    """
    conditions = [Recommendation.status == "pending"]
    if cloud_provider:
        conditions.append(Recommendation.cloud_provider == cloud_provider)
    if cluster_id:
        conditions.append(Recommendation.cluster_id == cluster_id)

    query = select(Recommendation).where(and_(*conditions))
    result = await db.execute(query)
    recommendations = result.scalars().all()

    # Calculate totals by priority
    by_priority: Dict[str, Dict[str, Any]] = {
        "critical": {"count": 0, "savings": Decimal("0")},
        "high": {"count": 0, "savings": Decimal("0")},
        "medium": {"count": 0, "savings": Decimal("0")},
        "low": {"count": 0, "savings": Decimal("0")},
    }

    # Calculate totals by type
    by_type: Dict[str, Dict[str, Any]] = {}

    for rec in recommendations:
        priority = rec.priority.value if rec.priority else "medium"
        if priority in by_priority:
            by_priority[priority]["count"] += 1
            by_priority[priority]["savings"] += rec.estimated_savings or Decimal(
                "0")

        rec_type = rec.recommendation_type.value if rec.recommendation_type else "other"
        if rec_type not in by_type:
            by_type[rec_type] = {"count": 0, "savings": Decimal("0")}
        by_type[rec_type]["count"] += 1
        by_type[rec_type]["savings"] += rec.estimated_savings or Decimal("0")

    # Count by status
    status_query = (
        select(Recommendation.status, func.count(Recommendation.id))
        .group_by(Recommendation.status)
    )
    status_result = await db.execute(status_query)
    by_status = {row[0]: row[1] for row in status_result.all()}

    # Total potential savings
    total_savings = sum(
        r.estimated_savings or Decimal("0")
        for r in recommendations
    )

    return {
        "total_recommendations": len(recommendations),
        "total_potential_savings_monthly": total_savings,
        "total_potential_savings_yearly": total_savings * 12,
        "by_priority": by_priority,
        "by_type": by_type,
        "by_status": by_status,
        "critical_count": by_priority.get("critical", {}).get("count", 0),
        "high_count": by_priority.get("high", {}).get("count", 0),
    }


@router.get("/{recommendation_id}", response_model=RecommendationResponse)
async def get_recommendation(
    recommendation_id: str,
    db: AsyncSession = Depends(get_db),
) -> RecommendationResponse:
    """Get a specific recommendation.

    Args:
        recommendation_id: Recommendation ID
        db: Database session

    Returns:
        Recommendation details
    """
    from uuid import UUID

    query = select(Recommendation).where(
        Recommendation.id == UUID(recommendation_id))
    result = await db.execute(query)
    recommendation = result.scalar_one_or_none()

    if not recommendation:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    return RecommendationResponse.model_validate(recommendation)


@router.post("")
async def create_recommendation(
    recommendation_data: RecommendationCreate,
    db: AsyncSession = Depends(get_db),
) -> RecommendationResponse:
    """Create a new recommendation.

    Args:
        recommendation_data: Recommendation data
        db: Database session

    Returns:
        Created recommendation
    """
    recommendation = Recommendation(
        **recommendation_data.model_dump(),
        status="pending",
    )
    db.add(recommendation)
    await db.commit()
    await db.refresh(recommendation)

    logger.info(
        "recommendation_created",
        recommendation_id=str(recommendation.id),
        type=recommendation.recommendation_type.value,
        priority=recommendation.priority.value,
    )

    return RecommendationResponse.model_validate(recommendation)


@router.patch("/{recommendation_id}")
async def update_recommendation(
    recommendation_id: str,
    update_data: RecommendationUpdate,
    db: AsyncSession = Depends(get_db),
) -> RecommendationResponse:
    """Update a recommendation status.

    Args:
        recommendation_id: Recommendation ID
        update_data: Update data
        db: Database session

    Returns:
        Updated recommendation
    """
    from uuid import UUID

    query = select(Recommendation).where(
        Recommendation.id == UUID(recommendation_id))
    result = await db.execute(query)
    recommendation = result.scalar_one_or_none()

    if not recommendation:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    # Update status
    recommendation.status = update_data.status

    if update_data.status in ["approved", "implemented"]:
        recommendation.reviewed_at = datetime.utcnow()

    if update_data.status == "implemented":
        recommendation.implemented_at = datetime.utcnow()

    await db.commit()
    await db.refresh(recommendation)

    logger.info(
        "recommendation_updated",
        recommendation_id=str(recommendation_id),
        status=update_data.status,
    )

    return RecommendationResponse.model_validate(recommendation)


@router.delete("/{recommendation_id}")
async def delete_recommendation(
    recommendation_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Delete a recommendation.

    Args:
        recommendation_id: Recommendation ID
        db: Database session

    Returns:
        Success message
    """
    from uuid import UUID

    query = select(Recommendation).where(
        Recommendation.id == UUID(recommendation_id))
    result = await db.execute(query)
    recommendation = result.scalar_one_or_none()

    if not recommendation:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    await db.delete(recommendation)
    await db.commit()

    logger.info("recommendation_deleted",
                recommendation_id=str(recommendation_id))

    return {"message": "Recommendation deleted successfully"}


@router.post("/generate")
async def generate_recommendations(
    cloud_provider: Optional[CloudProvider] = Query(
        None, description="Generate for specific provider"),
    cluster_id: Optional[str] = Query(
        None, description="Generate for specific cluster"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Generate optimization recommendations based on current costs and utilization.

    Args:
        cloud_provider: Optional cloud provider filter
        cluster_id: Optional cluster ID filter
        db: Database session

    Returns:
        Generated recommendations
    """
    optimizer = CostOptimizationService()

    recommendations = await optimizer.generate_recommendations(
        cloud_provider=cloud_provider,
        cluster_id=cluster_id,
        db=db,
    )

    # Save recommendations to database
    saved_count = 0
    for rec in recommendations:
        db_rec = Recommendation(
            **rec.model_dump(),
            status="pending",
        )
        db.add(db_rec)
        saved_count += 1

    await db.commit()

    logger.info(
        "recommendations_generated",
        count=saved_count,
        cloud_provider=cloud_provider,
        cluster_id=cluster_id,
    )

    return {
        "recommendations_generated": saved_count,
        "recommendations": [r.model_dump() for r in recommendations],
    }


@router.get("/idle-resources")
async def get_idle_resources(
    cloud_provider: Optional[CloudProvider] = Query(
        None, description="Filter by cloud provider"),
    cluster_id: Optional[str] = Query(None, description="Filter by cluster"),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Get resources that appear to be idle or underutilized.

    Args:
        cloud_provider: Optional cloud provider filter
        cluster_id: Optional cluster ID filter
        db: Database session

    Returns:
        List of potentially idle resources
    """
    # Query for resources with recent cost but low variety
    # This is a simplified check - in production would use utilization metrics

    conditions = [
        CostRecord.cost_amount > Decimal("0"),
    ]
    if cloud_provider:
        conditions.append(CostRecord.cloud_provider == cloud_provider)
    if cluster_id:
        conditions.append(CostRecord.cluster_id == cluster_id)

    query = (
        select(
            CostRecord.resource_id,
            CostRecord.resource_name,
            CostRecord.resource_type,
            CostRecord.service_name,
            CostRecord.cloud_provider,
            CostRecord.region,
            CostRecord.cluster_id,
            func.sum(CostRecord.cost_amount).label("total_cost"),
            func.count(CostRecord.id).label("usage_records"),
        )
        .where(and_(*conditions))
        .group_by(
            CostRecord.resource_id,
            CostRecord.resource_name,
            CostRecord.resource_type,
            CostRecord.service_name,
            CostRecord.cloud_provider,
            CostRecord.region,
            CostRecord.cluster_id,
        )
        .having(func.count(CostRecord.id) < 10)  # Low usage = few records
        .order_by(func.sum(CostRecord.cost_amount).desc())
        .limit(50)
    )

    result = await db.execute(query)
    rows = result.all()

    return [
        {
            "resource_id": row.resource_id,
            "resource_name": row.resource_name,
            "resource_type": row.resource_type,
            "service_name": row.service_name,
            "cloud_provider": row.cloud_provider.value if row.cloud_provider else None,
            "region": row.region,
            "cluster_id": row.cluster_id,
            "total_cost": row.total_cost or Decimal("0"),
            "usage_records": row.usage_records,
            # Annual projection
            "potential_savings": (row.total_cost or Decimal("0")) * 12,
            "recommendation_type": "delete_idle",
        }
        for row in rows
    ]


@router.get("/right-sizing")
async def get_right_sizing_opportunities(
    cloud_provider: Optional[CloudProvider] = Query(
        None, description="Filter by cloud provider"),
    cluster_id: Optional[str] = Query(None, description="Filter by cluster"),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Get resources that could be right-sized.

    Args:
        cloud_provider: Optional cloud provider filter
        cluster_id: Optional cluster ID filter
        db: Database session

    Returns:
        List of right-sizing opportunities
    """
    # This would typically use utilization metrics
    # For now, return a placeholder structure

    conditions = [
        CostRecord.resource_type.in_([
            "ec2", "rds", "elasticsearch", "redis", "kubernetes_pod"
        ]),
    ]
    if cloud_provider:
        conditions.append(CostRecord.cloud_provider == cloud_provider)
    if cluster_id:
        conditions.append(CostRecord.cluster_id == cluster_id)

    # Get top spenders which are candidates for right-sizing
    query = (
        select(
            CostRecord.resource_id,
            CostRecord.resource_name,
            CostRecord.resource_type,
            CostRecord.service_name,
            CostRecord.cloud_provider,
            CostRecord.region,
            func.sum(CostRecord.cost_amount).label("monthly_cost"),
        )
        .where(and_(*conditions))
        .group_by(
            CostRecord.resource_id,
            CostRecord.resource_name,
            CostRecord.resource_type,
            CostRecord.service_name,
            CostRecord.cloud_provider,
            CostRecord.region,
        )
        .order_by(func.sum(CostRecord.cost_amount).desc())
        .limit(50)
    )

    result = await db.execute(query)
    rows = result.all()

    return [
        {
            "resource_id": row.resource_id,
            "resource_name": row.resource_name,
            "resource_type": row.resource_type,
            "service_name": row.service_name,
            "cloud_provider": row.cloud_provider.value if row.cloud_provider else None,
            "region": row.region,
            "current_monthly_cost": row.monthly_cost or Decimal("0"),
            "recommended_action": "downsize",
            "estimated_savings_percent": 30.0,  # Placeholder
            "recommendation_type": "right_size",
        }
        for row in rows
    ]
