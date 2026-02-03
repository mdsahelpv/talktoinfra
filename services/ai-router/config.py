"""
Configuration settings for AI Router.
"""

from functools import lru_cache
from typing import List

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

    # Conversation
    max_conversation_history: int = 20
    conversation_ttl_hours: int = 24

    # Message Queue
    nats_url: str = "nats://localhost:4222"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
