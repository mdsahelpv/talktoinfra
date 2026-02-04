"""Configuration for Onboarding Service."""

from functools import lru_cache
from typing import Any, Dict, List, Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings for the Onboarding Service."""

    # Service Configuration
    service_host: str = Field(default="0.0.0.0")
    service_port: int = Field(default=8011)
    debug: bool = Field(default=False)
    environment: str = Field(default="development")

    # Database Configuration
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/talktoinfra",
        description="PostgreSQL database URL",
    )

    # Credential Encryption
    encryption_key: SecretStr = Field(
        default="change-me-in-production-32-bytes!",
        description="AES-256 encryption key for credential storage",
    )

    # HashiCorp Vault (optional)
    vault_url: Optional[str] = Field(
        default=None, description="Vault server URL")
    vault_token: Optional[SecretStr] = Field(
        default=None, description="Vault token")
    vault_mount_point: str = Field(
        default="secret", description="Vault mount point")
    vault_secret_path: str = Field(
        default="talktoinfra/onboarding", description="Base path for secrets"
    )

    # Kubernetes Client Settings
    k8s_client_timeout: int = Field(
        default=30, description="K8s API timeout in seconds")
    k8s_client_retry_attempts: int = Field(
        default=3, description="Retry attempts")
    k8s_client_retry_delay: int = Field(
        default=1, description="Retry delay in seconds")

    # Cloud Provider Settings
    aws_region: str = Field(default="us-east-1")
    azure_subscription_id: Optional[str] = None
    azure_tenant_id: Optional[str] = None
    azure_client_id: Optional[str] = None
    azure_client_secret: Optional[SecretStr] = None
    gcp_project_id: Optional[str] = None
    gcp_credentials_path: Optional[str] = None

    # Logging Configuration
    log_level: str = Field(default="INFO")
    structured_logging: bool = Field(default=True)

    # Rate Limiting
    rate_limit_requests: int = Field(
        default=100, description="Requests per minute")
    rate_limit_window: int = Field(default=60, description="Window in seconds")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def get_database_url() -> str:
    """Get database URL from settings."""
    return get_settings().database_url


def get_vault_config() -> Optional[Dict[str, Any]]:
    """Get Vault configuration if available."""
    settings = get_settings()
    if settings.vault_url and settings.vault_token:
        return {
            "url": settings.vault_url,
            "token": settings.vault_token.get_secret_value(),
            "mount_point": settings.vault_mount_point,
            "secret_path": settings.vault_secret_path,
        }
    return None
