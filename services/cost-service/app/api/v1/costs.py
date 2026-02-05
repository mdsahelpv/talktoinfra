"""Cost API Endpoints.

API endpoints for cost queries, trends, and aggregations.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import CostRecord, DailyCostAggregation
from app.schemas import (
    CloudProvider,
    CostQueryParams,
    CostRecordCreate,
    CostRecordResponse,
    CostSummary,
    CostByDimension,
    CostTrendPoint,
)
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/costs", tags=["Costs"])


@router.get("/summary")
async def get_cost_summary(
    start_date: datetime = Query(..., description="Start date for query"),
    end_date: datetime = Query(..., description="End date for query"),
    cloud_provider: Optional[CloudProvider] = Query(
        None, description="Filter by cloud provider"),
    cluster_id: Optional[str] = Query(
        None, description="Filter by cluster ID"),
    db: AsyncSession = Depends(get_db),
) -> CostSummary:
    """Get cost summary for a time period.

    Args:
        start_date: Start of the query period
        end_date: End of the query period
        cloud_provider: Optional cloud provider filter
        cluster_id: Optional cluster ID filter
        db: Database session

    Returns:
        CostSummary with total costs and period comparison
    """
    # Build query conditions
    conditions = [
        CostRecord.usage_start >= start_date,
        CostRecord.usage_start <= end_date,
    ]
    if cloud_provider:
        conditions.append(CostRecord.cloud_provider == cloud_provider)
    if cluster_id:
        conditions.append(CostRecord.cluster_id == cluster_id)

    # Calculate total cost for current period
    query = select(
        func.sum(CostRecord.cost_amount).label("total_cost"),
        func.count(CostRecord.id).label("resource_count"),
    ).where(and_(*conditions))

    result = await db.execute(query)
    row = result.one_or_none()

    total_cost = row.total_cost if row and row.total_cost else Decimal("0")
    resource_count = row.resource_count if row and row.resource_count else 0

    # Calculate previous period cost
    period_length = end_date - start_date
    prev_start = start_date - period_length
    prev_end = start_date

    prev_query = select(
        func.sum(CostRecord.cost_amount).label("prev_cost"),
    ).where(and_(
        CostRecord.usage_start >= prev_start,
        CostRecord.usage_start <= prev_end,
        *([CostRecord.cloud_provider == cloud_provider] if cloud_provider else []),
        *([CostRecord.cluster_id == cluster_id] if cluster_id else []),
    ))

    prev_result = await db.execute(prev_query)
    prev_row = prev_result.one_or_none()
    prev_cost = prev_row.prev_cost if prev_row and prev_row.prev_cost else Decimal(
        "0")

    # Calculate change percentage
    cost_change_percent = None
    if prev_cost > 0:
        cost_change_percent = float((total_cost - prev_cost) / prev_cost * 100)

    return CostSummary(
        total_cost=total_cost,
        currency="USD",
        period_start=start_date,
        period_end=end_date,
        resource_count=resource_count,
        previous_period_cost=prev_cost,
        cost_change_percent=cost_change_percent,
    )


@router.get("/by-provider")
async def get_costs_by_provider(
    start_date: datetime = Query(..., description="Start date for query"),
    end_date: datetime = Query(..., description="End date for query"),
    cluster_id: Optional[str] = Query(
        None, description="Filter by cluster ID"),
    db: AsyncSession = Depends(get_db),
) -> List[CostByDimension]:
    """Get cost breakdown by cloud provider.

    Args:
        start_date: Start of the query period
        end_date: End of the query period
        cluster_id: Optional cluster ID filter
        db: Database session

    Returns:
        List of cost breakdowns by provider
    """
    conditions = [
        CostRecord.usage_start >= start_date,
        CostRecord.usage_start <= end_date,
    ]
    if cluster_id:
        conditions.append(CostRecord.cluster_id == cluster_id)

    query = select(
        CostRecord.cloud_provider.label("dimension_value"),
        func.sum(CostRecord.cost_amount).label("total_cost"),
        func.count(CostRecord.id).label("resource_count"),
    ).where(and_(*conditions)).group_by(CostRecord.cloud_provider)

    result = await db.execute(query)
    rows = result.all()

    total_cost = sum(row.total_cost for row in rows if row.total_cost)

    return [
        CostByDimension(
            dimension="cloud_provider",
            dimension_value=row.dimension_value.value if row.dimension_value else "unknown",
            total_cost=row.total_cost or Decimal("0"),
            percentage=float((row.total_cost or Decimal("0")) /
                             total_cost * 100) if total_cost > 0 else 0,
            resource_count=row.resource_count or 0,
        )
        for row in rows
    ]


@router.get("/by-cluster")
async def get_costs_by_cluster(
    start_date: datetime = Query(..., description="Start date for query"),
    end_date: datetime = Query(..., description="End date for query"),
    cloud_provider: Optional[CloudProvider] = Query(
        None, description="Filter by cloud provider"),
    db: AsyncSession = Depends(get_db),
) -> List[CostByDimension]:
    """Get cost breakdown by cluster.

    Args:
        start_date: Start of the query period
        end_date: End of the query period
        cloud_provider: Optional cloud provider filter
        db: Database session

    Returns:
        List of cost breakdowns by cluster
    """
    conditions = [
        CostRecord.usage_start >= start_date,
        CostRecord.usage_start <= end_date,
        CostRecord.cluster_id.isnot(None),
    ]
    if cloud_provider:
        conditions.append(CostRecord.cloud_provider == cloud_provider)

    query = select(
        CostRecord.cluster_id.label("dimension_value"),
        func.sum(CostRecord.cost_amount).label("total_cost"),
        func.count(CostRecord.id).label("resource_count"),
    ).where(and_(*conditions)).group_by(CostRecord.cluster_id)

    result = await db.execute(query)
    rows = result.all()

    total_cost = sum(row.total_cost for row in rows if row.total_cost)

    return [
        CostByDimension(
            dimension="cluster",
            dimension_value=row.dimension_value or "unknown",
            total_cost=row.total_cost or Decimal("0"),
            percentage=float((row.total_cost or Decimal("0")) /
                             total_cost * 100) if total_cost > 0 else 0,
            resource_count=row.resource_count or 0,
        )
        for row in rows
    ]


@router.get("/by-service")
async def get_costs_by_service(
    start_date: datetime = Query(..., description="Start date for query"),
    end_date: datetime = Query(..., description="End date for query"),
    cloud_provider: Optional[CloudProvider] = Query(
        None, description="Filter by cloud provider"),
    cluster_id: Optional[str] = Query(
        None, description="Filter by cluster ID"),
    limit: int = Query(20, ge=1, le=100, description="Number of results"),
    db: AsyncSession = Depends(get_db),
) -> List[CostByDimension]:
    """Get cost breakdown by cloud service.

    Args:
        start_date: Start of the query period
        end_date: End of the query period
        cloud_provider: Optional cloud provider filter
        cluster_id: Optional cluster ID filter
        limit: Maximum number of results to return
        db: Database session

    Returns:
        List of cost breakdowns by service
    """
    conditions = [
        CostRecord.usage_start >= start_date,
        CostRecord.usage_start <= end_date,
    ]
    if cloud_provider:
        conditions.append(CostRecord.cloud_provider == cloud_provider)
    if cluster_id:
        conditions.append(CostRecord.cluster_id == cluster_id)

    query = select(
        CostRecord.service_name.label("dimension_value"),
        func.sum(CostRecord.cost_amount).label("total_cost"),
        func.count(CostRecord.id).label("resource_count"),
    ).where(and_(*conditions)).group_by(
        CostRecord.service_name
    ).order_by(
        func.sum(CostRecord.cost_amount).desc()
    ).limit(limit)

    result = await db.execute(query)
    rows = result.all()

    total_cost = sum(row.total_cost for row in rows if row.total_cost)

    return [
        CostByDimension(
            dimension="service",
            dimension_value=row.dimension_value or "unknown",
            total_cost=row.total_cost or Decimal("0"),
            percentage=float((row.total_cost or Decimal("0")) /
                             total_cost * 100) if total_cost > 0 else 0,
            resource_count=row.resource_count or 0,
        )
        for row in rows
    ]


@router.get("/by-region")
async def get_costs_by_region(
    start_date: datetime = Query(..., description="Start date for query"),
    end_date: datetime = Query(..., description="End date for query"),
    cloud_provider: Optional[CloudProvider] = Query(
        None, description="Filter by cloud provider"),
    db: AsyncSession = Depends(get_db),
) -> List[CostByDimension]:
    """Get cost breakdown by region.

    Args:
        start_date: Start of the query period
        end_date: End of the query period
        cloud_provider: Optional cloud provider filter
        db: Database session

    Returns:
        List of cost breakdowns by region
    """
    conditions = [
        CostRecord.usage_start >= start_date,
        CostRecord.usage_start <= end_date,
    ]
    if cloud_provider:
        conditions.append(CostRecord.cloud_provider == cloud_provider)

    query = select(
        CostRecord.region.label("dimension_value"),
        func.sum(CostRecord.cost_amount).label("total_cost"),
        func.count(CostRecord.id).label("resource_count"),
    ).where(and_(*conditions)).group_by(CostRecord.region)

    result = await db.execute(query)
    rows = result.all()

    total_cost = sum(row.total_cost for row in rows if row.total_cost)

    return [
        CostByDimension(
            dimension="region",
            dimension_value=row.dimension_value or "unknown",
            total_cost=row.total_cost or Decimal("0"),
            percentage=float((row.total_cost or Decimal("0")) /
                             total_cost * 100) if total_cost > 0 else 0,
            resource_count=row.resource_count or 0,
        )
        for row in rows
    ]


@router.get("/trends")
async def get_cost_trends(
    start_date: datetime = Query(..., description="Start date for query"),
    end_date: datetime = Query(..., description="End date for query"),
    cloud_provider: Optional[CloudProvider] = Query(
        None, description="Filter by cloud provider"),
    cluster_id: Optional[str] = Query(
        None, description="Filter by cluster ID"),
    granularity: str = Query(
        "daily", pattern="^(hourly|daily|weekly|monthly)$"),
    db: AsyncSession = Depends(get_db),
) -> List[CostTrendPoint]:
    """Get cost trend data over time.

    Args:
        start_date: Start of the query period
        end_date: End of the query period
        cloud_provider: Optional cloud provider filter
        cluster_id: Optional cluster ID filter
        granularity: Time series granularity
        db: Database session

    Returns:
        List of cost trend data points
    """
    conditions = [
        CostRecord.usage_start >= start_date,
        CostRecord.usage_start <= end_date,
    ]
    if cloud_provider:
        conditions.append(CostRecord.cloud_provider == cloud_provider)
    if cluster_id:
        conditions.append(CostRecord.cluster_id == cluster_id)

    # For daily aggregation, use the daily_cost_aggregations table for efficiency
    if granularity == "daily":
        agg_query = select(
            DailyCostAggregation.date.label("timestamp"),
            func.sum(DailyCostAggregation.total_cost).label("cost"),
        ).where(and_(
            DailyCostAggregation.date >= start_date,
            DailyCostAggregation.date <= end_date,
            *([DailyCostAggregation.cloud_provider ==
              cloud_provider] if cloud_provider else []),
            *([DailyCostAggregation.cluster_id == cluster_id] if cluster_id else []),
        )).group_by(DailyCostAggregation.date).order_by(DailyCostAggregation.date)

        result = await db.execute(agg_query)
        rows = result.all()

        if rows:
            return [
                CostTrendPoint(
                    timestamp=row.timestamp,
                    cost=row.cost or Decimal("0"),
                )
                for row in rows
            ]

    # Fall back to detailed query for hourly or when no aggregation exists
    query = select(
        func.date_trunc(granularity, CostRecord.usage_start).label(
            "timestamp"),
        func.sum(CostRecord.cost_amount).label("cost"),
    ).where(and_(*conditions)).group_by(
        func.date_trunc(granularity, CostRecord.usage_start)
    ).order_by(func.date_trunc(granularity, CostRecord.usage_start))

    result = await db.execute(query)
    rows = result.all()

    return [
        CostTrendPoint(
            timestamp=row.timestamp,
            cost=row.cost or Decimal("0"),
        )
        for row in rows
    ]


@router.get("/top-resources")
async def get_top_resources(
    start_date: datetime = Query(..., description="Start date for query"),
    end_date: datetime = Query(..., description="End date for query"),
    cloud_provider: Optional[CloudProvider] = Query(
        None, description="Filter by cloud provider"),
    cluster_id: Optional[str] = Query(
        None, description="Filter by cluster ID"),
    limit: int = Query(20, ge=1, le=100, description="Number of results"),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Get top expensive resources.

    Args:
        start_date: Start of the query period
        end_date: End of the query period
        cloud_provider: Optional cloud provider filter
        cluster_id: Optional cluster ID filter
        limit: Maximum number of results
        db: Database session

    Returns:
        List of top resources by cost
    """
    conditions = [
        CostRecord.usage_start >= start_date,
        CostRecord.usage_start <= end_date,
        CostRecord.resource_id.isnot(None),
    ]
    if cloud_provider:
        conditions.append(CostRecord.cloud_provider == cloud_provider)
    if cluster_id:
        conditions.append(CostRecord.cluster_id == cluster_id)

    query = select(
        CostRecord.resource_id,
        CostRecord.resource_name,
        CostRecord.resource_type,
        CostRecord.service_name,
        CostRecord.cloud_provider,
        CostRecord.region,
        func.sum(CostRecord.cost_amount).label("total_cost"),
        func.count(CostRecord.id).label("usage_hours"),
    ).where(and_(*conditions)).group_by(
        CostRecord.resource_id,
        CostRecord.resource_name,
        CostRecord.resource_type,
        CostRecord.service_name,
        CostRecord.cloud_provider,
        CostRecord.region,
    ).order_by(func.sum(CostRecord.cost_amount).desc()).limit(limit)

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
            "total_cost": row.total_cost or Decimal("0"),
            "usage_hours": row.usage_hours or 0,
        }
        for row in rows
    ]


@router.post("/records", response_model=CostRecordResponse)
async def create_cost_record(
    record: CostRecordCreate,
    db: AsyncSession = Depends(get_db),
) -> CostRecordResponse:
    """Create a new cost record.

    Args:
        record: Cost record data
        db: Database session

    Returns:
        Created cost record
    """
    db_record = CostRecord(
        **record.model_dump(),
    )
    db.add(db_record)
    await db.commit()
    await db.refresh(db_record)

    logger.info("cost_record_created", cost_record_id=str(db_record.id))

    return CostRecordResponse.model_validate(db_record)


@router.get("/records/{record_id}")
async def get_cost_record(
    record_id: str,
    db: AsyncSession = Depends(get_db),
) -> CostRecordResponse:
    """Get a specific cost record.

    Args:
        record_id: Cost record ID
        db: Database session

    Returns:
        Cost record details
    """
    from sqlalchemy import text
    from uuid import UUID

    query = select(CostRecord).where(CostRecord.id == UUID(record_id))
    result = await db.execute(query)
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(status_code=404, detail="Cost record not found")

    return CostRecordResponse.model_validate(record)
