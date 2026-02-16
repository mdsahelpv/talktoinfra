"""
Monitoring Service Configuration.

Pydantic settings for the monitoring service with environment variable support.
"""
from functools import lru_cache
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DatabaseSettings(BaseModel):
    """Database configuration for monitoring service."""

    url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/monitoring",
        description="PostgreSQL connection URL"
    )
    pool_size: int = Field(default=10, description="Connection pool size")
    max_overflow: int = Field(default=20, description="Max pool overflow")
    pool_timeout: int = Field(
        default=30, description="Pool timeout in seconds")


class RedisSettings(BaseModel):
    """Redis configuration for caching and pub/sub."""

    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, description="Redis port")
    db: int = Field(default=1, description="Redis database number")
    password: Optional[str] = Field(default=None, description="Redis password")


class CelerySettings(BaseModel):
    """Celery configuration for background tasks."""

    broker_url: str = Field(
        default="redis://localhost:6379/2",
        description="Celery broker URL"
    )
    result_backend: str = Field(
        default="redis://localhost:6379/3",
        description="Celery result backend"
    )
    task_serializer: str = Field(
        default="json", description="Task serialization format")
    result_serializer: str = Field(
        default="json", description="Result serialization")
    accept_content: List[str] = Field(
        default_factory=lambda: ["json"],
        description="Accepted content types"
    )
    timezone: str = Field(
        default="UTC", description="Timezone for scheduled tasks")
    enable_utc: bool = Field(default=True, description="Enable UTC")


class AlertNotificationSettings(BaseModel):
    """Alert notification channel configuration."""

    email_enabled: bool = Field(
        default=False, description="Enable email notifications")
    smtp_host: str = Field(default="smtp.example.com", description="SMTP host")
    smtp_port: int = Field(default=587, description="SMTP port")
    smtp_user: Optional[str] = Field(default=None, description="SMTP user")
    smtp_password: Optional[str] = Field(
        default=None, description="SMTP password")
    from_address: str = Field(
        default="alerts@example.com",
        description="From email address"
    )

    slack_enabled: bool = Field(
        default=False, description="Enable Slack notifications")
    slack_webhook_url: Optional[str] = Field(
        default=None,
        description="Slack webhook URL"
    )
    slack_channel: str = Field(default="#alerts", description="Slack channel")

    pagerduty_enabled: bool = Field(
        default=False,
        description="Enable PagerDuty integration"
    )
    pagerduty_api_key: Optional[str] = Field(
        default=None,
        description="PagerDuty API key"
    )
    pagerduty_service_id: Optional[str] = Field(
        default=None,
        description="PagerDuty service ID"
    )


class MetricCollectionSettings(BaseModel):
    """Metric collection configuration."""

    collection_interval_seconds: int = Field(
        default=30,
        description="Interval between metric collections"
    )
    k8s_enabled: bool = Field(
        default=True, description="Enable K8s metrics collection")
    postgres_enabled: bool = Field(
        default=True,
        description="Enable PostgreSQL metrics"
    )
    redis_enabled: bool = Field(
        default=True, description="Enable Redis metrics")
    custom_metrics_enabled: bool = Field(
        default=True,
        description="Enable custom metric collection"
    )
    metric_retention_days: int = Field(
        default=90,
        description="How long to retain metrics"
    )


class AnomalyDetectionSettings(BaseModel):
    """Anomaly detection configuration."""

    enabled: bool = Field(default=True, description="Enable anomaly detection")
    baseline_window_hours: int = Field(
        default=168,  # 7 days
        description="Window for learning baseline"
    )
    sensitivity: float = Field(
        default=2.0,
        description="Standard deviations for anomaly threshold"
    )
    seasonal_patterns: bool = Field(
        default=True,
        description="Account for daily/hourly patterns"
    )
    min_data_points: int = Field(
        default=100,
        description="Minimum data points for baseline"
    )


class Settings(BaseModel):
    """Main settings class for monitoring service."""

    service_name: str = Field(
        default="monitoring-service", description="Service name")
    service_host: str = Field(default="0.0.0.0", description="Service host")
    service_port: int = Field(default=8009, description="Service port")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Log level")

    # Database configuration
    database: DatabaseSettings = Field(
        default_factory=DatabaseSettings,
        description="Database settings"
    )

    # Redis configuration
    redis: RedisSettings = Field(
        default_factory=RedisSettings,
        description="Redis settings"
    )

    # Celery configuration
    celery: CelerySettings = Field(
        default_factory=CelerySettings,
        description="Celery settings"
    )

    # Alert notifications
    notifications: AlertNotificationSettings = Field(
        default_factory=AlertNotificationSettings,
        description="Notification settings"
    )

    # Metric collection
    metrics: MetricCollectionSettings = Field(
        default_factory=MetricCollectionSettings,
        description="Metric collection settings"
    )

    # Anomaly detection
    anomaly_detection: AnomalyDetectionSettings = Field(
        default_factory=AnomalyDetectionSettings,
        description="Anomaly detection settings"
    )

    # CORS settings
    cors_origins: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins"
    )

    # Service endpoints to monitor
    monitored_services: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:8001",  # API Gateway
            "http://localhost:8002",  # Agent Service
            "http://localhost:8003",  # Discovery Service
            "http://localhost:8004",  # Action Engine
            "http://localhost:8005",  # Audit Service
            "http://localhost:8006",  # Policy Engine
            "http://localhost:8007",  # AI Router
            "http://localhost:8008",  # Ingestion Service
            "http://localhost:8011",  # Onboarding Service
        ],
        description="List of services to monitor"
    )

    # Cluster configurations for K8s monitoring
    k8s_clusters: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Kubernetes cluster configurations"
    )

    # Action Engine URL for self-healing
    action_engine_url: str = Field(
        default="http://localhost:8010",
        description="Action Engine service URL for executing fixes"
    )

    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience function for accessing settings
def get_database_url() -> str:
    """Get database URL from settings."""
    return get_settings().database.url


def get_redis_url() -> str:
    """Get Redis URL from settings."""
    settings = get_settings()
    if settings.redis.password:
        return f"redis://:{settings.redis.password}@{settings.redis.host}:{settings.redis.port}/{settings.redis.db}"
    return f"redis://{settings.redis.host}:{settings.redis.port}/{settings.redis.db}"
