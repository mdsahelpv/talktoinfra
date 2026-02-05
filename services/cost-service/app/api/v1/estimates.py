"""Cost Estimation API Endpoints.

API endpoints for estimating infrastructure costs before deployment.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from app.database import get_db
from app.models import CostEstimate
from app.schemas import (
    CloudProvider,
    CostEstimateRequest,
    CostEstimateResponse,
    PricingModelType,
    ResourceSpec,
)
from app.services.estimator import CostEstimatorService
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/estimates", tags=["Cost Estimation"])


@router.post("", response_model=CostEstimateResponse)
async def create_cost_estimate(
    estimate_request: CostEstimateRequest,
    db: AsyncSession = Depends(get_db),
) -> CostEstimateResponse:
    """Estimate cost for given resource specifications.

    Args:
        estimate_request: Resource specifications and parameters
        db: Database session

    Returns:
        Cost estimate with breakdown and alternatives
    """
    estimator = CostEstimatorService()

    # Calculate costs
    estimate = await estimator.estimate(
        resource_spec=estimate_request.resource_spec,
        cloud_provider=estimate_request.cloud_provider,
        region=estimate_request.region,
        pricing_model=estimate_request.pricing_model,
        term_length=estimate_request.term_length,
        payment_option=estimate_request.payment_option,
    )

    # Save estimate to database
    db_estimate = CostEstimate(
        id=estimate["id"],
        resource_spec=estimate_request.resource_spec.model_dump(),
        cloud_provider=estimate_request.cloud_provider,
        region=estimate_request.region,
        pricing_model=estimate_request.pricing_model.value,
        term_length=estimate_request.term_length,
        payment_option=estimate_request.payment_option,
        hourly_cost=estimate["hourly_cost"],
        monthly_cost=estimate["monthly_cost"],
        yearly_cost=estimate["yearly_cost"],
        cost_breakdown=estimate.get("breakdown"),
        comparison=estimate.get("comparison"),
        expires_at=datetime.utcnow() + timedelta(hours=24),
    )
    db.add(db_estimate)
    await db.commit()

    logger.info(
        "cost_estimate_created",
        estimate_id=estimate["id"],
        cloud_provider=estimate_request.cloud_provider.value,
        region=estimate_request.region,
        monthly_cost=str(estimate["monthly_cost"]),
    )

    return CostEstimateResponse(**estimate)


@router.get("/{estimate_id}")
async def get_cost_estimate(
    estimate_id: str,
    db: AsyncSession = Depends(get_db),
) -> CostEstimateResponse:
    """Get a previously saved cost estimate.

    Args:
        estimate_id: Estimate ID
        db: Database session

    Returns:
        Cost estimate details
    """
    from uuid import UUID

    query = select(CostEstimate).where(CostEstimate.id == UUID(estimate_id))
    result = await db.execute(query)
    estimate = result.scalar_one_or_none()

    if not estimate:
        raise HTTPException(status_code=404, detail="Cost estimate not found")

    if estimate.expires_at and estimate.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=410, detail="Cost estimate has expired")

    return CostEstimateResponse(
        id=str(estimate.id),
        cloud_provider=estimate.cloud_provider,
        region=estimate.region,
        pricing_model=estimate.pricing_model,
        resource_spec=estimate.resource_spec,
        hourly_cost=estimate.hourly_cost,
        daily_cost=estimate.hourly_cost * 24,
        monthly_cost=estimate.monthly_cost,
        yearly_cost=estimate.yearly_cost,
        compute_cost=estimate.cost_breakdown.get(
            "compute", estimate.monthly_cost) if estimate.cost_breakdown else estimate.monthly_cost,
        storage_cost=estimate.cost_breakdown.get("storage", Decimal(
            "0")) if estimate.cost_breakdown else Decimal("0"),
        network_cost=estimate.cost_breakdown.get("network", Decimal(
            "0")) if estimate.cost_breakdown else Decimal("0"),
        other_costs=Decimal("0"),
        on_demand_hourly=estimate.comparison.get(
            "on_demand_hourly", estimate.hourly_cost) if estimate.comparison else estimate.hourly_cost,
        savings_with_pricing_model=estimate.comparison.get(
            "savings", None) if estimate.comparison else None,
        savings_percentage=estimate.comparison.get(
            "savings_percent", None) if estimate.comparison else None,
        alternatives=estimate.comparison.get(
            "alternatives", []) if estimate.comparison else None,
        created_at=estimate.created_at,
        expires_at=estimate.expires_at,
    )


@router.post("/compare")
async def compare_cost_estimates(
    resource_spec: ResourceSpec,
    cloud_provider: CloudProvider,
    region: str,
    pricing_models: List[PricingModelType],
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Compare costs across different pricing models.

    Args:
        resource_spec: Resource specifications
        cloud_provider: Cloud provider
        region: AWS region
        pricing_models: List of pricing models to compare
        db: Database session

    Returns:
        Comparison of costs across pricing models
    """
    estimator = CostEstimatorService()

    comparisons = []
    on_demand_cost = None

    for model in pricing_models:
        estimate = await estimator.estimate(
            resource_spec=resource_spec,
            cloud_provider=cloud_provider,
            region=region,
            pricing_model=model,
        )

        comparisons.append({
            "pricing_model": model.value,
            "hourly_cost": estimate["hourly_cost"],
            "monthly_cost": estimate["monthly_cost"],
            "yearly_cost": estimate["yearly_cost"],
            "upfront_cost": estimate.get("upfront_cost", Decimal("0")),
        })

        if model == PricingModelType.ON_DEMAND:
            on_demand_cost = estimate["monthly_cost"]

    # Calculate savings for each model vs on-demand
    for comparison in comparisons:
        if on_demand_cost and comparison["pricing_model"] != "on_demand":
            savings = on_demand_cost - comparison["monthly_cost"]
            comparison["savings_monthly"] = savings
            comparison["savings_percent"] = float(
                savings / on_demand_cost * 100) if on_demand_cost > 0 else 0

    return {
        "resource_spec": resource_spec.model_dump(),
        "cloud_provider": cloud_provider.value,
        "region": region,
        "comparisons": comparisons,
        "recommended_model": min(
            comparisons,
            key=lambda x: x["monthly_cost"] if x["pricing_model"] != "on_demand" else float(
                "inf")
        )["pricing_model"] if comparisons else None,
    }


