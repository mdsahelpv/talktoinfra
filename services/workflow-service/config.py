"""
Workflow Service Configuration
"""

from typing import List, Optional
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
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 2
    redis_password: Optional[str] = None
    state_cache_ttl: int = 86400  # 24 hours

    # NATS (for event-driven workflow updates)
    nats_url: str = "nats://localhost:4222"
    nats_connection_timeout: int = 5
    nats_reconnect_timeout: int = 5

    # Celery (for async workflow execution)
    celery_broker_url: str = "redis://localhost:6379/14"
    celery_result_backend: str = "redis://localhost:6379/15"
    celery_task_serializer: str = "json"
    celery_result_serializer: str = "json"
    celery_accept_content: List[str] = ["json"]
    celery_timezone: str = "UTC"
    celery_task_track_started: bool = True
    celery_task_time_limit: int = 3600  # 1 hour
    celery_soft_time_limit: int = 3300  # 55 minutes

    # External Services
    action_engine_url: str = "http://localhost:8010"
    notification_url: str = "http://localhost:8013"

    class Config:
        env_file = ".env"
        env_prefix = "WORKFLOW_"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
