"""Budget API Endpoints.

API endpoints for budget management and alerts.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Budget, BudgetAlert, CostRecord
from app.schemas import (
    BudgetAlertResponse,
    BudgetBase,
    BudgetCreate,
    BudgetResponse,
    BudgetUpdate,
    CloudProvider,
)
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/budgets", tags=["Budgets"])


def calculate_percentage_used(current: Decimal, budget: Decimal) -> float:
    """Calculate percentage of budget used."""
    if budget <= 0:
        return 0.0
    return float(current / budget * 100)


async def check_budget_thresholds(
    db: AsyncSession,
    budget: Budget,
    current_spend: Decimal,
) -> Optional[BudgetAlert]:
    """Check if budget thresholds have been exceeded and create alerts."""
    if not budget.alert_thresholds:
        return None

    percentage_used = calculate_percentage_used(current_spend, budget.amount)

    # Find the highest threshold exceeded
    exceeded_thresholds = [
        t for t in budget.alert_thresholds if percentage_used >= t]

    if not exceeded_thresholds:
        return None

    highest_threshold = max(exceeded_thresholds)

    # Check if we already alerted for this threshold
    last_alert = await db.execute(
        select(BudgetAlert).where(
            and_(
                BudgetAlert.budget_id == budget.id,
                BudgetAlert.threshold_percent == highest_threshold,
                BudgetAlert.status == "active",
            )
        )
    )

    if last_alert.scalar_one_or_none():
        return None  # Already alerted

    # Create alert
    alert = BudgetAlert(
        budget_id=budget.id,
        alert_type="threshold_exceeded",
        threshold_percent=highest_threshold,
        spend_amount=current_spend,
        budget_amount=budget.amount,
        percentage_used=percentage_used,
        status="active",
    )
    db.add(alert)

    # Update last alert time
    budget.last_alert_at = datetime.utcnow()

    await db.commit()
    await db.refresh(alert)

    logger.info(
        "budget_alert_triggered",
        budget_id=str(budget.id),
        threshold=highest_threshold,
        percentage_used=percentage_used,
    )

    return alert


@router.get("", response_model=List[BudgetResponse])
async def list_budgets(
    cloud_provider: Optional[CloudProvider] = Query(
        None, description="Filter by cloud provider"),
    cluster_id: Optional[str] = Query(
        None, description="Filter by cluster ID"),
    is_active: Optional[bool] = Query(
        None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db),
) -> List[BudgetResponse]:
    """List all budgets with optional filters.

    Args:
        cloud_provider: Optional cloud provider filter
        cluster_id: Optional cluster ID filter
        is_active: Optional active status filter
        db: Database session

    Returns:
        List of budgets
    """
    conditions = []
    if cloud_provider:
        conditions.append(Budget.cloud_provider == cloud_provider)
    if cluster_id:
        conditions.append(Budget.cluster_id == cluster_id)
    if is_active is not None:
        conditions.append(Budget.is_active == (1 if is_active else 0))

    query = select(Budget).where(and_(*conditions)
                                 ).order_by(Budget.created_at.desc())

    result = await db.execute(query)
    budgets = result.scalars().all()

    # Calculate current spend for each budget
    for budget in budgets:
        if budget.is_active == 1:
            spend_query = select(
                func.sum(CostRecord.cost_amount)
            ).where(and_(
                CostRecord.usage_start >= budget.start_date,
                CostRecord.usage_start <= (
                    budget.end_date or datetime.utcnow()),
                *([CostRecord.cloud_provider == budget.cloud_provider]
                  if budget.cloud_provider else []),
                *([CostRecord.cluster_id == budget.cluster_id]
                  if budget.cluster_id else []),
            ))
            spend_result = await db.execute(spend_query)
            current_spend = spend_result.scalar() or Decimal("0")

            budget.current_spend = current_spend
            await check_budget_thresholds(db, budget, current_spend)

    return [BudgetResponse.model_validate(b) for b in budgets]


@router.get("/{budget_id}", response_model=BudgetResponse)
async def get_budget(
    budget_id: str,
    db: AsyncSession = Depends(get_db),
) -> BudgetResponse:
    """Get a specific budget with current spend.

    Args:
        budget_id: Budget ID
        db: Database session

    Returns:
        Budget details
    """
    from uuid import UUID

    query = select(Budget).where(Budget.id == UUID(budget_id))
    result = await db.execute(query)
    budget = result.scalar_one_or_none()

    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")

    # Calculate current spend
    if budget.is_active == 1:
        spend_query = select(
            func.sum(CostRecord.cost_amount)
        ).where(and_(
            CostRecord.usage_start >= budget.start_date,
            CostRecord.usage_start <= (budget.end_date or datetime.utcnow()),
            *([CostRecord.cloud_provider == budget.cloud_provider]
              if budget.cloud_provider else []),
            *([CostRecord.cluster_id == budget.cluster_id]
              if budget.cluster_id else []),
        ))
        spend_result = await db.execute(spend_query)
        current_spend = spend_result.scalar() or Decimal("0")

        budget.current_spend = current_spend
        await check_budget_thresholds(db, budget, current_spend)
        await db.refresh(budget)

    return BudgetResponse.model_validate(budget)


@router.post("", response_model=BudgetResponse)
async def create_budget(
    budget_data: BudgetCreate,
    db: AsyncSession = Depends(get_db),
) -> BudgetResponse:
    """Create a new budget.

    Args:
        budget_data: Budget creation data
        db: Database session

    Returns:
        Created budget
    """
    budget = Budget(
        **budget_data.model_dump(),
        current_spend=Decimal("0"),
        is_active=1,
    )
    db.add(budget)
    await db.commit()
    await db.refresh(budget)

    logger.info("budget_created", budget_id=str(budget.id))

    return BudgetResponse.model_validate(budget)


@router.patch("/{budget_id}", response_model=BudgetResponse)
async def update_budget(
    budget_id: str,
    budget_data: BudgetUpdate,
    db: AsyncSession = Depends(get_db),
) -> BudgetResponse:
    """Update an existing budget.

    Args:
        budget_id: Budget ID
        budget_data: Update data
        db: Database session

    Returns:
        Updated budget
    """
    from uuid import UUID

    query = select(Budget).where(Budget.id == UUID(budget_id))
    result = await db.execute(query)
    budget = result.scalar_one_or_none()

    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")

    # Update fields
    update_data = budget_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(budget, field, value)

    await db.commit()
    await db.refresh(budget)

    logger.info("budget_updated", budget_id=str(budget.id))

    return BudgetResponse.model_validate(budget)


@router.delete("/{budget_id}")
async def delete_budget(
    budget_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Delete a budget.

    Args:
        budget_id: Budget ID
        db: Database session

    Returns:
        Success message
    """
    from uuid import UUID

    query = select(Budget).where(Budget.id == UUID(budget_id))
    result = await db.execute(query)
    budget = result.scalar_one_or_none()

    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")

    await db.delete(budget)
    await db.commit()

    logger.info("budget_deleted", budget_id=str(budget_id))

    return {"message": "Budget deleted successfully"}


