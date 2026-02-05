"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# Enums
class AlertSeverity(str, Enum):
    """Alert severity levels."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AlertStatus(str, Enum):
    """Alert status for lifecycle management."""

    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    SUPPRESSED = "SUPPRESSED"


class ComparisonOperator(str, Enum):
    """Operators for alert rule comparisons."""

    GT = ">"
    LT = "<"
    GTE = ">="
    LTE = "<="
    EQ = "=="
    NEQ = "!="


class ConditionType(str, Enum):
    """Type of alert condition."""

    THRESHOLD = "THRESHOLD"
    RATE_OF_CHANGE = "RATE_OF_CHANGE"
    ANOMALY = "ANOMALY"
    STATUS = "STATUS"


# Alert Rule Schemas
class AlertRuleBase(BaseModel):
    """Base schema for alert rules."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    enabled: bool = True

    condition_type: ConditionType = ConditionType.THRESHOLD
    metric_name: str = Field(..., min_length=1, max_length=255)
    comparison_operator: ComparisonOperator = ComparisonOperator.GT
    threshold_value: Optional[float] = None
    duration_seconds: int = Field(default=300, ge=1)

    severity: AlertSeverity = AlertSeverity.WARNING
    labels: Dict[str, str] = Field(default_factory=dict)
    annotations: Dict[str, str] = Field(default_factory=dict)

    evaluation_interval_seconds: int = Field(default=30, ge=1)
    group_name: Optional[str] = None
    notify_channels: List[str] = Field(default_factory=list)


class AlertRuleCreate(AlertRuleBase):
    """Schema for creating an alert rule."""

    pass


