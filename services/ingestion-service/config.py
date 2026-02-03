"""
Configuration settings for Ingestion Service.
"""

from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Service
    service_port: int = 8004
    service_name: str = "ingestion-service"

    # Qdrant Configuration
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "infrastructure"
    qdrant_api_key: Optional[str] = None

    # Ollama Configuration for Embeddings
    ollama_host: str = "http://localhost:11434"
    embedding_model: str = "nomic-embed-text"
    embedding_dimensions: int = 768

    # Ingestion Settings
    batch_size: int = 100
    max_workers: int = 4
    ingestion_interval_minutes: int = 30

    # Resource Types
    default_resource_types: List[str] = [
        "pod",
        "deployment",
        "service",
        "configmap",
        "secret",
        "ingress",
        "persistentvolumeclaim",
    ]

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
