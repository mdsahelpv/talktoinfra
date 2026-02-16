"""
Document Deduplication Service for RAG Pipeline.

This module provides functionality for detecting and removing duplicate
or near-duplicate documents from the vector store.
"""

import hashlib
from typing import Any, Dict, List, Optional, Set, Tuple

import structlog

from config import get_settings
from services.embedder import EmbeddingService, get_embedder

logger = structlog.get_logger()


class DeduplicationService:
    """Service for detecting and removing duplicate documents."""

    def __init__(
        self,
        embedder: Optional[EmbeddingService] = None,
        similarity_threshold: float = 0.95,
    ):
        """Initialize the deduplication service.

        Args:
            embedder: Embedding service instance
            similarity_threshold: Threshold for considering documents as duplicates
        """
        settings = get_settings()
        self.embedder = embedder or get_embedder()
        self.similarity_threshold = similarity_threshold

    def generate_document_hash(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate a hash for exact duplicate detection.

        Args:
            content: Document content
            metadata: Optional metadata for additional uniqueness

        Returns:
            SHA-256 hash as hex string
        """
        # Normalize content for hashing
        normalized = content.lower().strip()

        # Add metadata to hash if provided
        if metadata:
            key_fields = ["resource_type", "resource_name", "source_id"]
            for field in key_fields:
                if field in metadata and metadata[field]:
                    normalized += f"|{field}:{metadata[field]}"

        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def compute_similarity(
        self,
        vector1: List[float],
        vector2: List[float],
    ) -> float:
        """Compute cosine similarity between two vectors.

        Args:
            vector1: First embedding vector
            vector2: Second embedding vector

        Returns:
            Cosine similarity score (0-1)
        """
        if len(vector1) != len(vector2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vector1, vector2))
        magnitude1 = sum(a * a for a in vector1) ** 0.5
        magnitude2 = sum(b * b for b in vector2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def find_exact_duplicates(
        self,
        documents: List[Dict[str, Any]],
    ) -> Dict[str, List[str]]:
        """Find exact duplicate documents based on content hash.

        Args:
            documents: List of documents with 'content' and 'metadata' fields

        Returns:
            Dictionary mapping original document IDs to lists of duplicate IDs
        """
        hash_to_docs: Dict[str, List[Dict[str, Any]]] = {}
        duplicates: Dict[str, List[str]] = {}

        for doc in documents:
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})
            doc_id = doc.get("id", "")

            if not doc_id:
                continue

            doc_hash = self.generate_document_hash(content, metadata)

            if doc_hash in hash_to_docs:
                # This is a duplicate
                original_id = hash_to_docs[doc_hash][0].get("id")
                if original_id not in duplicates:
                    duplicates[original_id] = []
                duplicates[original_id].append(doc_id)
                hash_to_docs[doc_hash].append(doc)
            else:
                hash_to_docs[doc_hash] = [doc]

        logger.info(
            "exact_duplicates_found",
            duplicate_groups=len(duplicates),
        )

        return duplicates

    def find_near_duplicates(
        self,
        documents: List[Dict[str, Any]],
        use_embeddings: bool = True,
    ) -> Dict[str, List[str]]:
        """Find near-duplicate documents using embeddings.

        Args:
            documents: List of documents with 'content' and 'metadata' fields
            use_embeddings: Whether to use embeddings for similarity (slower but accurate)

        Returns:
            Dictionary mapping original document IDs to lists of near-duplicate IDs
        """
        if not documents:
            return {}

        near_duplicates: Dict[str, List[str]] = {}
        processed: Set[str] = set()

        if use_embeddings:
            # Generate embeddings for all documents
            contents = [doc.get("content", "") for doc in documents]
            embeddings = self.embedder.generate_embeddings_batch(contents)

            # Compare each document with others
            for i, doc in enumerate(documents):
                doc_id = doc.get("id", "")
                if doc_id in processed or not doc_id:
                    continue

                similar_docs: List[str] = []

                for j, other_doc in enumerate(documents):
                    if i == j:
                        continue

                    other_id = other_doc.get("id", "")
                    if other_id in processed or not other_id:
                        continue

                    similarity = self.compute_similarity(
                        embeddings[i],
                        embeddings[j],
                    )

                    if similarity >= self.similarity_threshold:
                        similar_docs.append(other_id)
                        processed.add(other_id)

                if similar_docs:
                    near_duplicates[doc_id] = similar_docs
                    processed.add(doc_id)

        else:
            # Fallback: Use content-based comparison
            for i, doc in enumerate(documents):
                doc_id = doc.get("id", "")
                if doc_id in processed or not doc_id:
                    continue

                content = doc.get("content", "")
                similar_docs: List[str] = []

                for j, other_doc in enumerate(documents):
                    if i == j:
                        continue

                    other_id = other_doc.get("id", "")
                    if other_id in processed or not other_id:
                        continue

                    other_content = other_doc.get("content", "")

                    # Simple Jaccard similarity on words
                    words1 = set(content.lower().split())
                    words2 = set(other_content.lower().split())

                    if not words1 or not words2:
                        continue

                    intersection = len(words1 & words2)
                    union = len(words1 | words2)
                    similarity = intersection / union if union > 0 else 0

                    if similarity >= self.similarity_threshold:
                        similar_docs.append(other_id)
                        processed.add(other_id)

                if similar_docs:
                    near_duplicates[doc_id] = similar_docs
                    processed.add(doc_id)

        logger.info(
            "near_duplicates_found",
            duplicate_groups=len(near_duplicates),
            threshold=self.similarity_threshold,
        )

        return near_duplicates

    def deduplicate_documents(
        self,
        documents: List[Dict[str, Any]],
        strategy: str = "keep_first",
    ) -> List[Dict[str, Any]]:
        """Remove duplicate documents from a list.

        Args:
            documents: List of documents to deduplicate
            strategy: Deduplication strategy ('keep_first', 'keep_newest', 'keep_oldest')

        Returns:
            Deduplicated list of documents
        """
        if not documents:
            return []

        # First find exact duplicates
        exact_dups = self.find_exact_duplicates(documents)

        # Track IDs to remove
        ids_to_remove: Set[str] = set()

        for original_id, duplicate_ids in exact_dups.items():
            ids_to_remove.update(duplicate_ids)

        # Find near duplicates among remaining documents
        remaining_docs = [
            doc for doc in documents if doc.get("id") not in ids_to_remove
        ]

        near_dups = self.find_near_duplicates(remaining_docs)

        for original_id, duplicate_ids in near_dups.items():
            ids_to_remove.update(duplicate_ids)

        # Filter out duplicates
        deduplicated = [
            doc for doc in documents if doc.get("id") not in ids_to_remove
        ]

        logger.info(
            "documents_deduplicated",
            original_count=len(documents),
            deduplicated_count=len(deduplicated),
            removed_count=len(documents) - len(deduplicated),
        )

        return deduplicated

    def get_duplicate_report(
        self,
        documents: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Generate a detailed duplicate report.

        Args:
            documents: List of documents to analyze

        Returns:
            Report with duplicate information
        """
        exact_dups = self.find_exact_duplicates(documents)
        near_dups = self.find_near_duplicates(documents)

        total_duplicates = sum(len(dups) for dups in exact_dups.values())
        total_duplicates += sum(len(dups) for dups in near_dups.values())

        return {
            "total_documents": len(documents),
            "exact_duplicate_groups": len(exact_dups),
            "exact_duplicate_count": sum(len(dups) for dups in exact_dups.values()),
            "near_duplicate_groups": len(near_dups),
            "near_duplicate_count": sum(len(dups) for dups in near_dups.values()),
            "total_duplicates": total_duplicates,
            "unique_documents": len(documents) - total_duplicates,
            "similarity_threshold": self.similarity_threshold,
            "exact_duplicates": exact_dups,
            "near_duplicates": near_dups,
        }


# Singleton instance
_deduplication_service: Optional[DeduplicationService] = None


def get_deduplication_service() -> DeduplicationService:
    """Get the singleton deduplication service instance."""
    global _deduplication_service
    if _deduplication_service is None:
        settings = get_settings()
        _deduplication_service = DeduplicationService(
            embedder=get_embedder(),
            similarity_threshold=0.95,
        )
    return _deduplication_service
