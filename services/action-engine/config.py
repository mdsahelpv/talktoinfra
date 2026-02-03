"""
Configuration settings for Action Engine.
"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Service
    service_port: int = 8002
    service_name: str = "action-engine"

    # Backend Services
    policy_engine_url: str = "http://localhost:8003"
    audit_service_url: str = "http://localhost:8005"
    ingestion_service_url: str = "http://localhost:8004"

    # Sandbox Configuration
    sandbox_enabled: bool = True
    sandbox_timeout_seconds: int = 300
    sandbox_max_memory_mb: int = 512
    sandbox_max_cpu_percent: int = 50

    # Rollback Configuration
    rollback_retention_hours: int = 24
    max_rollback_points: int = 100

    # Execution Configuration
    max_concurrent_actions: int = 10
    action_timeout_seconds: int = 600

    # Security
    require_approval_for_destructive: bool = True
    require_approval_for_production: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
