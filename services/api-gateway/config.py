"""
Configuration settings for API Gateway.
"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Service
    service_port: int = 8000
    service_name: str = "api-gateway"

    # Security
    jwt_secret: str = "your-secret-key"
    jwt_algorithm: str = "HS256"
    admin_password: str = "admin"

    # Database
    postgres_url: str = "postgresql://opsai:changeme@localhost:5432/opsai"
    redis_url: str = "redis://localhost:6379"

    # Backend Services
    ai_router_url: str = "http://localhost:8001"
    action_engine_url: str = "http://localhost:8002"
    policy_engine_url: str = "http://localhost:8003"
    audit_service_url: str = "http://localhost:8005"
    agent_service_url: str = "http://localhost:8006"
    discovery_service_url: str = "http://localhost:8007"
    onboarding_service_url: str = "http://localhost:8011"

    # Rate Limiting
    rate_limit: int = 100  # requests per minute

    # CORS
    cors_origins: List[str] = ["*"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
