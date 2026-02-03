"""
Configuration settings for Discovery Service.
"""

from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # Service
    service_name: str = "discovery-service"
    service_port: int = 8007
    debug: bool = False

    # Database
    database_url: str = "postgresql://opsai:changeme@localhost:5432/opsai"
    database_echo: bool = False

    # Redis (for Celery and caching)
    redis_url: str = "redis://localhost:6379/1"

    # JWT (shared with api-gateway)
    jwt_secret: str = "your-secret-key"
    jwt_algorithm: str = "HS256"

    # Scanner binaries
    masscan_path: str = "/usr/bin/masscan"
    nmap_path: str = "/usr/bin/nmap"

    # Scan limits
    max_network_size: int = 65536  # /16 network
    max_ports_per_scan: int = 1000
    require_approval_threshold: int = 4096  # /20 network - requires admin approval

    # Masscan settings
    masscan_rate: int = 1000  # packets per second
    masscan_adapter: Optional[str] = None  # Network interface (None = auto)
    masscan_wait_time: int = 10  # seconds to wait after scan completes

    # Nmap settings
    nmap_timing_template: str = "T4"  # T0 (paranoid) to T5 (insane)
    nmap_service_detection: bool = True
    nmap_os_detection: bool = False  # Requires root
    nmap_script_scan: bool = False

    # Python scanner settings
    python_scan_timeout: float = 2.0  # seconds per connection
    python_scan_concurrent: int = 50  # concurrent connections per host
    python_max_hosts_concurrent: int = 100  # max hosts scanned concurrently

    # Hybrid scan settings
    hybrid_masscan_timeout: float = 300.0  # 5 minutes max for masscan phase
    hybrid_nmap_timeout: float = 600.0  # 10 minutes max for nmap phase
    hybrid_max_hosts_for_nmap: int = 1000  # If masscan finds more, skip detailed scan

    # Health monitoring
    health_check_enabled: bool = True
    health_check_interval_seconds: int = 300  # 5 minutes
    health_check_timeout: float = 3.0  # seconds
    health_check_ports: List[int] = [22, 80, 443]  # Default ports to check

    # Retention (days)
    scan_result_retention_days: int = 7
    health_history_retention_days: int = 90
    max_health_checks_per_host: int = 1000  # Keep last N checks

    # Security
    excluded_networks: List[str] = [
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "127.0.0.0/8",
        "0.0.0.0/8",
        "169.254.0.0/16",
        "224.0.0.0/4",
        "240.0.0.0/4",
    ]

    # Rate limiting
    scan_rate_limit_per_minute: int = 5  # Max scans per user per minute
    api_rate_limit_per_minute: int = 100  # General API rate limit per user
    admin_rate_limit_per_minute: int = 30  # Admin operations rate limit
    max_concurrent_scans: int = 3  # Max concurrent scans system-wide

    # API Gateway (for auth verification)
    api_gateway_url: str = "http://localhost:8000"
    verify_token_with_gateway: bool = True

    # CORS settings
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    cors_allow_headers: List[str] = ["*"]

    # Security
    allowed_hosts: List[str] = ["*"]  # Restrict in production


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
