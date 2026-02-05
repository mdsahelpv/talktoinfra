"""Cost Optimization Service.

Generates cost optimization recommendations based on cost data and utilization.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import CostRecord, Recommendation
from app.schemas import (
    CloudProvider,
    RecommendationCreate,
    RecommendationPriority,
    RecommendationType,
    ResourceType,
)
import structlog

logger = structlog.get_logger()


class CostOptimizationService:
    """Service for generating cost optimization recommendations.

    Analyzes cost data and utilization metrics to identify
    opportunities for cost savings.
    """

    # Idle resource thresholds
    IDLE_CPU_THRESHOLD = 20.0  # Percent
    IDLE_MEMORY_THRESHOLD = 20.0  # Percent

    # Right-sizing thresholds
    RIGHT_SIZE_CPU_THRESHOLD = 40.0  # Percent
    RIGHT_SIZE_MEMORY_THRESHOLD = 50.0  # Percent

    # Spot instance thresholds
    SPOT_AVAILABILITY_THRESHOLD = 70.0  # Percent (stability required)

    def __init__(self) -> None:
        """Initialize the cost optimization service."""
        self.settings = get_settings()

    async def generate_recommendations(
        self,
        cloud_provider: Optional[CloudProvider] = None,
        cluster_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> List[RecommendationCreate]:
        """Generate cost optimization recommendations.

        Args:
            cloud_provider: Optional cloud provider filter
            cluster_id: Optional cluster ID filter
            db: Database session

        Returns:
            List of recommendation objects
        """
        recommendations: List[RecommendationCreate] = []

        # Generate different types of recommendations
        idle_recommendations = await self._find_idle_resources(
            cloud_provider=cloud_provider,
            cluster_id=cluster_id,
            db=db,
        )
        recommendations.extend(idle_recommendations)

        right_sizing_recommendations = await self._find_right_sizing_opportunities(
            cloud_provider=cloud_provider,
            cluster_id=cluster_id,
            db=db,
        )
        recommendations.extend(right_sizing_recommendations)

        reserved_instance_recommendations = await self._find_reserved_instance_opportunities(
            cloud_provider=cloud_provider,
            cluster_id=cluster_id,
            db=db,
        )
        recommendations.extend(reserved_instance_recommendations)

        storage_recommendations = await self._find_storage_optimization_opportunities(
            cloud_provider=cloud_provider,
            cluster_id=cluster_id,
            db=db,
        )
        recommendations.extend(storage_recommendations)

        logger.info(
            "recommendations_generated",
            total=len(recommendations),
            cloud_provider=cloud_provider,
            cluster_id=cluster_id,
        )

        return recommendations

    async def _find_idle_resources(
        self,
        cloud_provider: Optional[CloudProvider],
        cluster_id: Optional[str],
        db: Optional[AsyncSession],
    ) -> List[RecommendationCreate]:
        """Find resources that appear to be idle or underutilized."""
        recommendations: List[RecommendationCreate] = []

        if not db:
            return recommendations

        # Query for resources with low usage patterns
        conditions = [
            CostRecord.cost_amount > Decimal("0"),
        ]
        if cloud_provider:
            conditions.append(CostRecord.cloud_provider == cloud_provider)
        if cluster_id:
            conditions.append(CostRecord.cluster_id == cluster_id)

        # Find resources with few usage records (indicating low activity)
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
            .having(func.count(CostRecord.id) < 5)  # Very few records
            .order_by(func.sum(CostRecord.cost_amount).desc())
            .limit(20)
        )

        result = await db.execute(query)
        rows = result.all()

        for row in rows:
            monthly_cost = row.total_cost or Decimal("0")
            annual_savings = monthly_cost * 12

            # Determine priority based on cost
            priority = RecommendationPriority.LOW
            if annual_savings > 10000:
                priority = RecommendationPriority.CRITICAL
            elif annual_savings > 5000:
                priority = RecommendationPriority.HIGH
            elif annual_savings > 1000:
                priority = RecommendationPriority.MEDIUM

            recommendations.append(
                RecommendationCreate(
                    cloud_provider=row.cloud_provider or CloudProvider.AWS,
                    resource_type=self._map_resource_type(row.resource_type),
                    resource_id=row.resource_id,
                    resource_name=row.resource_name,
                    recommendation_type=RecommendationType.DELETE_IDLE,
                    title=f"Delete idle resource: {row.resource_name or row.resource_id}",
                    description=(
                        f"Resource {row.resource_name or row.resource_id} appears to be idle "
                        f"(low usage detected). Current monthly cost: ${monthly_cost:.2f}. "
                        f"Consider terminating or downsizing this resource."
                    ),
                    current_cost=monthly_cost,
                    estimated_savings=annual_savings,
                    priority=priority,
                    action_steps=[
                        f"Verify resource {row.resource_id} is no longer needed",
                        "Check for any dependent resources",
                        "Create snapshot if data needs to be preserved",
                        "Terminate the resource",
                        "Update any automation that might recreate it",
                    ],
                    risks=[
                        "Data loss if resource is still in use",
                        "Dependent resources may be affected",
                        "Application functionality may be impacted",
                    ],
                    prerequisites=[
                        "Confirm resource is not in use",
                        "Notify stakeholders before deletion",
                    ],
                    utilization_data={
                        "usage_records": row.usage_records,
                        "total_cost": float(monthly_cost),
                    },
                    source="cost_analysis",
                    confidence_score=85.0,
                )
            )

        return recommendations

    async def _find_right_sizing_opportunities(
        self,
        cloud_provider: Optional[CloudProvider],
        cluster_id: Optional[str],
        db: Optional[AsyncSession],
    ) -> List[RecommendationCreate]:
        """Find resources that could be right-sized."""
        recommendations: List[RecommendationCreate] = []

        if not db:
            return recommendations

        # Find high-cost resources that might be oversized
        conditions = [
            CostRecord.resource_type.in_([
                "ec2", "rds", "elasticsearch", "cache", "kubernetes_pod"
            ]),
            CostRecord.cost_amount > Decimal("10"),  # Significant cost
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
            .limit(20)
        )

        result = await db.execute(query)
        rows = result.all()

        for row in rows:
            monthly_cost = row.monthly_cost or Decimal("0")

            # Estimate 30% savings from right-sizing
            estimated_savings = monthly_cost * Decimal("0.30")
            annual_savings = estimated_savings * 12

            # Determine priority
            priority = RecommendationPriority.LOW
            if annual_savings > 5000:
                priority = RecommendationPriority.HIGH
            elif annual_savings > 1000:
                priority = RecommendationPriority.MEDIUM

            recommendations.append(
                RecommendationCreate(
                    cloud_provider=row.cloud_provider or CloudProvider.AWS,
                    resource_type=self._map_resource_type(row.resource_type),
                    resource_id=row.resource_id,
                    resource_name=row.resource_name,
                    recommendation_type=RecommendationType.RIGHT_SIZE,
                    title=f"Right-size resource: {row.resource_name or row.resource_id}",
                    description=(
                        f"Resource {row.resource_name or row.resource_id} may be oversized. "
                        f"Current monthly cost: ${monthly_cost:.2f}. "
                        f"Consider reducing instance size for ~30% savings."
                    ),
                    current_cost=monthly_cost,
                    estimated_savings=annual_savings,
                    priority=priority,
                    action_steps=[
                        f"Analyze utilization metrics for {row.resource_id}",
                        "Identify appropriate smaller instance type",
                        "Test application performance with smaller instance",
                        "Schedule maintenance window for change",
                        "Resize the resource",
                        "Monitor performance after resize",
                    ],
                    risks=[
                        "Performance degradation if instance is too small",
                        "Application may require specific instance features",
                        "Brief downtime during resize",
                    ],
                    right_sizing_data={
                        "current_monthly_cost": float(monthly_cost),
                        "estimated_savings_percent": 30.0,
                        "recommended_action": "downsize",
                    },
                    source="cost_analysis",
                    confidence_score=75.0,
                )
            )

        return recommendations

    async def _find_reserved_instance_opportunities(
        self,
        cloud_provider: Optional[CloudProvider],
        cluster_id: Optional[str],
        db: Optional[AsyncSession],
    ) -> List[RecommendationCreate]:
        """Find resources that would benefit from reserved instances."""
        recommendations: List[RecommendationCreate] = []

        if not db:
            return recommendations

        # Find consistently running on-demand resources
        conditions = [
            CostRecord.cost_amount > Decimal("50"),  # Significant cost
        ]
        if cloud_provider:
            conditions.append(CostRecord.cloud_provider == cloud_provider)
        if cluster_id:
            conditions.append(CostRecord.cluster_id == cluster_id)

        query = (
            select(
                CostRecord.service_name,
                CostRecord.cloud_provider,
                func.sum(CostRecord.cost_amount).label("monthly_cost"),
                func.count(func.distinct(CostRecord.resource_id)
                           ).label("resource_count"),
            )
            .where(and_(*conditions))
            .group_by(
                CostRecord.service_name,
                CostRecord.cloud_provider,
            )
            .order_by(func.sum(CostRecord.cost_amount).desc())
            .limit(10)
        )

        result = await db.execute(query)
        rows = result.all()

        for row in rows:
            monthly_cost = row.monthly_cost or Decimal("0")

            # 40% savings estimate with 1-year reserved instance
            reserved_savings = monthly_cost * Decimal("0.40")
            annual_savings = reserved_savings * 12

            if annual_savings < 1000:
                continue  # Skip small savings

            recommendations.append(
                RecommendationCreate(
                    cloud_provider=row.cloud_provider or CloudProvider.AWS,
                    resource_type=self._map_resource_type(row.service_name),
                    recommendation_type=RecommendationType.RESERVED_INSTANCE,
                    title=f"Purchase reserved instances for {row.service_name}",
                    description=(
                        f"Service {row.service_name} has consistent monthly costs of ${monthly_cost:.2f}. "
                        f"Reserved instances could save ~40% annually (${annual_savings:.2f})."
                    ),
                    current_cost=monthly_cost,
                    estimated_savings=annual_savings,
                    priority=RecommendationPriority.MEDIUM,
                    action_steps=[
                        f"Analyze usage patterns for {row.service_name}",
                        "Determine appropriate instance family and size",
                        "Choose reservation term (1-year or 3-year)",
                        "Select payment option (no upfront, partial, or all upfront)",
                        "Purchase reserved capacity",
                        "Associate reserved instances with running resources",
                    ],
                    risks=[
                        "Commitment for 1-3 years",
                        "Usage patterns may change",
                        "Unused reserved instances are wasted",
                    ],
                    right_sizing_data={
                        "monthly_on_demand": float(monthly_cost),
                        "reserved_savings_percent": 40.0,
                        "term_options": ["1_year", "3_year"],
                    },
                    source="cost_analysis",
                    confidence_score=90.0,
                )
            )

        return recommendations

    async def _find_storage_optimization_opportunities(
        self,
        cloud_provider: Optional[CloudProvider],
        cluster_id: Optional[str],
        db: Optional[AsyncSession],
    ) -> List[RecommendationCreate]:
        """Find storage resources that could be optimized."""
        recommendations: List[RecommendationCreate] = []

        if not db:
            return recommendations

        # Find storage resources
        conditions = [
            CostRecord.resource_type.in_([
                "ebs", "s3", "efs", "storage", "disk"
            ]),
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
                func.sum(CostRecord.cost_amount).label("monthly_cost"),
            )
            .where(and_(*conditions))
            .group_by(
                CostRecord.resource_id,
                CostRecord.resource_name,
                CostRecord.resource_type,
                CostRecord.service_name,
                CostRecord.cloud_provider,
            )
            .order_by(func.sum(CostRecord.cost_amount).desc())
            .limit(15)
        )

        result = await db.execute(query)
        rows = result.all()

        for row in rows:
            monthly_cost = row.monthly_cost or Decimal("0")

            # 20% savings from storage optimization
            estimated_savings = monthly_cost * Decimal("0.20")
            annual_savings = estimated_savings * 12

            if annual_savings < 100:
                continue

            # Determine optimization type
            if row.resource_type in ["ebs", "disk"]:
                opt_type = RecommendationType.STORAGE_OPTIMIZE
                title = f"Migrate EBS volume to gp3: {row.resource_name or row.resource_id}"
                description = (
                    f"EBS volume {row.resource_name or row.resource_id} may benefit from "
                    f"gp3 storage (20% cheaper than gp2 with better performance)."
                )
            else:
                opt_type = RecommendationType.STORAGE_OPTIMIZE
                title = f"Optimize storage: {row.resource_name or row.resource_id}"
                description = (
                    f"Storage resource {row.resource_name or row.resource_id} "
                    f"may have optimization opportunities."
                )

            recommendations.append(
                RecommendationCreate(
                    cloud_provider=row.cloud_provider or CloudProvider.AWS,
                    resource_type=ResourceType.STORAGE,
                    resource_id=row.resource_id,
                    resource_name=row.resource_name,
                    recommendation_type=opt_type,
                    title=title,
                    description=description,
                    current_cost=monthly_cost,
                    estimated_savings=annual_savings,
                    priority=RecommendationPriority.LOW,
                    action_steps=[
                        f"Analyze access patterns for {row.resource_id}",
                        "Identify infrequently accessed data",
                        "Move cold data to cheaper storage tier",
                        "Delete unused snapshots",
                        "Consider compression or deduplication",
                    ],
                    risks=[
                        "Performance impact from storage tier changes",
                        "Data retrieval delays for cold storage",
                        "Potential compatibility issues",
                    ],
                    source="cost_analysis",
                    confidence_score=70.0,
                )
            )

        return recommendations

    def _map_resource_type(self, resource_type: Optional[str]) -> Optional[ResourceType]:
        """Map string resource type to enum."""
        type_mapping = {
            "ec2": ResourceType.EC2,
            "rds": ResourceType.RDS,
            "s3": ResourceType.S3,
            "eks": ResourceType.EKS,
            "ebs": ResourceType.EBS,
            "lambda": ResourceType.LAMBDA,
            "kubernetes_pod": ResourceType.KUBERNETES_POD,
            "kubernetes_deployment": ResourceType.KUBERNETES_DEPLOYMENT,
            "kubernetes_service": ResourceType.KUBERNETES_SERVICE,
            "redis": ResourceType.REDIS,
            "postgresql": ResourceType.POSTGRESQL,
            "mysql": ResourceType.MYSQL,
            "mongodb": ResourceType.MONGODB,
        }
        return type_mapping.get(resource_type.lower() if resource_type else "", ResourceType.OTHER)

    def calculate_potential_savings(
        self,
        recommendations: List[RecommendationCreate],
    ) -> Dict[str, Any]:
        """Calculate total potential savings from recommendations.

        Args:
            recommendations: List of recommendations

        Returns:
            Savings summary by type and priority
        """
        by_type: Dict[str, Decimal] = {}
        by_priority: Dict[str, Decimal] = {}

        for rec in recommendations:
            savings = rec.estimated_savings or Decimal("0")

            # Group by type
            rec_type = rec.recommendation_type.value
            by_type[rec_type] = by_type.get(rec_type, Decimal("0")) + savings

            # Group by priority
            priority = rec.priority.value
            by_priority[priority] = by_priority.get(
                priority, Decimal("0")) + savings

        total_monthly = sum(by_type.values())
        total_yearly = total_monthly * 12

        return {
            "total_potential_savings_monthly": total_monthly,
            "total_potential_savings_yearly": total_yearly,
            "by_type": {k: float(v) for k, v in by_type.items()},
            "by_priority": {k: float(v) for k, v in by_priority.items()},
            "recommendation_count": len(recommendations),
        }
