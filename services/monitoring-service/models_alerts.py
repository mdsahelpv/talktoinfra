"""Alert Rule models for the monitoring service."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.models import Base


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

    GT = ">"  # Greater than
    LT = "<"  # Less than
    GTE = ">="  # Greater than or equal
    LTE = "<="  # Less than or equal
    EQ = "=="  # Equal
    NEQ = "!="  # Not equal


class ConditionType(str, Enum):
    """Type of alert condition."""

    THRESHOLD = "THRESHOLD"  # Static threshold
    RATE_OF_CHANGE = "RATE_OF_CHANGE"  # Rate/spike detection
    ANOMALY = "ANOMALY"  # Anomaly detection based
    STATUS = "STATUS"  # Service status check


class AlertRule(Base):
    """Alert rule configuration model."""

    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, default=True, nullable=False)

    # Condition configuration
    condition_type = Column(
        SQLEnum(ConditionType),
        nullable=False,
        default=ConditionType.THRESHOLD
    )
    metric_name = Column(String(255), nullable=False)
    comparison_operator = Column(
        SQLEnum(ComparisonOperator),
        nullable=False,
        default=ComparisonOperator.GT
    )
    threshold_value = Column(Float, nullable=True)
    duration_seconds = Column(
        Integer,
        default=300,
        nullable=False,
        description="How long condition must be true before triggering"
    )

    # Severity and labels
    severity = Column(
        SQLEnum(AlertSeverity),
        nullable=False,
        default=AlertSeverity.WARNING
    )
    labels = Column(Text, nullable=True, default="{}")  # JSON string
    annotations = Column(Text, nullable=True, default="{}")  # JSON string

    # Evaluation settings
    evaluation_interval_seconds = Column(
        Integer,
        default=30,
        nullable=False
    )
    group_name = Column(String(255), nullable=True)

    # Notification settings
    notify_channels = Column(Text, nullable=True, default="[]")  # JSON string
    escalation_policy_id = Column(
        Integer,
        ForeignKey("escalation_policies.id"),
        nullable=True
    )

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    # Relationships
    alerts = relationship("Alert", back_populates="rule")
    escalation_policy = relationship(
        "EscalationPolicy", back_populates="rules")

    def __repr__(self) -> str:
        return f"<AlertRule(id={self.id}, name='{self.name}', severity={self.severity})>"

    @property
    def labels_dict(self) -> Dict[str, str]:
        """Parse labels JSON to dict."""
        import json
        if self.labels:
            return json.loads(self.labels)
        return {}

    @property
    def annotations_dict(self) -> Dict[str, str]:
        """Parse annotations JSON to dict."""
        import json
        if self.annotations:
            return json.loads(self.annotations)
        return {}

    @property
    def notify_channels_list(self) -> List[str]:
        """Parse notification channels JSON to list."""
        import json
        if self.notify_channels:
            return json.loads(self.notify_channels)
        return []


class EscalationPolicy(Base):
    """Escalation policy for alert notifications."""

    __tablename__ = "escalation_policies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)

    # Escalation levels stored as JSON
    escalation_levels = Column(Text, nullable=False, default="[]")

    # Repeat interval for escalation
    repeat_interval_seconds = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    # Relationships
    rules = relationship("AlertRule", back_populates="escalation_policy")

    def __repr__(self) -> str:
        return f"<EscalationPolicy(id={self.id}, name='{self.name}')>"

    @property
    def levels(self) -> List[Dict[str, Any]]:
        """Parse escalation levels JSON to list."""
        import json
        if self.escalation_levels:
            return json.loads(self.escalation_levels)
        return []


class NotificationChannel(Base):
    """Notification channel configuration."""

    __tablename__ = "notification_channels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    # email, slack, pagerduty
    channel_type = Column(String(50), nullable=False)

    # Channel configuration stored as JSON
    config = Column(Text, nullable=False, default="{}")

    enabled = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<NotificationChannel(id={self.id}, name='{self.name}', type='{self.channel_type}')>"

    @property
    def config_dict(self) -> Dict[str, Any]:
        """Parse config JSON to dict."""
        import json
        if self.config:
            return json.loads(self.config)
        return {}
