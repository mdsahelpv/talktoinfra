"""Cost Service Schemas.

Pydantic schemas for API request/response validation.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class CloudProvider(str, Enum):
    """Supported cloud providers."""

    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    KUBERNETES = "kubernetes"


class ResourceType(str, Enum):
    """Resource types for cost tracking."""

    EC2 = "ec2"
    RDS = "rds"
    S3 = "s3"
    EKS = "eks"
    LAMBDA = "lambda"
    EBS = "ebs"
    ELB = "elb"
    NAT_GATEWAY = "nat_gateway"
    REDIS = "redis"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MONGODB = "mongodb"
    KUBERNETES_POD = "kubernetes_pod"
    KUBERNETES_DEPLOYMENT = "kubernetes_deployment"
    KUBERNETES_SERVICE = "kubernetes_service"
    KUBERNETES_NAMESPACE = "kubernetes_namespace"
    CONTAINER = "container"
    VM = "vm"
    STORAGE = "storage"
    NETWORK = "network"
    SERVERLESS = "serverless"
    OTHER = "other"


class RecommendationType(str, Enum):
    """Types of cost optimization recommendations."""

    RIGHT_SIZE = "right_size"
    SPOT_INSTANCE = "spot_instance"
    RESERVED_INSTANCE = "reserved_instance"
    DELETE_IDLE = "delete_idle"
    STORAGE_OPTIMIZE = "storage_optimize"
    NETWORK_OPTIMIZE = "network_optimize"
    GRAVITY_UPGRADE = "gravity_upgrade"
    MULTI_CLOUD_SHIFT = "multi_cloud_shift"
    ARCHITECTURE_REFACTOR = "architecture_refactor"
    SCHEDULE_NON_PROD = "schedule_non_prod"


class RecommendationPriority(str, Enum):
    """Priority levels for recommendations."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ============ Cost Record Schemas ============

class CostRecordBase(BaseModel):
    """Base schema for cost records."""

    cloud_provider: CloudProvider
    account_id: Optional[str] = None
    account_name: Optional[str] = None
    region: Optional[str] = None
    availability_zone: Optional[str] = None
    service_name: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    resource_name: Optional[str] = None
    cost_amount: Decimal = Field(..., ge=0)
    currency: str = Field(default="USD", max_length=3)
    usage_quantity: Optional[Decimal] = None
    usage_unit: Optional[str] = None
    operation: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[Dict[str, str]] = None


class CostRecordCreate(CostRecordBase):
    """Schema for creating a cost record."""

    usage_start: datetime
    usage_end: Optional[datetime] = None


class CostRecordResponse(CostRecordBase):
    """Schema for cost record response."""

    id: str
    cluster_id: Optional[str] = None
    usage_start: datetime
    usage_end: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ Cost Query Schemas ============

class CostQueryParams(BaseModel):
    """Parameters for querying costs."""

    start_date: datetime
    end_date: datetime
    cloud_provider: Optional[CloudProvider] = None
    cluster_id: Optional[str] = None
    account_id: Optional[str] = None
    region: Optional[str] = None
    service_name: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    group_by: Optional[List[str]] = None
    granularity: str = Field(
        default="daily", pattern="^(hourly|daily|monthly)$")


class CostSummary(BaseModel):
    """Summary of costs."""

    total_cost: Decimal
    currency: str = "USD"
    period_start: datetime
    period_end: datetime
    resource_count: int = 0
    previous_period_cost: Optional[Decimal] = None
    cost_change_percent: Optional[float] = None


class CostByDimension(BaseModel):
    """Cost breakdown by dimension."""

    dimension: str
    dimension_value: str
    total_cost: Decimal
    percentage: float
    resource_count: int = 0


class CostTrendPoint(BaseModel):
    """Single point in cost trend data."""

    timestamp: datetime
    cost: Decimal


# ============ Budget Schemas ============

class BudgetBase(BaseModel):
    """Base schema for budgets."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    cloud_provider: Optional[CloudProvider] = None
    cluster_id: Optional[str] = None
    namespace: Optional[str] = None
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(default="USD", max_length=3)
    period: str = Field(default="monthly",
                        pattern="^(daily|weekly|monthly|quarterly|yearly)$")
    start_date: datetime
    end_date: Optional[datetime] = None
    alert_thresholds: Optional[List[int]] = None
    notify_email: Optional[List[str]] = None
    notify_slack: Optional[List[str]] = None
    notify_pagerduty: Optional[List[str]] = None


class BudgetCreate(BudgetBase):
    """Schema for creating a budget."""

    pass


class BudgetUpdate(BaseModel):
    """Schema for updating a budget."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    amount: Optional[Decimal] = Field(None, gt=0)
    period: Optional[str] = Field(
        None, pattern="^(daily|weekly|monthly|quarterly|yearly)$")
    end_date: Optional[datetime] = None
    alert_thresholds: Optional[List[int]] = None
    notify_email: Optional[List[str]] = None
    notify_slack: Optional[List[str]] = None
    notify_pagerduty: Optional[List[str]] = None
    is_active: Optional[bool] = None


class BudgetResponse(BudgetBase):
    """Schema for budget response."""

    id: str
    cluster_id: Optional[str] = None
    namespace: Optional[str] = None
    current_spend: Decimal
    percentage_used: float
    is_active: bool
    last_alert_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BudgetAlertResponse(BaseModel):
    """Schema for budget alert response."""

    id: str
    budget_id: str
    budget_name: str
    alert_type: str
    threshold_percent: float
    spend_amount: Decimal
    budget_amount: Decimal
    percentage_used: float
    status: str
    triggered_at: datetime
    acknowledged_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============ Cost Estimation Schemas ============

