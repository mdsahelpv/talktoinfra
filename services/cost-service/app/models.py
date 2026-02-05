"""Cost Service Models.

SQLAlchemy models for cost tracking, budgets, and optimization recommendations.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    Text,
    ForeignKey,
    Index,
    JSON,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, NUMERIC
import uuid

from app.database import Base
from app.schemas import (
    CloudProvider,
    ResourceType,
    RecommendationPriority,
    RecommendationType,
)


class CostRecord(Base):
    """Database model for cost records."""

    __tablename__ = "cost_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cluster_id = Column(String(255), nullable=True, index=True)
    cloud_provider = Column(SQLEnum(CloudProvider), nullable=False)
    account_id = Column(String(255), nullable=True)
    account_name = Column(String(255), nullable=True)
    region = Column(String(50), nullable=True, index=True)
    availability_zone = Column(String(100), nullable=True)
    service_name = Column(String(255), nullable=True, index=True)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(String(255), nullable=True, index=True)
    resource_name = Column(String(255), nullable=True)

    # Cost data
    cost_amount = Column(NUMERIC(precision=12, scale=6), nullable=False)
    currency = Column(String(3), default="USD")
    usage_quantity = Column(NUMERIC(precision=12, scale=6), nullable=True)
    usage_unit = Column(String(50), nullable=True)
    pricing_unit = Column(String(50), nullable=True)

    # Dimensions
    operation = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)

    # Time dimensions
    usage_start = Column(DateTime(timezone=True), nullable=False, index=True)
    usage_end = Column(DateTime(timezone=True), nullable=True)

    # Metadata
    line_item_id = Column(String(255), nullable=True)
    bill_id = Column(String(255), nullable=True)
    invoice_id = Column(String(255), nullable=True)
    payer_account_id = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True),
                        default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    budget_alerts = relationship("BudgetAlert", back_populates="cost_record")

    __table_args__ = (
        Index("idx_cost_date_provider", "usage_start", "cloud_provider"),
        Index("idx_cost_cluster_date", "cluster_id", "usage_start"),
        Index("idx_cost_resource", "resource_id", "usage_start"),
    )


class Budget(Base):
    """Database model for cost budgets."""

    __tablename__ = "budgets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    cloud_provider = Column(SQLEnum(CloudProvider), nullable=True)
    cluster_id = Column(String(255), nullable=True, index=True)
    namespace = Column(String(255), nullable=True)

    # Budget configuration
    amount = Column(NUMERIC(precision=12, scale=2), nullable=False)
    currency = Column(String(3), default="USD")
    # daily, weekly, monthly, quarterly, yearly
    period = Column(String(20), default="monthly")

    # Time range
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=True)

    # Alert thresholds (percentages)
    alert_thresholds = Column(JSON, nullable=True)  # e.g., [50, 80, 90, 100]

    # Notification settings
    notify_email = Column(JSON, nullable=True)  # List of email addresses
    notify_slack = Column(JSON, nullable=True)  # Slack webhook URLs
    # PagerDuty integration keys
    notify_pagerduty = Column(JSON, nullable=True)

    # Status
    is_active = Column(Integer, default=1)  # 1=active, 0=inactive
    current_spend = Column(NUMERIC(precision=12, scale=2), default=0)
    last_alert_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True),
                        default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    alerts = relationship("BudgetAlert", back_populates="budget")

    __table_args__ = (
        Index("idx_budget_active", "is_active", "start_date", "end_date"),
    )


class BudgetAlert(Base):
    """Database model for budget alerts."""

    __tablename__ = "budget_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    budget_id = Column(
        UUID(as_uuid=True),
        ForeignKey("budgets.id"),
        nullable=False,
        index=True
    )
    cost_record_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cost_records.id"),
        nullable=True
    )

    # Alert details
    # threshold_exceeded, budget_exceeded
    alert_type = Column(String(50), nullable=False)
    threshold_percent = Column(Float, nullable=False)
    spend_amount = Column(NUMERIC(precision=12, scale=2), nullable=False)
    budget_amount = Column(NUMERIC(precision=12, scale=2), nullable=False)
    percentage_used = Column(Float, nullable=False)

    # Status
    # active, acknowledged, resolved
    status = Column(String(20), default="active")
    # Channels that were notified
    notified_channels = Column(JSON, nullable=True)

    # Timestamps
    triggered_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    budget = relationship("Budget", back_populates="alerts")
    cost_record = relationship("CostRecord", back_populates="budget_alerts")

    __table_args__ = (
        Index("idx_budget_alert_status", "status", "triggered_at"),
    )


class Recommendation(Base):
    """Database model for cost optimization recommendations."""

    __tablename__ = "recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cluster_id = Column(String(255), nullable=True, index=True)
    cloud_provider = Column(SQLEnum(CloudProvider), nullable=False)
    resource_type = Column(SQLEnum(ResourceType), nullable=True)
    resource_id = Column(String(255), nullable=True, index=True)
    resource_name = Column(String(255), nullable=True)

    # Recommendation details
    recommendation_type = Column(
        SQLEnum(RecommendationType),
        nullable=False,
        index=True
    )
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    current_cost = Column(NUMERIC(precision=12, scale=2), nullable=True)
    estimated_savings = Column(NUMERIC(precision=12, scale=2), nullable=True)
    currency = Column(String(3), default="USD")

    # Priority and status
    priority = Column(SQLEnum(RecommendationPriority),
                      default=RecommendationPriority.MEDIUM)
    # pending, approved, dismissed, implemented
    status = Column(String(20), default="pending")

    # Implementation details
    action_steps = Column(JSON, nullable=True)
    risks = Column(JSON, nullable=True)  # List of potential risks
    prerequisites = Column(JSON, nullable=True)  # List of prerequisites

    # Metrics for decision making
    utilization_data = Column(JSON, nullable=True)  # CPU, memory, etc.
    # Current vs recommended specs
    right_sizing_data = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True),
                        default=datetime.utcnow, onupdate=datetime.utcnow)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    implemented_at = Column(DateTime(timezone=True), nullable=True)

    # Metadata
    # kubecost, aws_cost_explorer, manual
    source = Column(String(100), nullable=True)
    # 0-100 confidence in recommendation
    confidence_score = Column(Float, nullable=True)

    __table_args__ = (
        Index("idx_recommendation_status", "status", "priority"),
        Index("idx_recommendation_savings", "estimated_savings"),
    )


class CostEstimate(Base):
    """Database model for cost estimates."""

    __tablename__ = "cost_estimates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=True)
    session_id = Column(String(255), nullable=True)

    # Resource specifications
    # CPU, memory, storage, network specs
    resource_spec = Column(JSON, nullable=False)

    # Cloud provider
    cloud_provider = Column(SQLEnum(CloudProvider), nullable=False)
    region = Column(String(50), nullable=True)

    # Pricing model
    # on_demand, reserved, spot
    pricing_model = Column(String(50), default="on_demand")
    term_length = Column(String(50), nullable=True)  # 1_year, 3_year
    # no_upfront, partial_upfront, all_upfront
    payment_option = Column(String(50), nullable=True)

    # Estimates
    hourly_cost = Column(NUMERIC(precision=12, scale=6), nullable=True)
    monthly_cost = Column(NUMERIC(precision=12, scale=2), nullable=True)
    yearly_cost = Column(NUMERIC(precision=12, scale=2), nullable=True)

    # Breakdown
    cost_breakdown = Column(JSON, nullable=True)
    # Comparison with other pricing models
    comparison = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_cost_estimate_created", "created_at"),
    )


class DailyCostAggregation(Base):
    """Pre-aggregated daily cost data for efficient queries."""

    __tablename__ = "daily_cost_aggregations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    cloud_provider = Column(SQLEnum(CloudProvider), nullable=False)
    cluster_id = Column(String(255), nullable=True, index=True)
    account_id = Column(String(255), nullable=True)
    account_name = Column(String(255), nullable=True)
    region = Column(String(50), nullable=True)
    service_name = Column(String(255), nullable=True)

    # Aggregated data
    total_cost = Column(NUMERIC(precision=12, scale=6), nullable=False)
    currency = Column(String(3), default="USD")
    resource_count = Column(Integer, default=0)

    # Cost by dimension
    cost_by_resource_type = Column(JSON, nullable=True)
    cost_by_operation = Column(JSON, nullable=True)

    # Usage aggregates
    total_usage_quantity = Column(NUMERIC(precision=12, scale=6), default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True),
                        default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_daily_agg_provider_date", "cloud_provider", "date"),
        Index("idx_daily_agg_cluster_date", "cluster_id", "date"),
    )