@router.get("/{budget_id}/alerts", response_model=List[BudgetAlertResponse])
async def get_budget_alerts(
    budget_id: str,
    status: Optional[str] = Query(None, description="Filter by alert status"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    db: AsyncSession = Depends(get_db),
) -> List[BudgetAlertResponse]:
    """Get alerts for a budget.

    Args:
        budget_id: Budget ID
        status: Optional status filter
        limit: Maximum number of results
        db: Database session

    Returns:
        List of budget alerts
    """
    from uuid import UUID

    conditions = [BudgetAlert.budget_id == UUID(budget_id)]
    if status:
        conditions.append(BudgetAlert.status == status)

    query = select(BudgetAlert).where(
        and_(*conditions)
    ).order_by(BudgetAlert.triggered_at.desc()).limit(limit)

    result = await db.execute(query)
    alerts = result.scalars().all()

    return [BudgetAlertResponse.model_validate(a) for a in alerts]


@router.get("/alerts", response_model=List[BudgetAlertResponse])
async def list_all_alerts(
    status: Optional[str] = Query(None, description="Filter by alert status"),
    cloud_provider: Optional[CloudProvider] = Query(
        None, description="Filter by cloud provider"),
    limit: int = Query(100, ge=1, le=200, description="Maximum results"),
    db: AsyncSession = Depends(get_db),
) -> List[BudgetAlertResponse]:
    """List all budget alerts.

    Args:
        status: Optional status filter
        cloud_provider: Optional cloud provider filter
        limit: Maximum number of results
        db: Database session

    Returns:
        List of all budget alerts
    """
    conditions = []
    if status:
        conditions.append(BudgetAlert.status == status)

    if cloud_provider:
        conditions.append(Budget.cloud_provider == cloud_provider)
        query = (
            select(BudgetAlert)
            .join(Budget, BudgetAlert.budget_id == Budget.id)
            .where(and_(*conditions))
            .order_by(BudgetAlert.triggered_at.desc())
            .limit(limit)
        )
    else:
        query = (
            select(BudgetAlert)
            .where(and_(*conditions))
            .order_by(BudgetAlert.triggered_at.desc())
            .limit(limit)
        )

    result = await db.execute(query)
    alerts = result.scalars().all()

    return [BudgetAlertResponse.model_validate(a) for a in alerts]


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
) -> BudgetAlertResponse:
    """Acknowledge a budget alert.

    Args:
        alert_id: Alert ID
        db: Database session

    Returns:
        Updated alert
    """
    from uuid import UUID

    query = select(BudgetAlert).where(BudgetAlert.id == UUID(alert_id))
    result = await db.execute(query)
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = "acknowledged"
    alert.acknowledged_at = datetime.utcnow()

    await db.commit()
    await db.refresh(alert)

    logger.info("budget_alert_acknowledged", alert_id=str(alert_id))

    return BudgetAlertResponse.model_validate(alert)


