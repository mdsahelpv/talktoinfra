"""Cost Service Configuration.

Pydantic settings for cost tracking, cloud provider APIs,
and optimization settings.
"""

from functools import lru_cache
from typing import Any, Dict, List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings for the Cost Management Service."""

    # Service Configuration
    service_name: str = Field(default="cost-service",
                              description="Service name")
    service_host: str = Field(default="0.0.0.0", description="Service host")
    service_port: int = Field(default=8010, description="Service port")
    debug: bool = Field(default=False, description="Debug mode")

    # Database Configuration
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/talktoinfra",
        description="PostgreSQL connection URL"
    )
    sync_database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/talktoinfra",
        description="Synchronous PostgreSQL connection URL"
    )

    # Redis Configuration (for caching and sessions)
    redis_url: str = Field(
        default="redis://localhost:6379/4",
        description="Redis URL for caching"
    )

    # AWS Configuration
    aws_cost_explorer_enabled: bool = Field(
        default=False,
        description="Enable AWS Cost Explorer integration"
    )
    aws_region: str = Field(default="us-east-1", description="AWS region")
    aws_access_key_id: Optional[str] = Field(
        default=None, description="AWS access key")
    aws_secret_access_key: Optional[str] = Field(
        default=None, description="AWS secret key")

    # Azure Configuration
    azure_cost_management_enabled: bool = Field(
        default=False,
        description="Enable Azure Cost Management integration"
    )
    azure_tenant_id: Optional[str] = Field(
        default=None, description="Azure tenant ID")
    azure_client_id: Optional[str] = Field(
        default=None, description="Azure client ID")
    azure_client_secret: Optional[str] = Field(
        default=None, description="Azure client secret")
    azure_subscription_id: Optional[str] = Field(
        default=None,
        description="Azure subscription ID"
    )

    # GCP Configuration
    gcp_billing_enabled: bool = Field(
        default=False,
        description="Enable GCP Billing integration"
    )
    gcp_project_id: Optional[str] = Field(
        default=None, description="GCP project ID")
    gcp_credentials_file: Optional[str] = Field(
        default=None,
        description="GCP service account credentials file"
    )

    # Kubernetes Cost Configuration
    kubecost_enabled: bool = Field(
        default=False,
        description="Enable Kubecost integration"
    )
    kubecost_url: Optional[str] = Field(
        default=None,
        description="Kubecost API URL"
    )
    kubecost_api_key: Optional[str] = Field(
        default=None, description="Kubecost API key")

    # Cost Estimation Defaults
    default_currency: str = Field(
        default="USD", description="Default currency")
    hourly_to_monthly_multiplier: float = Field(
        default=730.0,
        description="Hours per month for cost estimation (730 = 24*30.42)"
    )

    # Optimization Settings
    idle_threshold_percent: float = Field(
        default=20.0,
        description="CPU/Memory threshold below which resources are considered idle"
    )
    right_sizing_threshold_percent: float = Field(
        default=40.0,
        description="Utilization threshold for right-sizing recommendations"
    )
    spot_recommendation_threshold_percent: float = Field(
        default=70.0,
        description="Stability threshold for spot instance recommendations"
    )

    # Budget Settings
    default_budget_alert_threshold_percent: float = Field(
        default=80.0,
        description="Default percentage threshold for budget alerts"
    )

    # API Keys (optional integrations)
    openai_api_key: Optional[str] = Field(
        default=None, description="OpenAI API key")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Type aliases for better readability
CostData = Dict[str, Any]
CostBreakdown = Dict[str, float]
OptimizationRecommendation = Dict[str, Any]
BudgetAlert = Dict[str, Any]