class AlertRuleUpdate(BaseModel):
    """Schema for updating an alert rule."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    enabled: Optional[bool] = None

    condition_type: Optional[ConditionType] = None
    metric_name: Optional[str] = None
    comparison_operator: Optional[ComparisonOperator] = None
    threshold_value: Optional[float] = None
    duration_seconds: Optional[int] = Field(None, ge=1)

    severity: Optional[AlertSeverity] = None
    labels: Optional[Dict[str, str]] = None
    annotations: Optional[Dict[str, str]] = None

    evaluation_interval_seconds: Optional[int] = Field(None, ge=1)
    group_name: Optional[str] = None
    notify_channels: Optional[List[str]] = None


class AlertRuleResponse(AlertRuleBase):
    """Schema for alert rule response."""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Alert Schemas
class AlertBase(BaseModel):
    """Base schema for alerts."""

    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    severity: AlertSeverity
    status: AlertStatus

    labels: Dict[str, str] = Field(default_factory=dict)
    annotations: Dict[str, str] = Field(default_factory=dict)

    current_value: Optional[float] = None
    threshold_value: Optional[float] = None


class AlertResponse(AlertBase):
    """Schema for alert response."""

    id: int
    fingerprint: str
    rule_id: int

    starts_at: datetime
    ends_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_by: Optional[str] = None
    acknowledgment_notes: Optional[str] = None

    fire_count: int
    group_name: Optional[str] = None
    root_cause_alert_id: Optional[int] = None

    created_at: datetime
    updated_at: datetime

    # Related data
    rule: Optional[AlertRuleResponse] = None

    class Config:
        from_attributes = True


class AlertListResponse(BaseModel):
    """Schema for paginated alert list."""

    alerts: List[AlertResponse]
    total: int
    page: int
    page_size: int


class AlertAcknowledge(BaseModel):
    """Schema for acknowledging an alert."""

    acknowledged_by: str = Field(..., min_length=1)
    notes: Optional[str] = None


class AlertResolve(BaseModel):
    """Schema for resolving an alert."""

    resolved_by: str = Field(..., min_length=1)
    notes: Optional[str] = None


class AlertFilter(BaseModel):
    """Schema for filtering alerts."""

    status: Optional[List[AlertStatus]] = None
    severity: Optional[List[AlertSeverity]] = None
    rule_id: Optional[int] = None
    group_name: Optional[str] = None
    fingerprint: Optional[str] = None

    starts_after: Optional[datetime] = None
    starts_before: Optional[datetime] = None

    labels: Optional[Dict[str, str]] = None


# Metric Schemas
class MetricDataPoint(BaseModel):
    """Single metric data point."""

    timestamp: datetime
    value: float
    labels: Dict[str, str] = Field(default_factory=dict)


class MetricQuery(BaseModel):
    """Schema for querying metrics."""

    name: str
    labels: Optional[Dict[str, str]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    step_seconds: Optional[int] = None


class MetricResponse(BaseModel):
    """Schema for metric response."""

    metric_name: str
    metric_type: Optional[str] = None
    data_points: List[MetricDataPoint]
    source: Optional[str] = None


class MetricListResponse(BaseModel):
    """Schema for list of available metrics."""

    metrics: List[str]
    total: int


class CustomMetricSubmit(BaseModel):
    """Schema for submitting a custom metric."""

    name: str = Field(..., min_length=1, max_length=255)
    value: float
    metric_type: Optional[str] = None
    labels: Dict[str, str] = Field(default_factory=dict)
    source_service: Optional[str] = None
    source_instance: Optional[str] = None
    timestamp: Optional[datetime] = None


# Health Check Schemas
class ServiceHealthStatus(str, Enum):
    """Service health status values."""

    HEALTHY = "HEALTHY"
    UNHEALTHY = "UNHEALTHY"
    UNKNOWN = "UNKNOWN"
    ERROR = "ERROR"


class ComponentHealth(BaseModel):
    """Health of an individual component."""

    name: str
    status: ServiceHealthStatus
    message: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class ServiceHealthResponse(BaseModel):
    """Response for a single service health check."""

    service_name: str
    service_url: str
    status: ServiceHealthStatus
    response_time_ms: Optional[float] = None
    status_code: Optional[int] = None

    components: List[ComponentHealth] = Field(default_factory=list)
    error_message: Optional[str] = None
    error_type: Optional[str] = None

    checked_at: datetime
    next_check_at: Optional[datetime] = None


class HealthOverviewResponse(BaseModel):
    """Overall health overview."""

    overall_status: ServiceHealthStatus
    total_services: int
    healthy_services: int
    unhealthy_services: int
    unknown_services: int

    services: List[ServiceHealthResponse]
    last_updated: datetime


# Notification Channel Schemas
class NotificationChannelBase(BaseModel):
    """Base schema for notification channels."""

    name: str = Field(..., min_length=1, max_length=255)
    channel_type: str = Field(..., min_length=1, max_length=50)
    enabled: bool = True


class NotificationChannelCreate(NotificationChannelBase):
    """Schema for creating a notification channel."""

    config: Dict[str, Any] = Field(default_factory=dict)


class NotificationChannelUpdate(BaseModel):
    """Schema for updating a notification channel."""

    name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None


class NotificationChannelResponse(NotificationChannelBase):
    """Schema for notification channel response."""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Escalation Policy Schemas
class EscalationLevel(BaseModel):
    """Single escalation level."""

    level: int = Field(..., ge=1)
    delay_seconds: int = Field(default=300)
    notify_channels: List[str] = Field(default_factory=list)
    notify_users: List[str] = Field(default_factory=list)


class EscalationPolicyBase(BaseModel):
    """Base schema for escalation policies."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    escalation_levels: List[EscalationLevel] = Field(default_factory=list)
    repeat_interval_seconds: Optional[int] = None


class EscalationPolicyCreate(EscalationPolicyBase):
    """Schema for creating an escalation policy."""

    pass


class EscalationPolicyUpdate(BaseModel):
    """Schema for updating an escalation policy."""

    name: Optional[str] = None
    description: Optional[str] = None
    escalation_levels: Optional[List[EscalationLevel]] = None
    repeat_interval_seconds: Optional[int] = None


class EscalationPolicyResponse(EscalationPolicyBase):
    """Schema for escalation policy response."""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Dashboard Schemas
class AlertStatistics(BaseModel):
    """Alert statistics for dashboard."""

    total_alerts: int
    active_alerts: int
    acknowledged_alerts: int
    resolved_alerts: int

    by_severity: Dict[str, int]
    by_status: Dict[str, int]
    by_group: Dict[str, int]

    mttr_minutes: Optional[float] = None  # Mean time to resolve
    mtta_minutes: Optional[float] = None  # Mean time to acknowledge


class DashboardResponse(BaseModel):
    """Dashboard overview response."""

    health_overview: HealthOverviewResponse
    alert_statistics: AlertStatistics

    recent_alerts: List[AlertResponse] = Field(default_factory=list)
    top_metric_names: List[str] = Field(default_factory=list)

    last_updated: datetime
