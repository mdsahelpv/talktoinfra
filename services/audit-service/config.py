"""
Configuration settings for Audit Service.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Service
    service_port: int = 8005
    service_name: str = "audit-service"

    # Storage
    log_storage_path: str = "/data/audit-logs"
    log_retention_days: int = 365
    max_log_size_mb: int = 100

    # Integrity
    hash_algorithm: str = "sha256"
    enable_hash_chain: bool = True

    # Export
    export_directory: str = "/data/exports"
    export_max_age_hours: int = 24
    max_export_entries: int = 100000

    # Compliance
    compliance_check_interval_hours: int = 24
    alert_on_anomalies: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
