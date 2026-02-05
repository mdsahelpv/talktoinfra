"""
RAG settings management service.

Vector store settings (Qdrant, Pinecone, Weaviate)
Embedding model selection
Chunk size, overlap settings
Similarity threshold configuration
Index management (create, rebuild, delete)
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field

import structlog

logger = structlog.get_logger()


class VectorStoreType(str, Enum):
    """Supported vector store types."""

    QDRANT = "qdrant"
    PINECONE = "pinecone"
    WEAVIATE = "weaviate"
    MILVUS = "milvus"
    CHROMA = "chroma"


class EmbeddingProvider(str, Enum):
    """Embedding model providers."""

    OLLAMA = "ollama"
    OPENAI = "openai"
    COHERE = "cohere"
    HUGGINGFACE = "huggingface"
    BEDROCK = "bedrock"


class IndexStatus(str, Enum):
    """Index status enumeration."""

    ACTIVE = "active"
    BUILDING = "building"
    ERROR = "error"
    DISABLED = "disabled"


class VectorStoreConfig(BaseModel):
    """Vector store configuration."""

    id: str = Field(..., description="Vector store unique identifier")
    name: str = Field(..., description="Vector store display name")
    store_type: VectorStoreType = Field(..., description="Vector store type")
    enabled: bool = Field(default=True, description="Store enabled status")

    # Connection settings
    host: Optional[str] = Field(None, description="Host address")
    port: Optional[int] = Field(None, description="Port number")
    url: Optional[str] = Field(None, description="Connection URL")
    api_key: Optional[str] = Field(None, description="API key")
    index_name: str = Field(
        default="infrastructure", description="Index/collection name"
    )

    # Performance settings
    batch_size: int = Field(default=100, description="Batch size for indexing")
    num_workers: int = Field(default=4, description="Number of workers")
    timeout_seconds: int = Field(default=60, description="Request timeout")

    # Metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional config"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Created timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Updated timestamp"
    )


class EmbeddingConfig(BaseModel):
    """Embedding model configuration."""

    id: str = Field(..., description="Embedding config unique identifier")
    name: str = Field(..., description="Embedding model name")
    provider: EmbeddingProvider = Field(..., description="Embedding provider")
    model_id: str = Field(..., description="Model identifier")
    enabled: bool = Field(default=True, description="Embedding enabled")

    # Model settings
    dimensions: int = Field(default=768, description="Embedding dimensions")
    batch_size: int = Field(default=32, description="Batch size for embeddings")

    # Provider-specific settings
    base_url: Optional[str] = Field(None, description="API base URL")
    api_key: Optional[str] = Field(None, description="API key")

    # Cost tracking
    cost_per_1k_tokens: float = Field(default=0.0, description="Cost per 1K tokens")

    # Metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional config"
    )


class ChunkingConfig(BaseModel):
    """Text chunking configuration."""

    chunk_size: int = Field(default=1000, description="Chunk size in characters")
    chunk_overlap: int = Field(default=200, description="Overlap between chunks")
    separators: List[str] = Field(
        default_factory=lambda: ["\\n\\n", "\\n", ". ", "! ", "? ", "  "],
        description="Separators for chunking",
    )
    min_chunk_size: int = Field(default=100, description="Minimum chunk size")
    max_chunk_size: int = Field(default=2000, description="Maximum chunk size")
    preserve_structure: bool = Field(
        default=True, description="Preserve document structure"
    )


class RAGIndexConfig(BaseModel):
    """RAG index configuration."""

    id: str = Field(..., description="Index unique identifier")
    name: str = Field(..., description="Index display name")
    description: Optional[str] = Field(None, description="Index description")
    enabled: bool = Field(default=True, description="Index enabled status")

    # Store and embedding
    vector_store_id: str = Field(..., description="Associated vector store")
    embedding_id: str = Field(..., description="Associated embedding config")

    # Chunking
    chunking: ChunkingConfig = Field(
        default_factory=ChunkingConfig, description="Chunking config"
    )

    # Retrieval settings
    top_k: int = Field(default=5, description="Number of results to retrieve")
    similarity_threshold: float = Field(default=0.7, description="Similarity threshold")
    score_threshold: Optional[float] = Field(
        None, description="Minimum score threshold"
    )

    # Index status
    status: IndexStatus = Field(default=IndexStatus.ACTIVE, description="Index status")
    document_count: int = Field(default=0, description="Number of documents")
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")

    # Metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional config"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Created timestamp"
    )


class RAGSettings(BaseModel):
    """Global RAG settings."""

    # Default configurations
    default_vector_store_id: Optional[str] = Field(
        None, description="Default vector store"
    )
    default_embedding_id: Optional[str] = Field(
        None, description="Default embedding config"
    )
    default_index_id: Optional[str] = Field(
        default="default-index", description="Default index"
    )

    # Retrieval defaults
    default_top_k: int = Field(default=5, description="Default top-k")
    default_similarity_threshold: float = Field(
        default=0.7, description="Default threshold"
    )

    # Chunking defaults
    default_chunk_size: int = Field(default=1000, description="Default chunk size")
    default_chunk_overlap: int = Field(default=200, description="Default overlap")

    # Feature flags
    hybrid_search_enabled: bool = Field(
        default=False, description="Enable hybrid search"
    )
    reranking_enabled: bool = Field(default=False, description="Enable reranking")
    cache_enabled: bool = Field(default=True, description="Enable result caching")
    cache_ttl_seconds: int = Field(default=3600, description="Cache TTL")

    # Performance
    async_indexing: bool = Field(default=True, description="Enable async indexing")
    parallel_processing: bool = Field(
        default=True, description="Enable parallel processing"
    )
    max_concurrent_indexes: int = Field(default=5, description="Max concurrent indexes")


class RAGConfigService:
    """Service for managing RAG configurations."""

    def __init__(self) -> None:
        """Initialize the RAG configuration service."""
        self.vector_stores: Dict[str, VectorStoreConfig] = {}
        self.embeddings: Dict[str, EmbeddingConfig] = {}
        self.indexes: Dict[str, RAGIndexConfig] = {}
        self.settings = RAGSettings()
        self._load_default_config()
        logger.info("rag_config_service_initialized")

    def _load_default_config(self) -> None:
        """Load default RAG configurations."""

        # Default vector store (Qdrant)
        qdrant_store = VectorStoreConfig(
            id="qdrant-default",
            name="Default Qdrant",
            store_type=VectorStoreType.QDRANT,
            enabled=True,
            url="http://localhost:6333",
            index_name="infrastructure",
            batch_size=100,
        )
        self.vector_stores["qdrant-default"] = qdrant_store

        # Default embedding
        ollama_embedding = EmbeddingConfig(
            id="ollama-embed-default",
            name="Ollama Embedding",
            provider=EmbeddingProvider.OLLAMA,
            model_id="nomic-embed-text",
            enabled=True,
            dimensions=768,
            batch_size=32,
        )
        self.embeddings["ollama-embed-default"] = ollama_embedding

        # Default index
        default_index = RAGIndexConfig(
            id="default-index",
            name="Infrastructure Index",
            description="Default infrastructure knowledge index",
            enabled=True,
            vector_store_id="qdrant-default",
            embedding_id="ollama-embed-default",
            chunking=ChunkingConfig(chunk_size=1000, chunk_overlap=200),
            top_k=5,
            similarity_threshold=0.7,
            status=IndexStatus.ACTIVE,
        )
        self.indexes["default-index"] = default_index

        # Update settings
        self.settings.default_vector_store_id = "qdrant-default"
        self.settings.default_embedding_id = "ollama-embed-default"
        self.settings.default_index_id = "default-index"

    # Vector Store Operations
    def get_vector_store(self, store_id: str) -> Optional[VectorStoreConfig]:
        """Get a vector store by ID."""
        return self.vector_stores.get(store_id)

    def list_vector_stores(self, enabled_only: bool = False) -> List[VectorStoreConfig]:
        """List all vector stores."""
        stores = list(self.vector_stores.values())
        if enabled_only:
            stores = [s for s in stores if s.enabled]
        return stores

    def create_vector_store(self, store: VectorStoreConfig) -> VectorStoreConfig:
        """Create a new vector store configuration."""
        store.created_at = datetime.utcnow()
        store.updated_at = datetime.utcnow()
        self.vector_stores[store.id] = store
        logger.info("vector_store_created", store_id=store.id, name=store.name)
        return store

    def update_vector_store(
        self, store_id: str, updates: Dict[str, Any]
    ) -> Optional[VectorStoreConfig]:
        """Update a vector store configuration."""
        store = self.vector_stores.get(store_id)
        if not store:
            return None

        for key, value in updates.items():
            if hasattr(store, key) and key not in ("id", "created_at"):
                setattr(store, key, value)

        store.updated_at = datetime.utcnow()
        logger.info("vector_store_updated", store_id=store_id)
        return store

    def delete_vector_store(self, store_id: str) -> bool:
        """Delete a vector store configuration."""
        if store_id not in self.vector_stores:
            return False

        # Check if any indexes are using this store
        for index in self.indexes.values():
            if index.vector_store_id == store_id:
                logger.warning(
                    "vector_store_in_use",
                    store_id=store_id,
                    index_id=index.id,
                )

        del self.vector_stores[store_id]
        logger.info("vector_store_deleted", store_id=store_id)
        return True

    # Embedding Operations
    def get_embedding(self, embedding_id: str) -> Optional[EmbeddingConfig]:
        """Get an embedding configuration by ID."""
        return self.embeddings.get(embedding_id)

    def list_embeddings(self, enabled_only: bool = False) -> List[EmbeddingConfig]:
        """List all embedding configurations."""
        embeddings = list(self.embeddings.values())
        if enabled_only:
            embeddings = [e for e in embeddings if e.enabled]
        return embeddings

    def create_embedding(self, embedding: EmbeddingConfig) -> EmbeddingConfig:
        """Create a new embedding configuration."""
        self.embeddings[embedding.id] = embedding
        logger.info("embedding_created", embedding_id=embedding.id, name=embedding.name)
        return embedding

    def update_embedding(
        self, embedding_id: str, updates: Dict[str, Any]
    ) -> Optional[EmbeddingConfig]:
        """Update an embedding configuration."""
        embedding = self.embeddings.get(embedding_id)
        if not embedding:
            return None

        for key, value in updates.items():
            if hasattr(embedding, key) and key != "id":
                setattr(embedding, key, value)

        logger.info("embedding_updated", embedding_id=embedding_id)
        return embedding

    def delete_embedding(self, embedding_id: str) -> bool:
        """Delete an embedding configuration."""
        if embedding_id not in self.embeddings:
            return False

        del self.embeddings[embedding_id]
        logger.info("embedding_deleted", embedding_id=embedding_id)
        return True

    # Index Operations
    def get_index(self, index_id: str) -> Optional[RAGIndexConfig]:
        """Get an index configuration by ID."""
        return self.indexes.get(index_id)

    def list_indexes(self, enabled_only: bool = False) -> List[RAGIndexConfig]:
        """List all index configurations."""
        indexes = list(self.indexes.values())
        if enabled_only:
            indexes = [i for i in indexes if i.enabled]
        return indexes

    def create_index(self, index: RAGIndexConfig) -> RAGIndexConfig:
        """Create a new index configuration."""
        index.created_at = datetime.utcnow()
        self.indexes[index.id] = index
        logger.info("index_created", index_id=index.id, name=index.name)
        return index

    def update_index(
        self, index_id: str, updates: Dict[str, Any]
    ) -> Optional[RAGIndexConfig]:
        """Update an index configuration."""
        index = self.indexes.get(index_id)
        if not index:
            return None

        for key, value in updates.items():
            if hasattr(index, key) and key not in ("id", "created_at"):
                setattr(index, key, value)

        logger.info("index_updated", index_id=index_id)
        return index

    def delete_index(self, index_id: str) -> bool:
        """Delete an index configuration."""
        if index_id not in self.indexes:
            return False

        del self.indexes[index_id]
        logger.info("index_deleted", index_id=index_id)
        return True

    def rebuild_index(self, index_id: str) -> bool:
        """Trigger index rebuild."""
        index = self.indexes.get(index_id)
        if not index:
            return False

        index.status = IndexStatus.BUILDING
        index.last_updated = datetime.utcnow()
        logger.info("index_rebuild_started", index_id=index_id)
        return True

    # Settings Operations
    def get_settings(self) -> RAGSettings:
        """Get global RAG settings."""
        return self.settings

    def update_settings(self, settings_updates: Dict[str, Any]) -> RAGSettings:
        """Update global RAG settings."""
        for key, value in settings_updates.items():
            if hasattr(self.settings, key):
                setattr(self.settings, key, value)

        logger.info("rag_settings_updated")
        return self.settings

    # Utility Methods
    def get_default_index(self) -> Optional[RAGIndexConfig]:
        """Get the default index configuration."""
        if self.settings.default_index_id:
            return self.indexes.get(self.settings.default_index_id)
        return None if not self.indexes else list(self.indexes.values())[0]

    def validate_index_config(self, index_id: str) -> Dict[str, Any]:
        """Validate index configuration."""
        index = self.indexes.get(index_id)
        if not index:
            return {"valid": False, "error": "Index not found"}

        store = self.vector_stores.get(index.vector_store_id)
        embedding = self.embeddings.get(index.embedding_id)

        issues = []
        if not store:
            issues.append(f"Vector store '{index.vector_store_id}' not found")
        if not embedding:
            issues.append(f"Embedding '{index.embedding_id}' not found")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "index": index.model_dump() if index else None,
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get RAG configuration statistics."""
        return {
            "vector_stores": {
                "total": len(self.vector_stores),
                "enabled": sum(1 for s in self.vector_stores.values() if s.enabled),
            },
            "embeddings": {
                "total": len(self.embeddings),
                "enabled": sum(1 for e in self.embeddings.values() if e.enabled),
            },
            "indexes": {
                "total": len(self.indexes),
                "enabled": sum(1 for i in self.indexes.values() if i.enabled),
                "active": sum(
                    1 for i in self.indexes.values() if i.status == IndexStatus.ACTIVE
                ),
                "total_documents": sum(i.document_count for i in self.indexes.values()),
            },
            "settings": self.settings.model_dump(),
        }

    # Export/Import
    def export_config(self) -> Dict[str, Any]:
        """Export RAG configuration."""
        return {
            "vector_stores": {k: v.model_dump() for k, v in self.vector_stores.items()},
            "embeddings": {k: v.model_dump() for k, v in self.embeddings.items()},
            "indexes": {k: v.model_dump() for k, v in self.indexes.items()},
            "settings": self.settings.model_dump(),
            "exported_at": datetime.utcnow().isoformat(),
        }

    def import_config(self, data: Dict[str, Any]) -> None:
        """Import RAG configuration."""
        self.vector_stores = {}
        self.embeddings = {}
        self.indexes = {}

        for store_id, store_data in data.get("vector_stores", {}).items():
            self.vector_stores[store_id] = VectorStoreConfig(**store_data)

        for embedding_id, embedding_data in data.get("embeddings", {}).items():
            self.embeddings[embedding_id] = EmbeddingConfig(**embedding_data)

        for index_id, index_data in data.get("indexes", {}).items():
            self.indexes[index_id] = RAGIndexConfig(**index_data)

        if "settings" in data:
            self.settings = RAGSettings(**data["settings"])

        logger.info("rag_config_imported", count=len(self.indexes))


def get_rag_config_service() -> RAGConfigService:
    """Get the RAG configuration service singleton."""
    return RAGConfigService()
