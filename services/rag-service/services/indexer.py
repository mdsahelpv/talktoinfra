"""
Index management service for RAG pipeline.

This module provides functionality for managing Qdrant vector collections
and performing CRUD operations on indexed documents.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import (
    Distance,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from config import get_settings

logger = structlog.get_logger()


class IndexingService:
    """Service for managing vector indices in Qdrant."""

    def __init__(
        self,
        qdrant_url: Optional[str] = None,
        qdrant_api_key: Optional[str] = None,
    ):
        """Initialize the indexing service.

        Args:
            qdrant_url: Qdrant server URL
            qdrant_api_key: Qdrant API key
        """
        settings = get_settings()

        self.qdrant_url = qdrant_url or settings.qdrant_url
        self.qdrant_api_key = qdrant_api_key or settings.qdrant_api_key

        # Collection names
        self.collection_infrastructure = settings.collection_infrastructure
        self.collection_logs = settings.collection_logs
        self.collection_docs = settings.collection_docs
        self.collection_k8s_resources = settings.collection_k8s_resources

        # Vector configuration
        self.vector_size = 384  # Default for all-MiniLM-L6-v2
        self.distance = Distance.COSINE

        self._client: Optional[AsyncQdrantClient] = None

    async def _get_client(self) -> AsyncQdrantClient:
        """Get or create Qdrant client."""
        if self._client is None:
            self._client = AsyncQdrantClient(
                url=self.qdrant_url,
                api_key=self.qdrant_api_key,
            )
        return self._client

    async def get_all_collections(self) -> List[str]:
        """Get list of all collection names.

        Returns:
            List of collection names
        """
        client = await self._get_client()
        collections = await client.get_collections()
        return [c.name for c in collections.collections]

    async def collection_exists(self, collection_name: str) -> bool:
        """Check if a collection exists.

        Args:
            collection_name: Name of collection

        Returns:
            True if collection exists
        """
        client = await self._get_client()
        try:
            await client.get_collection(collection_name)
            return True
        except Exception:
            return False

    async def create_collection(
        self,
        collection_name: str,
        vector_size: Optional[int] = None,
        distance: Optional[Distance] = None,
    ) -> bool:
        """Create a new collection.

        Args:
            collection_name: Name of collection
            vector_size: Vector dimension size
            distance: Distance metric

        Returns:
            True if created successfully
        """
        client = await self._get_client()

        vec_size = vector_size or self.vector_size
        dist = distance or self.distance

        await client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=vec_size,
                distance=dist,
            ),
        )

        logger.info("collection_created", collection=collection_name)
        return True

    async def ensure_collection(self, collection_name: str) -> bool:
        """Ensure collection exists, create if not.

        Args:
            collection_name: Name of collection

        Returns:
            True if collection exists or was created
        """
        if await self.collection_exists(collection_name):
            logger.debug("collection_exists", collection=collection_name)
            return True

        logger.info("creating_collection", collection=collection_name)
        return await self.create_collection(collection_name)

    async def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection.

        Args:
            collection_name: Name of collection

        Returns:
            True if deleted successfully
        """
        client = await self._get_client()
        await client.delete_collection(collection_name)
        logger.info("collection_deleted", collection=collection_name)
        return True

    async def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """Get information about a collection.

        Args:
            collection_name: Name of collection

        Returns:
            Collection info dict
        """
        client = await self._get_client()
        info = await client.get_collection(collection_name)

        return {
            "name": collection_name,
            "vector_size": info.config.params.vectors.size,
            "distance": info.config.params.vectors.distance,
            "points_count": info.points_count,
        }

    async def index_document(
        self,
        collection_name: str,
        document_id: str,
        vector: List[float],
        payload: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Index a single document.

        Args:
            collection_name: Target collection
            document_id: Unique document ID
            vector: Embedding vector
            payload: Document metadata

        Returns:
            True if indexed successfully
        """
        client = await self._get_client()
        await self.ensure_collection(collection_name)

        point = PointStruct(
            id=document_id,
            vector=vector,
            payload=payload or {},
        )

        await client.upsert(
            collection_name=collection_name,
            points=[point],
        )

        logger.info(
            "document_indexed",
            collection=collection_name,
            document_id=document_id,
        )
        return True

    async def index_documents_batch(
        self,
        collection_name: str,
        documents: List[Dict[str, Any]],
    ) -> int:
        """Index multiple documents in batch.

        Args:
            collection_name: Target collection
            documents: List of documents with id, vector, payload

        Returns:
            Number of documents indexed
        """
        if not documents:
            return 0

        client = await self._get_client()
        await self.ensure_collection(collection_name)

        points = [
            PointStruct(
                id=doc["id"],
                vector=doc["vector"],
                payload=doc.get("payload", {}),
            )
            for doc in documents
        ]

        await client.upsert(
            collection_name=collection_name,
            points=points,
        )

        logger.info(
            "documents_indexed_batch",
            collection=collection_name,
            count=len(documents),
        )
        return len(documents)

    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        top_k: int = 10,
        filter_conditions: Optional[Dict[str, Any]] = None,
        score_threshold: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Search for similar documents.

        Args:
            collection_name: Target collection
            query_vector: Query embedding vector
            top_k: Number of results
            filter_conditions: Qdrant filter conditions
            score_threshold: Minimum similarity score

        Returns:
            List of search results
        """
        client = await self._get_client()

        qdrant_filter = None
        if filter_conditions:
            qdrant_filter = Filter(**filter_conditions)

        results = await client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=top_k,
            with_payload=True,
            with_vectors=False,
            filter=qdrant_filter,
            score_threshold=score_threshold,
        )

        return [
            {
                "id": str(result.id),
                "score": float(result.score),
                "payload": result.payload or {},
            }
            for result in results
        ]

    async def delete_document(
        self,
        collection_name: str,
        document_id: str,
    ) -> bool:
        """Delete a document from collection.

        Args:
            collection_name: Target collection
            document_id: Document ID to delete

        Returns:
            True if deleted successfully
        """
        client = await self._get_client()
        await client.delete(
            collection_name=collection_name,
            points_selector={"points": [document_id]},
        )

        logger.info(
            "document_deleted",
            collection=collection_name,
            document_id=document_id,
        )
        return True

    async def delete_by_filter(
        self,
        collection_name: str,
        filter_conditions: Dict[str, Any],
    ) -> int:
        """Delete documents matching filter.

        Args:
            collection_name: Target collection
            filter_conditions: Filter conditions

        Returns:
            Number of documents deleted
        """
        client = await self._get_client()

        qdrant_filter = Filter(**filter_conditions)

        result = await client.delete(
            collection_name=collection_name,
            points_selector=Filter(must=qdrant_filter.must),
        )

        logger.info(
            "documents_deleted_by_filter",
            collection=collection_name,
            count=result.operation_id,
        )
        return result.operation_id

    async def update_payload(
        self,
        collection_name: str,
        document_id: str,
        payload: Dict[str, Any],
    ) -> bool:
        """Update payload for a document.

        Args:
            collection_name: Target collection
            document_id: Document ID
            payload: New payload data

        Returns:
            True if updated successfully
        """
        client = await self._get_client()

        await client.set_payload(
            collection_name=collection_name,
            payload=payload,
            points=[document_id],
        )

        logger.info(
            "payload_updated",
            collection=collection_name,
            document_id=document_id,
        )
        return True

    def get_collection_for_document_type(self, document_type: str) -> str:
        """Get the appropriate collection for a document type.

        Args:
            document_type: Type of document

        Returns:
            Collection name
        """
        collection_map = {
            "infrastructure": self.collection_infrastructure,
            "log": self.collection_logs,
            "doc": self.collection_docs,
            "k8s_resource": self.collection_k8s_resources,
        }
        return collection_map.get(document_type, self.collection_infrastructure)


# Singleton instance
_indexing_service: Optional[IndexingService] = None


def get_indexer() -> IndexingService:
    """Get the singleton indexing service instance."""
    global _indexing_service
    if _indexing_service is None:
        _indexing_service = IndexingService()
    return _indexing_service
