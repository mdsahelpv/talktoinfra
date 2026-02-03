"""
Configuration settings for Policy Engine.
"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Service
    service_port: int = 8003
    service_name: str = "policy-engine"

    # Backend Services
    audit_service_url: str = "http://localhost:8005"

    # Default Roles
    default_roles: List[str] = ["admin", "engineer", "operator", "viewer"]

    # Approval Settings
    approval_expiry_hours: int = 24
    max_approval_chain_length: int = 3

    # Policy Settings
    production_requires_approval: bool = True
    destructive_requires_approval: bool = True
    auto_approve_read_only: bool = True

    # RBAC Settings
    enable_resource_level_permissions: bool = True
    enable_environment_policies: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
