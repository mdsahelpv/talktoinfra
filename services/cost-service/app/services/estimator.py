"""Cost Estimation Service.

Calculates estimated costs for infrastructure resources across cloud providers.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.config import get_settings
from app.schemas import CloudProvider, PricingModelType, ResourceSpec
import structlog

logger = structlog.get_logger()


class CostEstimatorService:
    """Service for estimating infrastructure costs.

    Provides cost estimates for various cloud resources across
    AWS, Azure, and GCP with support for different pricing models.
    """

    # AWS EC2 pricing (USD per hour, approximate)
    AWS_EC2_PRICING = {
        "t3.micro": Decimal("0.0104"),
        "t3.small": Decimal("0.0208"),
        "t3.medium": Decimal("0.0416"),
        "t3.large": Decimal("0.0832"),
        "t3.xlarge": Decimal("0.1664"),
        "t3.2xlarge": Decimal("0.3328"),
        "m5.large": Decimal("0.0960"),
        "m5.xlarge": Decimal("0.1920"),
        "m5.2xlarge": Decimal("0.3840"),
        "m5.4xlarge": Decimal("0.7680"),
        "c5.large": Decimal("0.0850"),
        "c5.xlarge": Decimal("0.1700"),
        "c5.2xlarge": Decimal("0.3400"),
        "r5.large": Decimal("0.1260"),
        "r5.xlarge": Decimal("0.2520"),
        "r5.2xlarge": Decimal("0.5040"),
    }

    # AWS instance family multipliers for different sizes
    AWS_SIZE_MULTIPLIERS = {
        "nano": Decimal("0.05"),
        "micro": Decimal("0.1"),
        "small": Decimal("0.2"),
        "medium": Decimal("0.4"),
        "large": Decimal("0.8"),
        "xlarge": Decimal("1.6"),
        "2xlarge": Decimal("3.2"),
        "4xlarge": Decimal("6.4"),
        "8xlarge": Decimal("12.8"),
        "16xlarge": Decimal("25.6"),
    }

    # AWS storage pricing (USD per GB-month)
    AWS_STORAGE_PRICING = {
        "gp2": Decimal("0.10"),
        "gp3": Decimal("0.08"),
        "io1": Decimal("0.125"),
        "io2": Decimal("0.125"),
        "sc1": Decimal("0.015"),
        "st1": Decimal("0.045"),
    }

    # Azure VM pricing (USD per hour, approximate)
    AZURE_VM_PRICING = {
        "Standard_B1s": Decimal("0.0080"),
        "Standard_B2s": Decimal("0.0240"),
        "Standard_B4ms": Decimal("0.0480"),
        "Standard_D2s_v3": Decimal("0.0960"),
        "Standard_D4s_v3": Decimal("0.1920"),
        "Standard_D8s_v3": Decimal("0.3840"),
        "Standard_F2s_v2": Decimal("0.0840"),
        "Standard_F4s_v2": Decimal("0.1680"),
        "Standard_F8s_v2": Decimal("0.3360"),
    }

    # Azure storage pricing (USD per GB-month)
    AZURE_STORAGE_PRICING = {
        "Standard_LRS": Decimal("0.072"),
        "Standard_GRS": Decimal("0.144"),
        "Premium_LRS": Decimal("0.144"),
        "Premium_GRS": Decimal("0.288"),
    }

    # GCP instance pricing (USD per hour, approximate)
    GCP_VM_PRICING = {
        "e2-micro": Decimal("0.0096"),
        "e2-small": Decimal("0.0192"),
        "e2-medium": Decimal("0.0384"),
        "n1-standard-1": Decimal("0.0475"),
        "n1-standard-2": Decimal("0.0950"),
        "n1-standard-4": Decimal("0.1900"),
        "n1-standard-8": Decimal("0.3800"),
        "n2-standard-2": Decimal("0.1066"),
        "n2-standard-4": Decimal("0.2132"),
        "n2-standard-8": Decimal("0.4264"),
    }

    # GCP storage pricing (USD per GB-month)
    GCP_STORAGE_PRICING = {
        "standard": Decimal("0.020"),
        "nearline": Decimal("0.010"),
        "coldline": Decimal("0.004"),
        "pd-standard": Decimal("0.10"),
        "pd-ssd": Decimal("0.17"),
    }

    # Reserved instance discounts (percentage of on-demand)
    RESERVED_DISCOUNTS = {
        "1_year_no_upfront": Decimal("0.30"),
        "1_year_partial_upfront": Decimal("0.40"),
        "1_year_all_upfront": Decimal("0.45"),
        "3_year_no_upfront": Decimal("0.50"),
        "3_year_partial_upfront": Decimal("0.60"),
        "3_year_all_upfront": Decimal("0.65"),
    }

    # Spot instance discounts (percentage of on-demand)
    SPOT_DISCOUNTS = {
        "general_purpose": Decimal("0.60"),
        "compute_optimized": Decimal("0.70"),
        "memory_optimized": Decimal("0.65"),
        "storage_optimized": Decimal("0.50"),
    }

    def __init__(self) -> None:
        """Initialize the cost estimator."""
        self.settings = get_settings()
        self.hourly_to_monthly = self.settings.hourly_to_monthly_multiplier

    async def estimate(
        self,
        resource_spec: ResourceSpec,
        cloud_provider: CloudProvider,
        region: str,
        pricing_model: PricingModelType = PricingModelType.ON_DEMAND,
        term_length: Optional[str] = None,
        payment_option: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Estimate cost for a resource specification.

        Args:
            resource_spec: Resource specifications (CPU, memory, etc.)
            cloud_provider: Cloud provider
            region: AWS region
            pricing_model: Pricing model (on_demand, reserved, spot)
            term_length: Reserved instance term length
            payment_option: Reserved instance payment option

        Returns:
            Dictionary with cost breakdown
        """
        # Calculate compute cost
        compute_cost = await self._calculate_compute_cost(
            resource_spec=resource_spec,
            cloud_provider=cloud_provider,
            region=region,
            pricing_model=pricing_model,
            term_length=term_length,
            payment_option=payment_option,
        )

        # Calculate storage cost
        storage_cost = await self._calculate_storage_cost(
            storage_gb=resource_spec.storage_gb or 0,
            storage_type=resource_spec.storage_type or "gp3",
            cloud_provider=cloud_provider,
        )

        # Calculate network cost
        network_cost = await self._calculate_network_cost(
            resource_spec=resource_spec,
            cloud_provider=cloud_provider,
            region=region,
        )

        # Calculate other costs
        other_costs = await self._calculate_other_costs(
            resource_spec=resource_spec,
            cloud_provider=cloud_provider,
        )

        # Total costs
        hourly_cost = compute_cost + storage_cost + network_cost + other_costs
        monthly_cost = hourly_cost * self.hourly_to_monthly
        yearly_cost = monthly_cost * 12

        # Get on-demand cost for comparison
        on_demand_compute = await self._calculate_compute_cost(
            resource_spec=resource_spec,
            cloud_provider=cloud_provider,
            region=region,
            pricing_model=PricingModelType.ON_DEMAND,
        )
        on_demand_hourly = (
            on_demand_compute +
            storage_cost +
            network_cost +
            other_costs
        )

        # Calculate savings
        savings = None
        savings_percent = None
        if pricing_model != PricingModelType.ON_DEMAND:
            savings = on_demand_hourly - hourly_cost
            savings_percent = float(
                savings / on_demand_hourly * 100) if on_demand_hourly > 0 else 0

        # Get alternatives
        alternatives = await self._get_alternatives(
            resource_spec=resource_spec,
            cloud_provider=cloud_provider,
            region=region,
            on_demand_hourly=on_demand_hourly,
        )

        return {
            "id": str(uuid4()),
            "cloud_provider": cloud_provider,
            "region": region,
            "pricing_model": pricing_model.value,
            "resource_spec": resource_spec.model_dump(),
            "hourly_cost": round(hourly_cost, 6),
            "daily_cost": round(hourly_cost * 24, 4),
            "monthly_cost": round(monthly_cost, 2),
            "yearly_cost": round(yearly_cost, 2),
            "currency": self.settings.default_currency,
            "breakdown": {
                "compute": round(compute_cost, 6),
                "storage": round(storage_cost, 4),
                "network": round(network_cost, 4),
                "other": round(other_costs, 4),
            },
            "on_demand_hourly": round(on_demand_hourly, 6),
            "savings": round(savings, 6) if savings else None,
            "savings_percent": round(savings_percent, 2) if savings_percent else None,
            "comparison": {
                "on_demand_hourly": round(on_demand_hourly, 6),
                "savings": round(savings, 6) if savings else None,
                "savings_percent": round(savings_percent, 2) if savings_percent else None,
                "alternatives": alternatives,
            },
            "created_at": datetime.utcnow(),
        }

    async def _calculate_compute_cost(
        self,
        resource_spec: ResourceSpec,
        cloud_provider: CloudProvider,
        region: str,
        pricing_model: PricingModelType,
        term_length: Optional[str] = None,
        payment_option: Optional[str] = None,
    ) -> Decimal:
        """Calculate compute cost based on specifications."""
        # Base cost calculation using CPU and memory
        base_hourly = Decimal("0")

        if cloud_provider == CloudProvider.AWS:
            base_hourly = self._calculate_aws_compute(
                resource_spec, pricing_model, term_length, payment_option)
        elif cloud_provider == CloudProvider.AZURE:
            base_hourly = self._calculate_azure_compute(
                resource_spec, pricing_model, term_length, payment_option)
        elif cloud_provider == CloudProvider.GCP:
            base_hourly = self._calculate_gcp_compute(
                resource_spec, pricing_model, term_length, payment_option)
        else:
            # Default pricing for unknown providers
            base_hourly = Decimal(
                str(resource_spec.cpu_cores * 0.03 + resource_spec.memory_gb * 0.01))

        return base_hourly

    def _calculate_aws_compute(
        self,
        resource_spec: ResourceSpec,
        pricing_model: PricingModelType,
        term_length: Optional[str],
        payment_option: Optional[str],
    ) -> Decimal:
        """Calculate AWS compute cost."""
        # Use instance name if provided
        if resource_spec.instance_name and resource_spec.instance_name in self.AWS_EC2_PRICING:
            hourly = self.AWS_EC2_PRICING[resource_spec.instance_name]
        else:
            # Estimate based on CPU and memory
            hourly = Decimal(str(resource_spec.cpu_cores *
                             0.04 + resource_spec.memory_gb * 0.01))

        # Apply pricing model discounts
        if pricing_model == PricingModelType.RESERVED_1_YEAR:
            if term_length == "1_year":
                if payment_option == "all_upfront":
                    hourly *= self.RESERVED_DISCOUNTS["1_year_all_upfront"]
                elif payment_option == "partial_upfront":
                    hourly *= self.RESERVED_DISCOUNTS["1_year_partial_upfront"]
                else:
                    hourly *= self.RESERVED_DISCOUNTS["1_year_no_upfront"]
        elif pricing_model == PricingModelType.RESERVED_3_YEAR:
            if term_length == "3_year":
                if payment_option == "all_upfront":
                    hourly *= self.RESERVED_DISCOUNTS["3_year_all_upfront"]
                elif payment_option == "partial_upfront":
                    hourly *= self.RESERVED_DISCOUNTS["3_year_partial_upfront"]
                else:
                    hourly *= self.RESERVED_DISCOUNTS["3_year_no_upfront"]
        elif pricing_model == PricingModelType.SPOT:
            hourly *= self.SPOT_DISCOUNTS["general_purpose"]

        return hourly

    def _calculate_azure_compute(
        self,
        resource_spec: ResourceSpec,
        pricing_model: PricingModelType,
        term_length: Optional[str],
        payment_option: Optional[str],
    ) -> Decimal:
        """Calculate Azure compute cost."""
        # Use instance name if provided
        if resource_spec.instance_name and resource_spec.instance_name in self.AZURE_VM_PRICING:
            hourly = self.AZURE_VM_PRICING[resource_spec.instance_name]
        else:
            # Estimate based on CPU and memory
            hourly = Decimal(str(resource_spec.cpu_cores *
                             0.045 + resource_spec.memory_gb * 0.012))

        # Apply pricing model discounts
        if pricing_model == PricingModelType.RESERVED_1_YEAR:
            if term_length == "1_year":
                hourly *= self.RESERVED_DISCOUNTS["1_year_partial_upfront"]
        elif pricing_model == PricingModelType.RESERVED_3_YEAR:
            if term_length == "3_year":
                hourly *= self.RESERVED_DISCOUNTS["3_year_partial_upfront"]
        elif pricing_model == PricingModelType.SPOT:
            hourly *= self.SPOT_DISCOUNTS["general_purpose"]

        return hourly

    def _calculate_gcp_compute(
        self,
        resource_spec: ResourceSpec,
        pricing_model: PricingModelType,
        term_length: Optional[str],
        payment_option: Optional[str],
    ) -> Decimal:
        """Calculate GCP compute cost."""
        # Use instance name if provided
        if resource_spec.instance_name and resource_spec.instance_name in self.GCP_VM_PRICING:
            hourly = self.GCP_VM_PRICING[resource_spec.instance_name]
        else:
            # Estimate based on CPU and memory
            hourly = Decimal(str(resource_spec.cpu_cores *
                             0.035 + resource_spec.memory_gb * 0.008))

        # Apply pricing model discounts
        if pricing_model == PricingModelType.RESERVED_1_YEAR:
            if term_length == "1_year":
                hourly *= Decimal("0.63")  # GCP 1-year commitment discount
        elif pricing_model == PricingModelType.RESERVED_3_YEAR:
            if term_length == "3_year":
                hourly *= Decimal("0.48")  # GCP 3-year commitment discount
        elif pricing_model == PricingModelType.SPOT:
            hourly *= self.SPOT_DISCOUNTS["general_purpose"]

        return hourly

    async def _calculate_storage_cost(
        self,
        storage_gb: float,
        storage_type: str,
        cloud_provider: CloudProvider,
    ) -> Decimal:
        """Calculate storage cost."""
        if storage_gb <= 0:
            return Decimal("0")

        monthly_cost = Decimal("0")

        if cloud_provider == CloudProvider.AWS:
            storage_rate = self.AWS_STORAGE_PRICING.get(
                storage_type.lower(), self.AWS_STORAGE_PRICING["gp3"]
            )
            monthly_cost = Decimal(str(storage_gb)) * storage_rate
        elif cloud_provider == CloudProvider.AZURE:
            storage_rate = self.AZURE_STORAGE_PRICING.get(
                storage_type.lower(
                ), self.AZURE_STORAGE_PRICING["Standard_LRS"]
            )
            monthly_cost = Decimal(str(storage_gb)) * storage_rate
        elif cloud_provider == CloudProvider.GCP:
            storage_rate = self.GCP_STORAGE_PRICING.get(
                storage_type.lower(), self.GCP_STORAGE_PRICING["pd-standard"]
            )
            monthly_cost = Decimal(str(storage_gb)) * storage_rate
        else:
            monthly_cost = Decimal(str(storage_gb)) * Decimal("0.10")

        return monthly_cost / Decimal(str(self.hourly_to_monthly))

    async def _calculate_network_cost(
        self,
        resource_spec: ResourceSpec,
        cloud_provider: CloudProvider,
        region: str,
    ) -> Decimal:
        """Calculate network egress cost."""
        egress_gb = resource_spec.monthly_network_egress_gb or 0

        if egress_gb <= 0:
            return Decimal("0")

        # Network pricing per GB (approximate)
        network_rates = {
            CloudProvider.AWS: Decimal("0.09"),  # $0.09/GB for first 1TB
            CloudProvider.AZURE: Decimal("0.08"),  # $0.08/GB for first 5GB
            CloudProvider.GCP: Decimal("0.12"),  # $0.12/GB for first 1TB
        }

        rate = network_rates.get(cloud_provider, Decimal("0.10"))
        monthly_cost = Decimal(str(egress_gb)) * rate

        return monthly_cost / Decimal(str(self.hourly_to_monthly))

    async def _calculate_other_costs(
        self,
        resource_spec: ResourceSpec,
        cloud_provider: CloudProvider,
    ) -> Decimal:
        """Calculate other costs (load balancer, etc.)."""
        # Placeholder for additional costs
        # Could include: load balancer, managed services, monitoring, etc.
        return Decimal("0")

    async def _get_alternatives(
        self,
        resource_spec: ResourceSpec,
        cloud_provider: CloudProvider,
        region: str,
        on_demand_hourly: Decimal,
    ) -> List[Dict[str, Any]]:
        """Get alternative configuration options."""
        alternatives = []

        if cloud_provider == CloudProvider.AWS:
            # Suggest smaller instance types
            alternatives.extend([
                {
                    "instance_type": "t3.medium",
                    "description": "Smaller instance type",
                    "hourly_cost": round(self.AWS_EC2_PRICING["t3.medium"], 4),
                    "monthly_cost": round(self.AWS_EC2_PRICING["t3.medium"] * self.hourly_to_monthly, 2),
                    "savings_percent": round(
                        float(
                            (on_demand_hourly - self.AWS_EC2_PRICING["t3.medium"]) / on_demand_hourly * 100)
                        if on_demand_hourly > 0 else 0,
                        1,
                    ),
                },
                {
                    "instance_type": "m5.large",
                    "description": "Alternative instance family",
                    "hourly_cost": round(self.AWS_EC2_PRICING["m5.large"], 4),
                    "monthly_cost": round(self.AWS_EC2_PRICING["m5.large"] * self.hourly_to_monthly, 2),
                    "savings_percent": round(
                        float(
                            (on_demand_hourly - self.AWS_EC2_PRICING["m5.large"]) / on_demand_hourly * 100)
                        if on_demand_hourly > 0 else 0,
                        1,
                    ),
                },
            ])

        return alternatives

    def get_recommended_instance_types(
        self,
        cloud_provider: CloudProvider,
        cpu_cores: int,
        memory_gb: int,
        region: str,
    ) -> List[Dict[str, Any]]:
        """Get recommended instance types based on requirements.

        Args:
            cloud_provider: Cloud provider
            cpu_cores: Minimum CPU cores required
            memory_gb: Minimum memory GB required
            region: AWS region

        Returns:
            List of recommended instance types
        """
        recommendations = []

        if cloud_provider == CloudProvider.AWS:
            # AWS instance recommendations
            instance_families = [
                ("t3", "general_purpose"),
                ("m5", "general_purpose"),
                ("c5", "compute_optimized"),
                ("r5", "memory_optimized"),
            ]

            for family, category in instance_families:
                for size in ["medium", "large", "xlarge", "2xlarge"]:
                    instance_name = f"{family}.{size}"
                    if instance_name in self.AWS_EC2_PRICING:
                        recommendations.append({
                            "instance_type": instance_name,
                            "category": category,
                            "hourly_cost": float(self.AWS_EC2_PRICING[instance_name]),
                            "monthly_cost": float(self.AWS_EC2_PRICING[instance_name] * self.hourly_to_monthly),
                        })

        elif cloud_provider == CloudProvider.AZURE:
            # Azure VM recommendations
            for name, hourly in list(self.AZURE_VM_PRICING.items())[:5]:
                recommendations.append({
                    "instance_type": name,
                    "hourly_cost": float(hourly),
                    "monthly_cost": float(hourly * self.hourly_to_monthly),
                })

        elif cloud_provider == CloudProvider.GCP:
            # GCP VM recommendations
            for name, hourly in list(self.GCP_VM_PRICING.items())[:5]:
                recommendations.append({
                    "instance_type": name,
                    "hourly_cost": float(hourly),
                    "monthly_cost": float(hourly * self.hourly_to_monthly),
                })

        # Sort by cost
        recommendations.sort(key=lambda x: x["hourly_cost"])

        return recommendations[:10]  # Return top 10
