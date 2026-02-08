"""
Workflow Service Configuration
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""

    # Service
    service_name: str = "workflow-service"
    service_port: int = 8012
    debug: bool = False

    # Database
    postgres_url: str = "postgresql://postgres:postgres@localhost:5432/talktoinfra"

    # Redis (for workflow state caching)
    redis_url: str = "redis://localhost:6379/2"

    # NATS (for event-driven workflow updates)
    nats_url: str = "nats://localhost:4222"

    # Celery (for async workflow execution)
    celery_broker_url: str = "redis://localhost:6379/3"

    class Config:
        env_file = ".env"
        env_prefix = "WORKFLOW_"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