@router.get("/summary")
async def get_budget_summary(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get overall budget summary.

    Args:
        db: Database session

    Returns:
        Budget summary statistics
    """
    # Count budgets by status
    active_query = select(func.count(Budget.id)).where(Budget.is_active == 1)
    inactive_query = select(func.count(Budget.id)).where(Budget.is_active == 0)

    active_result = await db.execute(active_query)
    inactive_result = await db.execute(inactive_query)

    active_count = active_result.scalar() or 0
    inactive_count = inactive_result.scalar() or 0

    # Get alerts summary
    active_alerts_query = select(func.count(BudgetAlert.id)).where(
        BudgetAlert.status == "active"
    )
    alerts_result = await db.execute(active_alerts_query)
    active_alerts = alerts_result.scalar() or 0

    # Calculate total budget and spend
    budgets_query = select(Budget).where(Budget.is_active == 1)
    budgets_result = await db.execute(budgets_query)
    budgets = budgets_result.scalars().all()

    total_budget = sum(b.amount for b in budgets)
    total_spend = sum(b.current_spend for b in budgets)

    # Count budgets near limit
    near_limit_count = sum(
        1 for b in budgets
        if calculate_percentage_used(b.current_spend, b.amount) >= 80
    )

    # Count exceeded budgets
    exceeded_count = sum(
        1 for b in budgets
        if calculate_percentage_used(b.current_spend, b.amount) >= 100
    )

    return {
        "total_budgets": active_count + inactive_count,
        "active_budgets": active_count,
        "inactive_budgets": inactive_count,
        "total_budget_amount": total_budget,
        "total_spend": total_spend,
        "utilization_percent": float(total_spend / total_budget * 100) if total_budget > 0 else 0,
        "active_alerts": active_alerts,
        "budgets_near_limit": near_limit_count,
        "budgets_exceeded": exceeded_count,
    }