class ResourceSpec(BaseModel):
    """Resource specification for cost estimation."""

    cpu_cores: int = Field(..., ge=0)
    memory_gb: float = Field(..., ge=0)
    storage_gb: Optional[float] = Field(None, ge=0)
    storage_type: str = Field(
        default="gp3", pattern="^(gp2|gp3|io1|io2|sc1|st1)$")
    monthly_network_egress_gb: Optional[float] = Field(None, ge=0)
    monthly_requests: Optional[int] = Field(None, ge=0)
    operating_system: str = Field(default="linux")
    instance_family: Optional[str] = None
    instance_name: Optional[str] = None


class PricingModelType(str, Enum):
    """Pricing model options."""

    ON_DEMAND = "on_demand"
    RESERVED_1_YEAR = "reserved_1_year"
    RESERVED_3_YEAR = "reserved_3_year"
    SPOT = "spot"


class CostEstimateRequest(BaseModel):
    """Request for cost estimation."""

    resource_spec: ResourceSpec
    cloud_provider: CloudProvider
    region: str = Field(..., min_length=2, max_length=50)
    pricing_model: PricingModelType = PricingModelType.ON_DEMAND
    term_length: Optional[str] = Field(None, pattern="^(1_year|3_year)$")
    payment_option: Optional[str] = Field(
        None, pattern="^(no_upfront|partial_upfront|all_upfront)$")


class CostEstimateResponse(BaseModel):
    """Response for cost estimation."""

    id: str
    cloud_provider: CloudProvider
    region: str
    pricing_model: str
    resource_spec: Dict[str, Any]

    # Costs
    hourly_cost: Decimal
    daily_cost: Decimal
    monthly_cost: Decimal
    yearly_cost: Decimal
    currency: str = "USD"

    # Breakdown
    compute_cost: Decimal
    storage_cost: Decimal
    network_cost: Decimal
    other_costs: Decimal

    # Comparison
    on_demand_hourly: Decimal
    savings_with_pricing_model: Optional[Decimal] = None
    savings_percentage: Optional[float] = None

    # Alternatives
    alternatives: Optional[List[Dict[str, Any]]] = None

    # Timestamps
    created_at: datetime
    expires_at: Optional[datetime] = None


# ============ Recommendation Schemas ============

class RecommendationBase(BaseModel):
    """Base schema for recommendations."""

    cloud_provider: CloudProvider
    resource_type: Optional[ResourceType] = None
    resource_id: Optional[str] = None
    resource_name: Optional[str] = None
    recommendation_type: RecommendationType
    title: str
    description: str
    current_cost: Optional[Decimal] = None
    estimated_savings: Optional[Decimal] = None
    priority: RecommendationPriority = RecommendationPriority.MEDIUM


class RecommendationCreate(RecommendationBase):
    """Schema for creating a recommendation."""

    action_steps: Optional[List[str]] = None
    risks: Optional[List[str]] = None
    prerequisites: Optional[List[str]] = None
    utilization_data: Optional[Dict[str, Any]] = None
    right_sizing_data: Optional[Dict[str, Any]] = None
    source: Optional[str] = None
    confidence_score: Optional[float] = Field(None, ge=0, le=100)


class RecommendationResponse(RecommendationBase):
    """Schema for recommendation response."""

    id: str
    cluster_id: Optional[str] = None
    status: str
    action_steps: Optional[List[str]] = None
    risks: Optional[List[str]] = None
    utilization_data: Optional[Dict[str, Any]] = None
    right_sizing_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    reviewed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RecommendationUpdate(BaseModel):
    """Schema for updating a recommendation status."""

    status: str = Field(..., pattern="^(approved|dismissed|implemented)$")
    notes: Optional[str] = None


class UtilizationMetrics(BaseModel):
    """Resource utilization metrics."""

    cpu_utilization_percent: float = Field(..., ge=0, le=100)
    memory_utilization_percent: float = Field(..., ge=0, le=100)
    network_in_percent: Optional[float] = Field(None, ge=0, le=100)
    network_out_percent: Optional[float] = Field(None, ge=0, le=100)
    disk_io_percent: Optional[float] = Field(None, ge=0, le=100)
    request_rate: Optional[float] = None
    latency_p99_ms: Optional[float] = None


# ============ Dashboard Schemas ============

class CostDashboardOverview(BaseModel):
    """Cost dashboard overview."""

    total_cost: Decimal
    currency: str = "USD"
    period: str
    period_start: datetime
    period_end: datetime

    # Trends
    previous_period_cost: Decimal
    cost_change_percent: float

    # By provider
    cost_by_provider: Dict[str, Decimal]

    # By cluster
    cost_by_cluster: Dict[str, Decimal]

    # Top resources
    top_resources: List[Dict[str, Any]]

    # Budget status
    active_budgets: int
    budgets_near_limit: int
    budgets_exceeded: int


class TimeSeriesDataPoint(BaseModel):
    """Single data point for time series charts."""

    timestamp: datetime
    value: float
    label: Optional[str] = None


class TimeSeriesData(BaseModel):
    """Time series data for charts."""

    metric: str
    provider: Optional[CloudProvider] = None
    unit: str
    data_points: List[TimeSeriesDataPoint]


# ============ Health Check Schemas ============

class HealthCheckResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    database_status: str
    cache_status: str
    collector_status: Dict[str, str]
    timestamp: datetime
