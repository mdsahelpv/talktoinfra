"""
Configuration settings for Agent Service.
Production-ready configuration with safety defaults.
"""

from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Agent Service configuration with production safety defaults."""

    # Service
    service_port: int = Field(default=8006, description="Service port")
    service_name: str = Field(default="agent-service", description="Service name")
    environment: str = Field(default="development", description="Environment")
    log_level: str = Field(default="INFO", description="Logging level")

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://opsai:changeme@localhost:5432/opsai",
        description="PostgreSQL connection URL",
    )

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379", description="Redis connection URL"
    )

    # NATS
    nats_url: str = Field(
        default="nats://localhost:4222", description="NATS connection URL"
    )

    # Ollama LLM
    ollama_host: str = Field(
        default="http://localhost:11434", description="Ollama server URL"
    )
    ollama_model: str = Field(
        default="llama3.3:70b", description="LLM model for agents"
    )
    ollama_timeout: int = Field(
        default=60, description="Ollama request timeout in seconds"
    )

    # Safety Configuration (Production Defaults)
    safety_mode: str = Field(
        default="strict", description="Safety mode: strict, standard, or permissive"
    )
    auto_approve_read_only: bool = Field(
        default=True, description="Auto-approve read-only operations"
    )
    auto_approve_analysis: bool = Field(
        default=True, description="Auto-approve analysis operations"
    )
    require_approval_for_actions: str = Field(
        default="all",
        description="Require approval for: all, high-risk, or critical-only",
    )

    # Rate Limiting
    max_tasks_per_hour: int = Field(
        default=50, description="Maximum tasks per user per hour"
    )
    max_parallel_tasks: int = Field(
        default=5, description="Maximum parallel tasks per user"
    )
    max_tool_calls_per_task: int = Field(
        default=20, description="Maximum tool calls per task"
    )

    # Task Timeouts
    task_timeout_seconds: int = Field(
        default=300, description="Task execution timeout in seconds"
    )
    approval_timeout_seconds: int = Field(
        default=3600, description="Approval request timeout in seconds"
    )

    # Agent Configuration
    max_iterations: int = Field(default=10, description="Maximum agent iterations")
    max_context_tokens: int = Field(
        default=8000, description="Maximum context tokens for LLM"
    )

    # Skills
    skills_directory: str = Field(
        default="/app/skills", description="Skills directory path"
    )
    auto_load_builtin_skills: bool = Field(
        default=True, description="Auto-load built-in skills"
    )

    # External Services
    ai_router_url: str = Field(
        default="http://ai-router:8001", description="AI Router service URL"
    )
    policy_engine_url: str = Field(
        default="http://policy-engine:8003", description="Policy Engine service URL"
    )
    audit_service_url: str = Field(
        default="http://audit-service:8005", description="Audit Service URL"
    )

    # Security
    jwt_secret: str = Field(
        default="changeme-production-secret",
        description="JWT secret for token validation",
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")

    # Blocked Operations (comma-separated)
    blocked_operations: str = Field(
        default="k8s.delete_namespace,k8s.delete_all,aws.terminate_all",
        description="Blocked operations",
    )

    # High-Risk Resources (comma-separated patterns)
    high_risk_resources: str = Field(
        default="kube-system,production,*-prod-*",
        description="High-risk resource patterns",
    )

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"

    def get_blocked_operations(self) -> List[str]:
        """Parse blocked operations from config."""
        return [op.strip() for op in self.blocked_operations.split(",") if op.strip()]

    def get_high_risk_resources(self) -> List[str]:
        """Parse high-risk resource patterns from config."""
        return [
            res.strip() for res in self.high_risk_resources.split(",") if res.strip()
        ]


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
