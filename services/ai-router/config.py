"""
Configuration settings for AI Router.
"""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Service
    service_port: int = 8001
    service_name: str = "ai-router"

    # Database
    postgres_url: str = "postgresql://opsai:changeme@localhost:5432/opsai"
    redis_url: str = "redis://localhost:6379"

    # Vector Database
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "infrastructure"

    # Ollama Configuration
    ollama_host: str = "http://localhost:11434"
    ollama_model_chat: str = "llama3.3:70b"
    ollama_model_code: str = "codellama:34b"
    ollama_model_embed: str = "nomic-embed-text"

    # RAG Configuration
    rag_top_k: int = 5
    rag_similarity_threshold: float = 0.7
    rag_chunk_size: int = 1000
    rag_chunk_overlap: int = 200
    rag_embedding_model: str = "nomic-embed-text"

    # Model Registry Settings
    model_registry_enabled: bool = True
    default_chat_model: str = "llama3.3:70b"
    default_embedding_model: str = "nomic-embed-text"
    default_code_model: str = "codellama:34b"

    # Provider Configurations (with env var support)
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    azure_api_key: Optional[str] = None
    azure_endpoint: Optional[str] = None
    azure_api_version: str = "2024-02-01"
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"
    ollama_api_key: Optional[str] = None

    # Cost Tracking Settings
    cost_tracking_enabled: bool = True
    cost_limit_monthly: Optional[float] = None
    cost_warning_threshold: float = 0.8

    # Default Model Assignments
    agent_query_model: str = "llama3.3:70b"
    agent_action_model: str = "llama3.3:70b"
    agent_analysis_model: str = "llama3.3:70b"
    agent_planning_model: str = "llama3.3:70b"

    # Safety Settings
    safety_approval_threshold: str = "MEDIUM"
    safety_block_critical_actions: bool = True
    safety_max_retries: int = 3

    # Conversation
    max_conversation_history: int = 20
    conversation_ttl_hours: int = 24

    # Message Queue
    nats_url: str = "nats://localhost:4222"

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
