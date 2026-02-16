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


# ============ Cost Tag Schemas ============

class CostTagBase(BaseModel):
    """Base schema for cost tags."""

    cloud_provider: CloudProvider
    cluster_id: Optional[str] = None
    account_id: Optional[str] = None
    team: Optional[str] = None
    project: Optional[str] = None
    environment: Optional[str] = None
    service: Optional[str] = None
    namespace: Optional[str] = None
    resource_id: Optional[str] = None
    resource_type: Optional[str] = None
    custom_tags: Optional[Dict[str, str]] = None


class CostTagCreate(CostTagBase):
    """Schema for creating a cost tag."""

    period_start: datetime
    period_end: datetime


class CostTagResponse(CostTagBase):
    """Schema for cost tag response."""

    id: str
    cost_amount: Decimal
    period_start: datetime
    period_end: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CostTagAggregation(BaseModel):
    """Aggregated cost by tag dimension."""

    team: Optional[str] = None
    project: Optional[str] = None
    environment: Optional[str] = None
    service: Optional[str] = None
    namespace: Optional[str] = None
    total_cost: Decimal
    resource_count: int = 0
    percentage: float = 0.0


# ============ Cost Anomaly Schemas ============

class AnomalyType(str, Enum):
    """Types of cost anomalies."""

    SPENDING_SPIKE = "spending_spike"
    NEW_EXPENSIVE_RESOURCE = "new_expensive_resource"
    IDLE_RESOURCE = "idle_resource"
    DATA_TRANSFER_SPIKE = "data_transfer_spike"
    UNUSED_VOLUME = "unused_volume"
    PRICE_CHANGE = "price_change"
    ANOMALY_DETECTED = "anomaly_detected"


class AnomalySeverity(str, Enum):
    """Severity levels for anomalies."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AnomalyStatus(str, Enum):
    """Status of anomaly."""

    ACTIVE = "active"
    INVESTIGATED = "investigated"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class CostAnomalyBase(BaseModel):
    """Base schema for cost anomalies."""

    cloud_provider: CloudProvider
    cluster_id: Optional[str] = None
    anomaly_type: AnomalyType
    severity: AnomalySeverity = AnomalySeverity.WARNING
    title: str
    description: str
    baseline_value: Optional[Decimal] = None
    current_value: Optional[Decimal] = None
    expected_value: Optional[Decimal] = None
    change_percent: Optional[float] = None
    resource_id: Optional[str] = None
    resource_name: Optional[str] = None
    resource_type: Optional[str] = None
    service_name: Optional[str] = None
    cost_impact: Optional[Decimal] = None
    currency: str = "USD"
    detection_method: Optional[str] = None
    confidence_score: Optional[float] = None


class CostAnomalyCreate(CostAnomalyBase):
    """Schema for creating an anomaly."""

    metadata: Optional[Dict[str, Any]] = None


class CostAnomalyResponse(CostAnomalyBase):
    """Schema for anomaly response."""

    id: str
    status: AnomalyStatus
    detected_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class AnomalyDetectionRequest(BaseModel):
    """Request schema for anomaly detection."""

    start_date: datetime
    end_date: datetime
    cloud_provider: Optional[CloudProvider] = None
    cluster_id: Optional[str] = None
    sensitivity: float = Field(
        default=2.0, ge=1.0, le=4.0)  # Z-score threshold


class AnomalyDetectionResult(BaseModel):
    """Result of anomaly detection run."""

    anomalies_detected: int
    critical_count: int
    warning_count: int
    info_count: int
    total_cost_impact: Decimal
    detection_run_time: datetime


# ============ Chargeback Report Schemas ============

class ChargebackReportBase(BaseModel):
    """Base schema for chargeback reports."""

    team: str
    project: Optional[str] = None
    environment: Optional[str] = None
    cloud_provider: Optional[CloudProvider] = None
    period_start: datetime
    period_end: datetime


class ChargebackReportCreate(ChargebackReportBase):
    """Schema for generating chargeback report."""

    pass


class ChargebackReportResponse(ChargebackReportBase):
    """Schema for chargeback report response."""

    id: str
    total_cost: Decimal
    compute_cost: Optional[Decimal] = None
    storage_cost: Optional[Decimal] = None
    network_cost: Optional[Decimal] = None
    other_cost: Optional[Decimal] = None
    currency: str = "USD"
    resource_count: int = 0
    active_instances: int = 0
    storage_gb: Optional[Decimal] = None
    budget_amount: Optional[Decimal] = None
    budget_variance: Optional[Decimal] = None
    budget_variance_percent: Optional[float] = None
    status: str
    generated_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class ChargebackSummary(BaseModel):
    """Summary of chargeback by team."""

    team: str
    total_cost: Decimal
    resource_count: int
    percentage_of_total: float
    trend_percent: Optional[float] = None


# ============ Cost Forecast Schemas ============

class CostForecastRequest(BaseModel):
    """Request schema for cost forecast."""

    forecast_start: datetime
    forecast_end: datetime
    cloud_provider: Optional[CloudProvider] = None
    cluster_id: Optional[str] = None
    team: Optional[str] = None
    project: Optional[str] = None
    budget_amount: Optional[Decimal] = None


class CostForecastResponse(BaseModel):
    """Schema for cost forecast response."""

    id: str
    forecast_start: datetime
    forecast_end: datetime
    base_period_start: datetime
    base_period_end: datetime
    cloud_provider: Optional[CloudProvider] = None
    cluster_id: Optional[str] = None
    team: Optional[str] = None
    project: Optional[str] = None
    predicted_cost: Decimal
    confidence_low: Optional[Decimal] = None
    confidence_high: Optional[Decimal] = None
    confidence_level: Optional[float] = None
    current_cost: Optional[Decimal] = None
    previous_period_cost: Optional[Decimal] = None
    trend_percent: Optional[float] = None
    seasonality_detected: bool = False
    budget_amount: Optional[Decimal] = None
    budget_variance: Optional[Decimal] = None
    budget_exceed_date: Optional[datetime] = None
    currency: str = "USD"
    forecast_method: str
    mape: Optional[float] = None
    generated_at: datetime
    status: str

    class Config:
        from_attributes = True


class ForecastSummary(BaseModel):
    """Summary of forecast data."""

    total_predicted_cost: Decimal
    currency: str = "USD"
    forecast_period_start: datetime
    forecast_period_end: datetime
    overall_trend_percent: float
    budget_status: str  # on_track, at_risk, exceeded
    potential_budget_variance: Optional[Decimal] = None
    budget_exceed_date: Optional[datetime] = None
