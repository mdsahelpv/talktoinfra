"""Cost Anomaly Detection Service.

Provides statistical anomaly detection for cost data using Z-score,
IQR (Interquartile Range), and threshold-based methods.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
import statistics
import numpy as np

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CostRecord, CostAnomaly, DailyCostAggregation
from app.schemas import (
    AnomalyType,
    AnomalySeverity,
    AnomalyStatus,
    CloudProvider,
    CostAnomalyCreate,
)
import structlog

logger = structlog.get_logger()


class AnomalyDetectorService:
    """Service for detecting cost anomalies using statistical methods.

    Supports Z-score, IQR, and threshold-based anomaly detection.
    """

    # Default thresholds
    DEFAULT_ZSCORE_THRESHOLD = 2.0
    DEFAULT_IQR_MULTIPLIER = 1.5
    DEFAULT_MIN_HISTORY_DAYS = 7

    # Anomaly detection thresholds
    SPENDING_SPIKE_THRESHOLD = 2.0  # 200% increase
    NEW_RESOURCE_COST_THRESHOLD = Decimal("100")  # $100/day
    IDLE_RESOURCE_DAYS = 30
    DATA_TRANSFER_SPIKE = 3.0  # 300% increase

    def __init__(self) -> None:
        """Initialize the anomaly detection service."""
        self.sensitivity = self.DEFAULT_ZSCORE_THRESHOLD

    async def detect_anomalies(
        self,
        start_date: datetime,
        end_date: datetime,
        cloud_provider: Optional[CloudProvider] = None,
        cluster_id: Optional[str] = None,
        sensitivity: float = DEFAULT_ZSCORE_THRESHOLD,
        db: Optional[AsyncSession] = None,
    ) -> List[CostAnomalyCreate]:
        """Detect anomalies in cost data.

        Args:
            start_date: Start of the detection period
            end_date: End of the detection period
            cloud_provider: Optional cloud provider filter
            cluster_id: Optional cluster ID filter
            sensitivity: Z-score threshold (higher = less sensitive)
            db: Database session

        Returns:
            List of detected anomalies
        """
                   return []

        self.sensitivity = sensitivity
 if not db:
        anomalies: List[CostAnomalyCreate] = []

        # Get historical data for baseline
        baseline_start = start_date - timedelta(days=30)
        historical_data = await self._get_historical_costs(
            db, baseline_start, start_date, cloud_provider, cluster_id
        )

        # Get current period data
        current_data = await self._get_current_costs(
            db, start_date, end_date, cloud_provider, cluster_id
        )

        # Run detection methods
        spending_spikes = await self._detect_spending_spikes(
            current_data, historical_data
        )
        anomalies.extend(spending_spikes)

        new_resources = await self._detect_new_expensive_resources(
            db, start_date, end_date, cloud_provider, cluster_id
        )
        anomalies.extend(new_resources)

        idle_resources = await self._detect_idle_resources(
            db, start_date, end_date, cloud_provider, cluster_id
        )
        anomalies.extend(idle_resources)

        data_transfer_spikes = await self._detect_data_transfer_spikes(
            db, start_date, end_date, cloud_provider, cluster_id
        )
        anomalies.extend(data_transfer_spikes)

        unused_volumes = await self._detect_unused_volumes(
            db, start_date, end_date, cloud_provider, cluster_id
        )
        anomalies.extend(unused_volumes)

        # Statistical anomaly detection
        statistical_anomalies = await self._detect_statistical_anomalies(
            current_data, historical_data
        )
        anomalies.extend(statistical_anomalies)

        logger.info(
            "anomaly_detection_completed",
            total_anomalies=len(anomalies),
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
        )

        return anomalies

    async def _get_historical_costs(
        self,
        db: AsyncSession,
        start_date: datetime,
        end_date: datetime,
        cloud_provider: Optional[CloudProvider],
        cluster_id: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Get historical cost data for baseline calculation."""
        conditions = [
            CostRecord.usage_start >= start_date,
            CostRecord.usage_start <= end_date,
        ]
        if cloud_provider:
            conditions.append(CostRecord.cloud_provider == cloud_provider)
        if cluster_id:
            conditions.append(CostRecord.cluster_id == cluster_id)

        query = select(
            func.date(CostRecord.usage_start).label("date"),
            func.sum(CostRecord.cost_amount).label("total_cost"),
            CostRecord.service_name,
            CostRecord.resource_id,
        ).where(and_(*conditions)).group_by(
            func.date(CostRecord.usage_start),
            CostRecord.service_name,
            CostRecord.resource_id,
        )

        result = await db.execute(query)
        return [
            {
                "date": row.date,
                "total_cost": row.total_cost or Decimal("0"),
                "service_name": row.service_name,
                "resource_id": row.resource_id,
            }
            for row in result.all()
        ]

    async def _get_current_costs(
        self,
        db: AsyncSession,
        start_date: datetime,
        end_date: datetime,
        cloud_provider: Optional[CloudProvider],
        cluster_id: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Get current period cost data."""
        conditions = [
            CostRecord.usage_start >= start_date,
            CostRecord.usage_start <= end_date,
        ]
        if cloud_provider:
            conditions.append(CostRecord.cloud_provider == cloud_provider)
        if cluster_id:
            conditions.append(CostRecord.cluster_id == cluster_id)

        query = select(
            CostRecord.id,
            CostRecord.resource_id,
            CostRecord.resource_name,
            CostRecord.resource_type,
            CostRecord.service_name,
            CostRecord.cloud_provider,
            CostRecord.region,
            CostRecord.cost_amount,
            CostRecord.usage_start,
        ).where(and_(*conditions))

        result = await db.execute(query)
        return [
            {
                "id": row.id,
                "resource_id": row.resource_id,
                "resource_name": row.resource_name,
                "resource_type": row.resource_type,
                "service_name": row.service_name,
                "cloud_provider": row.cloud_provider,
                "region": row.region,
                "cost_amount": row.cost_amount or Decimal("0"),
                "usage_start": row.usage_start,
            }
            for row in result.all()
        ]

    async def _detect_spending_spikes(
        self,
        current_data: List[Dict[str, Any]],
        historical_data: List[Dict[str, Any]],
    ) -> List[CostAnomalyCreate]:
        """Detect sudden spending spikes compared to historical baseline.
        
        Detects: "AWS spend increased $500/day (usual: $100/day)"
        """
        anomalies: List[CostAnomalyCreate] = []

        # Calculate historical daily average by provider
        historical_by_provider: Dict[str, List[Decimal]] = {}
        for item in historical_data:
            provider = str(item.get("cloud_provider", "unknown"))
            if provider not in historical_by_provider:
                historical_by_provider[provider] = []
            historical_by_provider[provider].append(item["total_cost"])

        # Calculate current daily average by provider
        current_by_provider: Dict[str, Decimal] = {}
        for item in current_data:
            provider = str(item.get("cloud_provider", "unknown"))
            if provider not in current_by_provider:
                current_by_provider[provider] = Decimal("0")
            current_by_provider[provider] += item["cost_amount"]

        # Check for spikes
        for provider, current_cost in current_by_provider.items():
            historical_costs = historical_by_provider.get(provider, [])
            if not historical_costs:
                continue

            avg_historical = sum(historical_costs) / len(historical_costs)
            if avg_historical <= 0:
                continue

            change_percent = float((current_cost - avg_historical) / avg_historical * 100)

            if change_percent >= (self.SPENDING_SPIKE_THRESHOLD * 100):
                # Determine severity
                severity = AnomalySeverity.WARNING
                if change_percent >= 500:
                    severity = AnomalySeverity.CRITICAL
                elif change_percent >= 300:
                    severity = AnomalySeverity.WARNING
                else:
                    severity = AnomalySeverity.INFO

                anomalies.append(
                    CostAnomalyCreate(
                        cloud_provider=CloudProvider(provider.lower()) 
                            if provider.lower() in [p.value for p in CloudProvider] 
                            else CloudProvider.AWS,
                        anomaly_type=AnomalyType.SPENDING_SPIKE,
                        severity=severity,
                        title=f"Spending spike detected: {provider}",
                        description=(
                            f"{provider} spend increased {change_percent:.0f}% "
                            f"(current: ${current_cost:.2f}/day vs usual: ${avg_historical:.2f}/day)"
                        ),
                        baseline_value=avg_historical,
                        current_value=current_cost,
                        expected_value=avg_historical * Decimal("1.5"),
                        change_percent=change_percent,
                        cost_impact=current_cost - avg_historical,
                        detection_method="threshold",
                        confidence_score=85.0,
                    )
                )

        return anomalies

    async def _detect_new_expensive_resources(
        self,
        db: AsyncSession,
        start_date: datetime,
        end_date: datetime,
        cloud_provider: Optional[CloudProvider],
        cluster_id: Optional[str],
    ) -> List[CostAnomalyCreate]:
        """Detect new expensive resources.
        
        Detects: "New expensive instance type detected: m5.24xlarge"
        """
        anomalies: List[CostAnomalyCreate] = []

        # Look for new resources in current period
        lookback_start = start_date - timedelta(days=7)
        
        # Get resources that appeared in current period
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
            func.sum(CostRecord.cost_amount).label("total_cost"),
        ).where(and_(*conditions)).group_by(
            CostRecord.resource_id,
            CostRecord.resource_name,
            CostRecord.resource_type,
            CostRecord.service_name,
            CostRecord.cloud_provider,
        ).having(func.sum(CostRecord.cost_amount) >= self.NEW_RESOURCE_COST_THRESHOLD)

        result = await db.execute(query)
        
        for row in result.all():
            total_cost = row.total_cost or Decimal("0")
            
            # Check if this is a new resource by looking for previous costs
            prev_query = select(func.count(CostRecord.id)).where(
                and_(
                    CostRecord.resource_id == row.resource_id,
                    CostRecord.usage_start < start_date,
                )
            )
            prev_result = await db.execute(prev_query)
            prev_count = prev_result.scalar() or 0

            if prev_count == 0:  # New resource
                anomalies.append(
                    CostAnomalyCreate(
                        cloud_provider=row.cloud_provider or CloudProvider.AWS,
                        anomaly_type=AnomalyType.NEW_EXPENSIVE_RESOURCE,
                        severity=AnomalySeverity.WARNING,
                        title=f"New expensive resource: {row.resource_name or row.resource_id}",
                        description=(
                            f"New resource detected with high cost: "
                            f"{row.resource_type or row.service_name}. "
                            f"Monthly cost: ${total_cost:.2f}"
                        ),
                        resource_id=row.resource_id,
                        resource_name=row.resource_name,
                        resource_type=row.resource_type,
                        service_name=row.service_name,
                        current_value=total_cost,
                        cost_impact=total_cost,
                        detection_method="threshold",
                        confidence_score=90.0,
                    )
                )

        return anomalies

    async def _detect_idle_resources(
        self,
        db: AsyncSession,
        start_date: datetime,
        end_date: datetime,
        cloud_provider: Optional[CloudProvider],
        cluster_id: Optional[str],
    ) -> List[CostAnomalyCreate]:
        """Detect idle resources that are still incurring costs.
        
        Detects resources that have costs but minimal usage.
        """
        anomalies: List[CostAnomalyCreate] = []

        # Find resources with consistent low-cost patterns (likely idle)
        conditions = [
            CostRecord.usage_start >= start_date - timedelta(days=self.IDLE_RESOURCE_DAYS),
            CostRecord.usage_start <= end_date,
            CostRecord.cost_amount > Decimal("0"),
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
            func.sum(CostRecord.cost_amount).label("total_cost"),
            func.count(CostRecord.id).label("usage_count"),
        ).where(and_(*conditions)).group_by(
            CostRecord.resource_id,
            CostRecord.resource_name,
            CostRecord.resource_type,
            CostRecord.service_name,
            CostRecord.cloud_provider,
        ).having(
            and_(
                func.count(CostRecord.id) >= 20,  # Consistent presence
                func.count(CostRecord.id) <= 25,  # But low (assuming ~daily)
                func.sum(CostRecord.cost_amount) > Decimal("10"),
            )
        )

        result = await db.execute(query)
        
        for row in result.all():
            total_cost = row.total_cost or Decimal("0")
            
            # Calculate daily average
            daily_avg = total_cost / row.usage_count if row.usage_count > 0 else Decimal("0")
            
            anomalies.append(
                CostAnomalyCreate(
                    cloud_provider=row.cloud_provider or CloudProvider.AWS,
                    anomaly_type=AnomalyType.IDLE_RESOURCE,
                    severity=AnomalySeverity.INFO,
                    title=f"Idle resource detected: {row.resource_name or row.resource_id}",
                    description=(
                        f"Resource appears to be idle but still incurring costs. "
                        f"Monthly cost: ${total_cost:.2f}. "
                        f"Consider terminating or downsizing."
                    ),
                    resource_id=row.resource_id,
                    resource_name=row.resource_name,
                    resource_type=row.resource_type,
                    service_name=row.service_name,
                    current_value=total_cost,
                    cost_impact=total_cost,
                    detection_method="usage_pattern",
                    confidence_score=75.0,
                )
            )

        return anomalies

    async def _detect_data_transfer_spikes(
        self,
        db: AsyncSession,
        start_date: datetime,
        end_date: datetime,
        cloud_provider: Optional[CloudProvider],
        cluster_id: Optional[str],
    ) -> List[CostAnomalyCreate]:
        """Detect data transfer cost spikes.
        
        Detects: "Data transfer costs spiked 500%"
        """
        anomalies: List[CostAnomalyCreate] = []

        # Look for data transfer services
        transfer_services = ["nat-gateway", "natgateway", "data-transfer", "egress", "internet"]
        
        conditions = [
            CostRecord.usage_start >= start_date,
            CostRecord.usage_start <= end_date,
            CostRecord.service_name.ilike("%nat%") | 
            CostRecord.service_name.ilike("%transfer%") |
            CostRecord.service_name.ilike("%egress%") |
            CostRecord.service_name.ilike("%internet%"),
        ]
        if cloud_provider:
            conditions.append(CostRecord.cloud_provider == cloud_provider)
        if cluster_id:
            conditions.append(CostRecord.cluster_id == cluster_id)

        query = select(
            CostRecord.service_name,
            CostRecord.cloud_provider,
            func.sum(CostRecord.cost_amount).label("current_cost"),
        ).where(and_(*conditions)).group_by(
            CostRecord.service_name,
            CostRecord.cloud_provider,
        )

        result = await db.execute(query)
        
        for row in result.all():
            current_cost = row.current_cost or Decimal("0")
            
            # Compare with previous period
            prev_conditions = [
                CostRecord.usage_start >= start_date - timedelta(days=30),
                CostRecord.usage_start < start_date,
                CostRecord.service_name == row.service_name,
            ]
            if cloud_provider:
                prev_conditions.append(CostRecord.cloud_provider == cloud_provider)
            if cluster_id:
                prev_conditions.append(CostRecord.cluster_id == cluster_id)
            
            prev_query = select(
                func.sum(CostRecord.cost_amount).label("prev_cost"),
            ).where(and_(*prev_conditions))
            
            prev_result = await db.execute(prev_query)
            prev_cost = prev_result.scalar() or Decimal("0")
            
            if prev_cost > 0:
                change_percent = float((current_cost - prev_cost) / prev_cost * 100)
                
                if change_percent >= (self.DATA_TRANSFER_SPIKE * 100):
                    anomalies.append(
                        CostAnomalyCreate(
                            cloud_provider=row.cloud_provider or CloudProvider.AWS,
                            anomaly_type=AnomalyType.DATA_TRANSFER_SPIKE,
                            severity=AnomalySeverity.CRITICAL if change_percent >= 500 
                                else AnomalySeverity.WARNING,
                            title=f"Data transfer spike: {row.service_name}",
                            description=(
                                f"Data transfer costs spiked {change_percent:.0f}% "
                                f"(current: ${current_cost:.2f} vs previous: ${prev_cost:.2f})"
                            ),
                            baseline_value=prev_cost,
                            current_value=current_cost,
                            change_percent=change_percent,
                            service_name=row.service_name,
                            cost_impact=current_cost - prev_cost,
                            detection_method="threshold",
                            confidence_score=80.0,
                        )
                    )

        return anomalies

    async def _detect_unused_volumes(
        self,
        db: AsyncSession,
        start_date: datetime,
        end_date: datetime,
        cloud_provider: Optional[CloudProvider],
        cluster_id: Optional[str],
    ) -> List[CostAnomalyCreate]:
        """Detect unused storage volumes.
        
        Detects: "Unused EBS volumes costing $200/month"
        """
        anomalies: List[CostAnomalyCreate] = []

        conditions = [
            CostRecord.usage_start >= start_date,
            CostRecord.usage_start <= end_date,
            CostRecord.resource_type.in_(["ebs", "volume", "disk"]),
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
        ).where(and_(*conditions)).group_by(
            CostRecord.resource_id,
            CostRecord.resource_name,
            CostRecord.resource_type,
            CostRecord.service_name,
            CostRecord.cloud_provider,
            CostRecord.region,
        )

        result = await db.execute(query)
        
        for row in result.all():
            total_cost = row.total_cost or Decimal("0")
            
            # If monthly cost > $50, it might be an unused expensive volume
            if total_cost >= Decimal("50"):
                anomalies.append(
                    CostAnomalyCreate(
                        cloud_provider=row.cloud_provider or CloudProvider.AWS,
                        anomaly_type=AnomalyType.UNUSED_VOLUME,
                        severity=AnomalySeverity.WARNING,
                        title=f"Potential unused volume: {row.resource_name or row.resource_id}",
                        description=(
                            f"EBS volume {row.resource_name or row.resource_id} "
                            f"costing ${total_cost:.2f}/month. "
                            f"Verify if still in use and consider deletion."
                        ),
                        resource_id=row.resource_id,
                        resource_name=row.resource_name,
                        resource_type=row.resource_type,
                        service_name=row.service_name,
                        region=row.region,
                        current_value=total_cost,
                        cost_impact=total_cost,
                        detection_method="threshold",
                        confidence_score=70.0,
                    )
                )

        return anomalies

    async def _detect_statistical_anomalies(
        self,
        current_data: List[Dict[str, Any]],
        historical_data: List[Dict[str, Any]],
    ) -> List[CostAnomalyCreate]:
        """Detect anomalies using Z-score statistical method."""
        anomalies: List[CostAnomalyCreate] = []

        if not historical_data or len(historical_data) < 5:
            return anomalies

        # Group historical data by day
        daily_costs: List[float] = []
        for item in historical_data:
            cost = float(item["total_cost"])
            if cost > 0:
                daily_costs.append(cost)

        if len(daily_costs) < 5:
            return anomalies

        # Calculate statistics
        mean_cost = statistics.mean(daily_costs)
        stdev_cost = statistics.stdev(daily_costs) if len(daily_costs) > 1 else 0

        if stdev_cost == 0:
            return anomalies

        # Calculate current daily total
        current_daily_total = sum(float(item["cost_amount"]) for item in current_data)
        
        # Calculate Z-score
        z_score = (current_daily_total - mean_cost) / stdev_cost

        if abs(z_score) >= self.sensitivity:
            change_percent = z_score * 100
            anomalies.append(
                CostAnomalyCreate(
                    cloud_provider=CloudProvider.AWS,
                    anomaly_type=AnomalyType.ANOMALY_DETECTED,
                    severity=AnomalySeverity.CRITICAL if abs(z_score) >= 3.0 
                        else AnomalySeverity.WARNING,
                    title=f"Statistical cost anomaly detected",
                    description=(
                        f"Cost pattern deviates significantly from historical baseline. "
                        f"Z-score: {z_score:.2f} (threshold: {self.sensitivity})"
                    ),
                    baseline_value=Decimal(str(mean_cost)),
                    current_value=Decimal(str(current_daily_total)),
                    change_percent=change_percent,
                    cost_impact=Decimal(str(abs(current_daily_total - mean_cost))),
                    detection_method="zscore",
                    confidence_score=min(95.0, abs(z_score) * 30),
                )
            )

        return anomalies

    async def save_anomalies(
        self,
        anomalies: List[CostAnomalyCreate],
        db: AsyncSession,
    ) -> int:
        """Save detected anomalies to database.
        
        Args:
            anomalies: List of anomaly objects to save
            db: Database session
            
        Returns:
            Number of anomalies saved
        """
        saved_count = 0
        
        for anomaly in anomalies:
            db_anomaly = CostAnomaly(**anomaly.model_dump())
            db.add(db_anomaly)
            saved_count += 1

        await db.commit()
        
        logger.info("anomalies_saved", count=saved_count)
        
        return saved_count