@router.get("/instance-types/{cloud_provider}")
async def get_recommended_instance_types(
    cloud_provider: CloudProvider,
    cpu_cores: int = 2,
    memory_gb: int = 8,
    region: str = "us-east-1",
) -> List[Dict[str, Any]]:
    """Get recommended instance types based on resource requirements.

    Args:
        cloud_provider: Cloud provider
        cpu_cores: Minimum CPU cores required
        memory_gb: Minimum memory GB required
        region: AWS region

    Returns:
        List of recommended instance types with costs
    """
    estimator = CostEstimatorService()

    return estimator.get_recommended_instance_types(
        cloud_provider=cloud_provider,
        cpu_cores=cpu_cores,
        memory_gb=memory_gb,
        region=region,
    )


@router.get("/pricing-models")
async def get_pricing_models(
    cloud_provider: CloudProvider,
) -> Dict[str, Any]:
    """Get available pricing models for a cloud provider.

    Args:
        cloud_provider: Cloud provider

    Returns:
        Available pricing models and their characteristics
    """
    models_info = {
        CloudProvider.AWS: {
            "on_demand": {
                "description": "Pay per hour with no commitment",
                "best_for": "Short-term, unpredictable, or testing workloads",
                "flexibility": "High",
                "savings": "None",
            },
            "reserved_1_year": {
                "description": "1-year commitment with significant discounts",
                "best_for": "Predictable, steady-state workloads",
                "flexibility": "Medium",
                "savings": "30-40% vs on-demand",
            },
            "reserved_3_year": {
                "description": "3-year commitment with maximum discounts",
                "best_for": "Long-term, stable production workloads",
                "flexibility": "Low",
                "savings": "50-60% vs on-demand",
            },
            "spot": {
                "description": "Unused capacity at deep discounts",
                "best_for": "Fault-tolerant, flexible workloads",
                "flexibility": "Low - can be interrupted",
                "savings": "60-90% vs on-demand",
            },
        },
        CloudProvider.AZURE: {
            "on_demand": {
                "description": "Pay per second with no commitment",
                "best_for": "Short-term and development workloads",
                "flexibility": "High",
                "savings": "None",
            },
            "reserved_vm_1_year": {
                "description": "1-year reserved capacity commitment",
                "best_for": "Predictable workloads",
                "flexibility": "Medium",
                "savings": "40-50% vs on-demand",
            },
            "reserved_vm_3_year": {
                "description": "3-year reserved capacity commitment",
                "best_for": "Long-term production workloads",
                "flexibility": "Low",
                "savings": "55-65% vs on-demand",
            },
            "spot": {
                "description": "Unused capacity at reduced prices",
                "best_for": "Interruptible workloads",
                "flexibility": "Low",
                "savings": "60-90% vs on-demand",
            },
        },
        CloudProvider.GCP: {
            "on_demand": {
                "description": "Pay per second with no commitment",
                "best_for": "Short-term and variable workloads",
                "flexibility": "High",
                "savings": "None",
            },
            "committed_use_1_year": {
                "description": "1-year resource commitment",
                "best_for": "Predictable baseline workloads",
                "flexibility": "Medium",
                "savings": "37% vs on-demand",
            },
            "committed_use_3_year": {
                "description": "3-year resource commitment",
                "best_for": "Long-term production workloads",
                "flexibility": "Low",
                "savings": "52% vs on-demand",
            },
            "preemptible": {
                "description": "Short-lived, heavily discounted instances",
                "best_for": "Batch processing, fault-tolerant workloads",
                "flexibility": "Very low - max 24 hours",
                "savings": "60-90% vs on-demand",
            },
        },
    }

    return models_info.get(cloud_provider, {})
