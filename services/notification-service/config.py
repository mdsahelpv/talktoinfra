"""Notification Service Configuration."""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    service_port: int = Field(default=8013, description="Notification service port")
    service_host: str = Field(default="0.0.0.0", description="Notification service host")

    # Database
    database_url: str = Field(
        default="postgresql://opsai:changeme@postgres:5432/opsai_notifications",
        description="PostgreSQL database URL",
    )
    database_url_async: str = Field(
        default="postgresql+asyncpg://opsai:changeme@postgres:5432/opsai_notifications",
        description="PostgreSQL async database URL",
    )

    # Redis
    redis_url: str = Field(
        default="redis://redis:6379/7",
        description="Redis URL",
    )

    # NATS
    nats_url: str = Field(
        default="nats://nats:4222",
        description="NATS server URL",
    )

    # Email Settings
    smtp_host: Optional[str] = Field(default=None, description="SMTP host")
    smtp_port: int = Field(default=587, description="SMTP port")
    smtp_user: Optional[str] = Field(default=None, description="SMTP user")
    smtp_password: Optional[str] = Field(default=None, description="SMTP password")
    smtp_from_email: Optional[str] = Field(default=None, description="From email address")
    smtp_from_name: str = Field(default="TalkAI", description="From email name")

    # Slack Settings
    slack_bot_token: Optional[str] = Field(default=None, description="Slack bot token")
    slack_signing_secret: Optional[str] = Field(default=None, description="Slack signing secret")
    slack_default_channel: Optional[str] = Field(default=None, description="Default Slack channel")

    # Teams Settings
    teams_webhook_url: Optional[str] = Field(default=None, description="Microsoft Teams webhook URL")

    # PagerDuty Settings
    pagerduty_api_key: Optional[str] = Field(default=None, description="PagerDuty API key")
    pagerduty_service_id: Optional[str] = Field(default=None, description="PagerDuty service ID")

    # Webhook Settings
    webhook_timeout: int = Field(default=30, description="Webhook timeout in seconds")
    webhook_retry_count: int = Field(default=3, description="Webhook retry count")

    # Rate Limiting
    rate_limit_per_minute: int = Field(
        default=60, description="API rate limit per minute"
    )

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:3000"],
        description="Allowed CORS origins",
    )

    class Config:
        env_file = ".env"
        env_prefix = "NOTIFICATION_SERVICE_"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
