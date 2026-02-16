"""Notification Service Database Models."""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class NotificationChannel(str, enum.Enum):
    """Notification channel types."""

    EMAIL = "email"
    SLACK = "slack"
    TEAMS = "teams"
    PAGERDUTY = "pagerduty"
    WEBHOOK = "webhook"
    IN_APP = "in_app"


class NotificationPriority(str, enum.Enum):
    """Notification priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationStatus(str, enum.Enum):
    """Notification delivery status."""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    DELIVERED = "delivered"


class NotificationTemplate(Base):
    """Notification template model."""

    __tablename__ = "notification_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Template content
    subject: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    body_template: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    html_template: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Channel-specific templates
    slack_template: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    teams_template: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Variables
    variables: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    __table_args__ = (Index("idx_templates_name", "name"),)


class NotificationPreference(Base):
    """User notification preferences."""

    __tablename__ = "notification_preferences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # Channel preferences
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    slack_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    teams_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    pagerduty_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Notification type preferences
    alerts_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    approvals_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    workflow_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    digest_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Contact info
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    slack_user_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    teams_user_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pagerduty_user_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Digest settings
    digest_frequency: Mapped[str] = mapped_column(
        String(20), default="daily", nullable=False
    )  # hourly, daily, weekly

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        Index("idx_preferences_user_id", "user_id"),
        UniqueConstraint("user_id", name="uq_preferences_user"),
    )


class UniqueConstraint:
    """SQLAlchemy unique constraint."""

    def __init__(self, *columns, name: str = None):
        self.columns = columns
        self.name = name


class Notification(Base):
    """Notification model."""

    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # Notification content
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel), nullable=False
    )
    priority: Mapped[NotificationPriority] = mapped_column(
        Enum(NotificationPriority), default=NotificationPriority.MEDIUM, nullable=False
    )

    # Status
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus), default=NotificationStatus.PENDING, nullable=False
    )

    # Metadata
    metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    action_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Delivery info
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        Index("idx_notifications_user_id", "user_id"),
        Index("idx_notifications_status", "status"),
        Index("idx_notifications_created_at", "created_at"),
    )


class WebhookConfig(Base):
    """Webhook configuration for outgoing notifications."""

    __tablename__ = "webhook_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    method: Mapped[str] = mapped_column(String(10), default="POST", nullable=False)

    # Authentication
    auth_type: Mapped[str] = mapped_column(
        String(20), default="none", nullable=False
    )  # none, basic, bearer, hmac
    auth_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Headers
    headers: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Retry settings
    retry_count: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    retry_interval: Mapped[int] = mapped_column(Integer, default=60, nullable=False)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    __table_args__ = (Index("idx_webhook_configs_name", "name"),)


class NotificationLog(Base):
    """Notification delivery log."""

    __tablename__ = "notification_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    notification_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )

    # Log details
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timing
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        Index("idx_logs_notification_id", "notification_id"),
        Index("idx_logs_sent_at", "sent_at"),
    )
