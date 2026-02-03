"""
RAG (Retrieval-Augmented Generation) engine using Qdrant.
"""

from typing import Any, Dict, List, Optional

import structlog
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import Distance, VectorParams
from sentence_transformers import SentenceTransformer

from config import get_settings

logger = structlog.get_logger()


class RAGEngine:
    """Retrieval-Augmented Generation engine using Qdrant vector database."""

    def __init__(
        self,
        qdrant_url: str,
        ollama_host: str,
        collection_name: str = "infrastructure",
        embedding_model: str = "all-MiniLM-L6-v2",
    ):
        """Initialize RAG engine.

        Args:
            qdrant_url: Qdrant server URL
            ollama_host: Ollama server URL for embeddings
            collection_name: Qdrant collection name
            embedding_model: Sentence-transformers model name
        """
        self.qdrant_url = qdrant_url
        self.ollama_host = ollama_host
        self.collection_name = collection_name
        self.embedding_model_name = embedding_model

        self.client: Optional[AsyncQdrantClient] = None
        self.embedding_model: Optional[SentenceTransformer] = None
        self.vector_size = 384  # Default for all-MiniLM-L6-v2

    async def _get_client(self) -> AsyncQdrantClient:
        """Get or create Qdrant client."""
        if self.client is None:
            self.client = AsyncQdrantClient(url=self.qdrant_url)
        return self.client

    def _get_embedding_model(self) -> SentenceTransformer:
        """Get or load embedding model."""
        if self.embedding_model is None:
            logger.info("loading_embedding_model", model=self.embedding_model_name)
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
        return self.embedding_model

    async def health_check(self) -> Dict[str, Any]:
        """Check Qdrant connection health.

        Returns:
            Health status dict

        Raises:
            ConnectionError: If Qdrant is unreachable
        """
        try:
            client = await self._get_client()
            collections = await client.get_collections()

            # Check if our collection exists
            collection_names = [c.name for c in collections.collections]
            collection_exists = self.collection_name in collection_names

            return {
                "status": "healthy",
                "qdrant_url": self.qdrant_url,
                "collection_exists": collection_exists,
                "available_collections": collection_names,
            }

        except Exception as e:
            logger.error("qdrant_health_check_failed", error=str(e))
            raise ConnectionError(f"Qdrant health check failed: {str(e)}")

    async def ensure_collection(self) -> None:
        """Ensure the collection exists, create if not."""
        client = await self._get_client()

        try:
            await client.get_collection(self.collection_name)
            logger.debug("collection_exists", collection=self.collection_name)
        except Exception:
            logger.info("creating_collection", collection=self.collection_name)
            await client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE,
                ),
            )

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for text.

        Args:
            text: Input text

        Returns:
            Embedding vector as list of floats
        """
        model = self._get_embedding_model()
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filter_conditions: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve similar documents by query embedding.

        Args:
            query: Search query text
            top_k: Number of results to return
            filter_conditions: Optional Qdrant filter

        Returns:
            List of retrieved documents with scores
        """
        try:
            client = await self._get_client()

            # Generate query embedding
            query_vector = self._generate_embedding(query)

            # Search in Qdrant
            settings = get_settings()
            results = await client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=top_k,
                with_payload=True,
                score_threshold=settings.rag_similarity_threshold,
            )

            # Format results
            documents = []
            for result in results:
                doc = {
                    "id": str(result.id),
                    "score": float(result.score),
                    "payload": result.payload or {},
                }

                # Extract resource type from payload if available
                if result.payload:
                    doc["resource_type"] = result.payload.get("resource_type")

                documents.append(doc)

            logger.info(
                "rag_retrieval_completed",
                query_length=len(query),
                results_count=len(documents),
                top_score=documents[0]["score"] if documents else 0,
            )

            return documents

        except Exception as e:
            logger.error("rag_retrieval_failed", error=str(e), query_length=len(query))
            raise

    async def add_document(
        self,
        document_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Add a document to the vector store.

        Args:
            document_id: Unique document identifier
            text: Document text content
            metadata: Optional metadata dict

        Returns:
            True if successful
        """
        try:
            client = await self._get_client()
            await self.ensure_collection()

            # Generate embedding
            vector = self._generate_embedding(text)

            # Prepare payload
            payload = metadata or {}
            payload["text"] = text

            # Upsert to Qdrant
            await client.upsert(
                collection_name=self.collection_name,
                points=[
                    {
                        "id": document_id,
                        "vector": vector,
                        "payload": payload,
                    }
                ],
            )

            logger.info(
                "document_added",
                document_id=document_id,
                vector_size=len(vector),
            )

            return True

        except Exception as e:
            logger.error("document_add_failed", error=str(e), document_id=document_id)
            raise

    async def delete_document(self, document_id: str) -> bool:
        """Delete a document from the vector store.

        Args:
            document_id: Document identifier

        Returns:
            True if deleted
        """
        try:
            client = await self._get_client()
            await client.delete(
                collection_name=self.collection_name,
                points_selector={"points": [document_id]},
            )

            logger.info("document_deleted", document_id=document_id)
            return True

        except Exception as e:
            logger.error(
                "document_delete_failed", error=str(e), document_id=document_id
            )
            raise

    async def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the collection.

        Returns:
            Collection info dict
        """
        client = await self._get_client()
        info = await client.get_collection(self.collection_name)

        return {
            "name": info.config.params.vectors.size,
            "vector_size": info.config.params.vectors.size,
            "distance": info.config.params.vectors.distance,
            "points_count": info.points_count,
        }
