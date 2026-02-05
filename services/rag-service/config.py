"""
Configuration for RAG Service.

This module provides settings for the RAG (Retrieval-Augmented Generation)
service using Pydantic settings with environment variable support.
"""

from functools import lru_cache
from typing import Any, Dict, List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings for RAG service."""

    # Service configuration
    service_name: str = Field(default="rag-service",
                              description="Service name")
    service_port: int = Field(default=8012, description="Service port")
    debug: bool = Field(default=False, description="Debug mode")

    # Database configuration (PostgreSQL)
    database_url: str = Field(
        default="postgresql://opsai:changeme@localhost:5432/opsai",
        description="PostgreSQL database URL",
    )
    database_url_async: str = Field(
        default="postgresql+asyncpg://opsai:changeme@localhost:5432/opsai",
        description="Async PostgreSQL database URL",
    )

    # Redis configuration
    redis_url: str = Field(
        default="redis://localhost:6379/5",
        description="Redis URL for caching",
    )

    # Qdrant (Vector DB) configuration
    qdrant_url: str = Field(
        default="http://localhost:6333",
        description="Qdrant server URL",
    )
    qdrant_api_key: Optional[str] = Field(
        default=None,
        description="Qdrant API key",
    )

    # Elasticsearch/OpenSearch configuration
    elasticsearch_url: Optional[str] = Field(
        default=None,
        description="Elasticsearch URL",
    )
    elasticsearch_api_key: Optional[str] = Field(
        default=None,
        description="Elasticsearch API key",
    )

    # Embedding model configuration
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2",
        description="Sentence-transformers model name",
    )
    embedding_batch_size: int = Field(
        default=32,
        description="Batch size for embedding generation",
    )
    embedding_device: str = Field(
        default="cpu",
        description="Device for embedding model (cpu/cuda)",
    )

    # RAG configuration
    rag_similarity_threshold: float = Field(
        default=0.7,
        description="Minimum similarity score for RAG retrieval",
    )
    rag_top_k: int = Field(
        default=10,
        description="Default number of results to retrieve",
    )
    rag_max_context_length: int = Field(
        default=4000,
        description="Maximum context length for RAG prompts",
    )

    # Collection names for different document types
    collection_infrastructure: str = Field(
        default="infrastructure-resources",
        description="Collection for infrastructure resources",
    )
    collection_logs: str = Field(
        default="infrastructure-logs",
        description="Collection for log patterns",
    )
    collection_docs: str = Field(
        default="infrastructure-docs",
        description="Collection for documentation",
    )
    collection_k8s_resources: str = Field(
        default="k8s-resources",
        description="Collection for K8s resources",
    )

    # NATS configuration for event-driven indexing
    nats_url: str = Field(
        default="nats://localhost:4222",
        description="NATS server URL",
    )
    nats_rag_channel: str = Field(
        default="rag.index",
        description="NATS channel for indexing events",
    )

    # CORS configuration
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="CORS allowed origins",
    )

    # Rate limiting
    rate_limit_requests: int = Field(
        default=100,
        description="Rate limit requests per minute",
    )

    class Config:
        env_file = ".env"
        env_prefix = "RAG_"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience function for accessing settings
settings = get_settings()
