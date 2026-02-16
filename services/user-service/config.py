"""User Service Configuration."""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    service_port: int = Field(default=8008, description="User service port")
    service_host: str = Field(default="0.0.0.0", description="User service host")

    # Database
    database_url: str = Field(
        default="postgresql://opsai:changeme@postgres:5432/opsai_users",
        description="PostgreSQL database URL",
    )
    database_url_async: str = Field(
        default="postgresql+asyncpg://opsai:changeme@postgres:5432/opsai_users",
        description="PostgreSQL async database URL",
    )

    # Redis for sessions
    redis_url: str = Field(
        default="redis://redis:6379/6",
        description="Redis URL for session storage",
    )

    # JWT Settings
    jwt_secret: str = Field(
        default="your-secret-key-change-in-production",
        description="JWT secret key",
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_access_token_expire_minutes: int = Field(
        default=30, description="Access token expiration in minutes"
    )
    jwt_refresh_token_expire_days: int = Field(
        default=7, description="Refresh token expiration in days"
    )

    # OAuth Providers
    oauth_google_enabled: bool = Field(
        default=False, description="Enable Google OAuth"
    )
    oauth_google_client_id: Optional[str] = Field(
        default=None, description="Google OAuth client ID"
    )
    oauth_google_client_secret: Optional[str] = Field(
        default=None, description="Google OAuth client secret"
    )

    oauth_github_enabled: bool = Field(
        default=False, description="Enable GitHub OAuth"
    )
    oauth_github_client_id: Optional[str] = Field(
        default=None, description="GitHub OAuth client ID"
    )
    oauth_github_client_secret: Optional[str] = Field(
        default=None, description="GitHub OAuth client secret"
    )

    oauth_azure_enabled: bool = Field(
        default=False, description="Enable Azure AD OAuth"
    )
    oauth_azure_client_id: Optional[str] = Field(
        default=None, description="Azure AD client ID"
    )
    oauth_azure_client_secret: Optional[str] = Field(
        default=None, description="Azure AD client secret"
    )
    oauth_azure_tenant_id: Optional[str] = Field(
        default=None, description="Azure AD tenant ID"
    )

    # MFA Settings
    mfa_enabled: bool = Field(default=False, description="Enable MFA/TOTP")
    mfa_issuer: str = Field(default="TalkAI", description="MFA issuer name")

    # Session Settings
    session_expire_hours: int = Field(
        default=24, description="Session expiration in hours"
    )
    max_sessions_per_user: int = Field(
        default=5, description="Maximum concurrent sessions per user"
    )

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
        env_prefix = "USER_SERVICE_"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
