"""
Embedding service for RAG pipeline.

This module provides functionality for generating text embeddings
using sentence-transformers models.
"""

import hashlib
import time
from typing import Any, Dict, List, Optional

import structlog
from sentence_transformers import SentenceTransformer

from config import get_settings

logger = structlog.get_logger()


class EmbeddingService:
    """Service for generating text embeddings."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        batch_size: Optional[int] = None,
    ):
        """Initialize the embedding service.

        Args:
            model_name: Name of the sentence-transformers model
            device: Device to run model on (cpu/cuda)
            batch_size: Batch size for embedding generation
        """
        settings = get_settings()

        self.model_name = model_name or settings.embedding_model
        self.device = device or settings.embedding_device
        self.batch_size = batch_size or settings.embedding_batch_size

        self._model: Optional[SentenceTransformer] = None
        self._vector_size: Optional[int] = None

    def _load_model(self) -> SentenceTransformer:
        """Load and cache the embedding model."""
        if self._model is None:
            logger.info(
                "loading_embedding_model",
                model=self.model_name,
                device=self.device,
            )
            self._model = SentenceTransformer(
                self.model_name,
                device=self.device,
            )
        return self._model

    @property
    def vector_size(self) -> int:
        """Get the embedding vector size."""
        if self._vector_size is None:
            model = self._load_model()
            self._vector_size = model.get_sentence_embedding_dimension()
        return self._vector_size

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text.

        Args:
            text: Input text to embed

        Returns:
            Embedding vector as list of floats
        """
        model = self._load_model()
        embedding = model.encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return embedding.tolist()

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts in batch.

        Args:
            texts: List of input texts to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        model = self._load_model()
        start_time = time.time()

        embeddings = model.encode(
            texts,
            batch_size=self.batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        elapsed_ms = (time.time() - start_time) * 1000
        logger.info(
            "batch_embeddings_generated",
            count=len(texts),
            vector_size=self.vector_size,
            elapsed_ms=elapsed_ms,
        )

        return [emb.tolist() for emb in embeddings]

    def generate_content_hash(self, content: str) -> str:
        """Generate SHA-256 hash of content.

        Args:
            content: Text content to hash

        Returns:
            SHA-256 hash as hex string
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def truncate_for_embedding(self, text: str, max_tokens: int = 8000) -> str:
        """Truncate text to fit within token limit.

        Args:
            text: Input text
            max_tokens: Maximum tokens (approximate)

        Returns:
            Truncated text
        """
        # Rough estimate: ~4 characters per token
        max_chars = max_tokens * 4
        if len(text) <= max_chars:
            return text

        truncated = text[:max_chars]
        # Try to truncate at a sentence boundary
        last_period = truncated.rfind(".")
        last_newline = truncated.rfind("\n")

        if last_period > max_chars * 0.8:
            return truncated[: last_period + 1]
        elif last_newline > max_chars * 0.8:
            return truncated[: last_newline + 1]

        return truncated + "..."

    def create_document_text(
        self,
        title: Optional[str],
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create searchable document text from content and metadata.

        Args:
            title: Document title
            content: Main content
            metadata: Additional metadata

        Returns:
            Formatted document text for embedding
        """
        parts = []

        if title:
            parts.append(f"Title: {title}")

        parts.append(f"Content: {content}")

        if metadata:
            # Add key metadata as searchable text
            key_fields = ["resource_type",
                          "resource_name", "namespace", "cluster_id"]
            for field in key_fields:
                if field in metadata and metadata[field]:
                    parts.append(
                        f"{field.replace('_', ' ').title()}: {metadata[field]}")

        return "\n".join(parts)


# Singleton instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedder() -> EmbeddingService:
    """Get the singleton embedding service instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
