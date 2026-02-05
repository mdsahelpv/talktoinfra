"""
Data transformation pipeline for RAG system.

This module provides functionality for transforming various data sources
into RAG documents and indexing them into the vector store.
"""

import hashlib
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from models import RAGDocument, RAGIndexingJob
from services.embedder import EmbeddingService, get_embedder
from services.indexer import IndexingService, get_indexer

logger = structlog.get_logger()


class RAGPipeline:
    """Data transformation and indexing pipeline for RAG system."""

    def __init__(
        self,
        embedder: Optional[EmbeddingService] = None,
        indexer: Optional[IndexingService] = None,
    ):
        """Initialize the RAG pipeline.

        Args:
            embedder: Embedding service instance
            indexer: Indexing service instance
        """
        settings = get_settings()

        self.embedder = embedder or get_embedder()
        self.indexer = indexer or get_indexer()

        self.rag_similarity_threshold = settings.rag_similarity_threshold
        self.rag_top_k = settings.rag_top_k

    async def transform_discovery_host(
        self,
        host_data: Dict[str, Any],
        ports_data: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Transform discovered host into RAG document.

        Args:
            host_data: Host discovery data
            ports_data: List of port data

        Returns:
            RAG document dict
        """
        # Build document content
        content_parts = [
            f"Host: {host_data.get('ip_address', 'unknown')}",
        ]

        if host_data.get("hostname"):
            content_parts.append(f"Hostname: {host_data['hostname']}")

        # Add port information
        if ports_data:
            port_list = ", ".join(
                f"{p.get('port', '?')}/{p.get('service', 'unknown')}"
                for p in ports_data[:10]  # Limit to top 10 ports
            )
            content_parts.append(f"Ports: {port_list}")

        # Add service banners if available
        banners = [p.get("banner") for p in ports_data if p.get("banner")]
        if banners:
            content_parts.append(f"Service Banners: {'; '.join(banners)}")

        content = "\n".join(content_parts)

        # Build metadata
        metadata = {
            "resource_type": "discovered_host",
            "resource_name": host_data.get("ip_address"),
            "source_type": "discovery",
            "source_id": str(host_data.get("id")),
            "scan_metadata": host_data.get("scan_metadata", {}),
            "service_banners": host_data.get("service_banners"),
            "last_seen_at": datetime.utcnow().isoformat(),
        }

        # Generate content hash
        content_hash = self.embedder.generate_content_hash(content)

        return {
            "document_id": f"discovery_host_{host_data.get('id')}",
            "document_type": "infrastructure",
            "source_id": str(host_data.get("id")),
            "source_type": "discovery",
            "title": f"Discovered Host: {host_data.get('ip_address')}",
            "content": content,
            "content_hash": content_hash,
            "metadata": metadata,
        }

    async def transform_k8s_pod(self, pod_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform K8s pod into RAG document.

        Args:
            pod_data: Pod resource data

        Returns:
            RAG document dict
        """
        # Build document content
        content_parts = [
            f"Pod: {pod_data.get('name')}",
            f"Namespace: {pod_data.get('namespace')}",
            f"Status: {pod_data.get('status')}",
        ]

        if pod_data.get("node_name"):
            content_parts.append(f"Node: {pod_data['node_name']}")

        if pod_data.get("images"):
            content_parts.append(f"Images: {', '.join(pod_data['images'])}")

        if pod_data.get("labels"):
            labels_str = ", ".join(
                f"{k}={v}" for k, v in pod_data["labels"].items())
            content_parts.append(f"Labels: {labels_str}")

        if pod_data.get("containers"):
            container_names = [c.get("name") for c in pod_data["containers"]]
            content_parts.append(f"Containers: {', '.join(container_names)}")

        content = "\n".join(content_parts)

        # Build metadata
        metadata = {
            "resource_type": "k8s_pod",
            "resource_name": pod_data.get("name"),
            "namespace": pod_data.get("namespace"),
            "cluster_id": pod_data.get("cluster_id"),
            "status": pod_data.get("status"),
            "images": pod_data.get("images", []),
            "labels": pod_data.get("labels", {}),
            "last_seen_at": datetime.utcnow().isoformat(),
        }

        content_hash = self.embedder.generate_content_hash(content)

        return {
            "document_id": f"k8s_pod_{pod_data.get('cluster_id')}_{pod_data.get('namespace')}_{pod_data.get('name')}",
            "document_type": "k8s_resource",
            "source_id": pod_data.get("uid") or pod_data.get("name"),
            "source_type": "k8s",
            "title": f"K8s Pod: {pod_data.get('namespace')}/{pod_data.get('name')}",
            "content": content,
            "content_hash": content_hash,
            "metadata": metadata,
        }

    async def transform_k8s_deployment(
        self,
        deployment_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Transform K8s deployment into RAG document.

        Args:
            deployment_data: Deployment resource data

        Returns:
            RAG document dict
        """
        content_parts = [
            f"Deployment: {deployment_data.get('name')}",
            f"Namespace: {deployment_data.get('namespace')}",
            f"Replicas: {deployment_data.get('ready_replicas', 0)}/{deployment_data.get('replicas', 0)}",
            f"Strategy: {deployment_data.get('strategy_type', 'RollingUpdate')}",
        ]

        if deployment_data.get("selector_match_labels"):
            labels_str = ", ".join(
                f"{k}={v}"
                for k, v in deployment_data["selector_match_labels"].items()
            )
            content_parts.append(f"Selector: {labels_str}")

        content = "\n".join(content_parts)

        metadata = {
            "resource_type": "k8s_deployment",
            "resource_name": deployment_data.get("name"),
            "namespace": deployment_data.get("namespace"),
            "cluster_id": deployment_data.get("cluster_id"),
            "replicas": deployment_data.get("replicas"),
            "ready_replicas": deployment_data.get("ready_replicas"),
            "strategy_type": deployment_data.get("strategy_type"),
            "last_seen_at": datetime.utcnow().isoformat(),
        }

        content_hash = self.embedder.generate_content_hash(content)

        return {
            "document_id": f"k8s_deployment_{deployment_data.get('cluster_id')}_{deployment_data.get('namespace')}_{deployment_data.get('name')}",
            "document_type": "k8s_resource",
            "source_id": deployment_data.get("uid") or deployment_data.get("name"),
            "source_type": "k8s",
            "title": f"K8s Deployment: {deployment_data.get('namespace')}/{deployment_data.get('name')}",
            "content": content,
            "content_hash": content_hash,
            "metadata": metadata,
        }

    async def transform_k8s_service(
        self,
        service_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Transform K8s service into RAG document.

        Args:
            service_data: Service resource data

        Returns:
            RAG document dict
        """
        content_parts = [
            f"Service: {service_data.get('name')}",
            f"Namespace: {service_data.get('namespace')}",
            f"Type: {service_data.get('type')}",
        ]

        if service_data.get("cluster_ip"):
            content_parts.append(f"Cluster IP: {service_data['cluster_ip']}")

        if service_data.get("ports"):
            port_strs = []
            for p in service_data["ports"]:
                port_str = f"{p.get('port')}"
                if p.get("targetPort"):
                    port_str += f":{p.get('targetPort')}"
                if p.get("protocol"):
                    port_str += f"/{p.get('protocol')}"
                port_strs.append(port_str)
            content_parts.append(f"Ports: {', '.join(port_strs)}")

        if service_data.get("selector"):
            selector_str = ", ".join(
                f"{k}={v}" for k, v in service_data["selector"].items())
            content_parts.append(f"Selector: {selector_str}")

        content = "\n".join(content_parts)

        metadata = {
            "resource_type": "k8s_service",
            "resource_name": service_data.get("name"),
            "namespace": service_data.get("namespace"),
            "cluster_id": service_data.get("cluster_id"),
            "service_type": service_data.get("type"),
            "last_seen_at": datetime.utcnow().isoformat(),
        }

        content_hash = self.embedder.generate_content_hash(content)

        return {
            "document_id": f"k8s_service_{service_data.get('cluster_id')}_{service_data.get('namespace')}_{service_data.get('name')}",
            "document_type": "k8s_resource",
            "source_id": service_data.get("uid") or service_data.get("name"),
            "source_type": "k8s",
            "title": f"K8s Service: {service_data.get('namespace')}/{service_data.get('name')}",
            "content": content,
            "content_hash": content_hash,
            "metadata": metadata,
        }

    async def index_document(
        self,
        document: Dict[str, Any],
        db_session: AsyncSession,
    ) -> bool:
        """Index a document into the vector store.

        Args:
            document: Document to index
            db_session: Database session

        Returns:
            True if indexed successfully
        """
        try:
            # Get collection for document type
            collection = self.indexer.get_collection_for_document_type(
                document.get("document_type", "infrastructure")
            )

            # Generate embedding
            text = self.embedder.create_document_text(
                title=document.get("title"),
                content=document["content"],
                metadata=document.get("metadata", {}),
            )

            vector = self.embedder.generate_embedding(text)

            # Index in Qdrant
            await self.indexer.index_document(
                collection_name=collection,
                document_id=document["document_id"],
                vector=vector,
                payload={
                    "document_id": document["document_id"],
                    "document_type": document.get("document_type"),
                    "source_id": document.get("source_id"),
                    "source_type": document.get("source_type"),
                    "title": document.get("title"),
                    "content": document["content"],
                    "content_hash": document.get("content_hash"),
                    "metadata": document.get("metadata", {}),
                    "indexed_at": datetime.utcnow().isoformat(),
                },
            )

            # Update document tracking in database
            rag_doc = RAGDocument(
                document_id=document["document_id"],
                document_type=document.get("document_type", "infrastructure"),
                source_id=document.get("source_id"),
                source_type=document.get("source_type"),
                title=document.get("title"),
                content_hash=document.get("content_hash"),
                metadata=document.get("metadata", {}),
                is_indexed=True,
                indexed_at=datetime.utcnow(),
                last_seen_at=datetime.utcnow(),
            )

            db_session.add(rag_doc)
            await db_session.commit()

            logger.info(
                "document_indexed",
                document_id=document["document_id"],
                collection=collection,
            )

            return True

        except Exception as e:
            logger.error(
                "document_indexing_failed",
                error=str(e),
                document_id=document.get("document_id"),
            )

            # Track failed document
            rag_doc = RAGDocument(
                document_id=document.get("document_id", str(uuid.uuid4())),
                document_type=document.get("document_type", "infrastructure"),
                source_id=document.get("source_id"),
                source_type=document.get("source_type"),
                title=document.get("title"),
                content_hash=document.get("content_hash"),
                is_indexed=False,
                indexing_error=str(e),
            )
            db_session.add(rag_doc)
            await db_session.commit()

            return False

    async def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        document_types: Optional[List[str]] = None,
        namespaces: Optional[List[str]] = None,
        cluster_ids: Optional[List[str]] = None,
        min_score: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Perform RAG search across collections.

        Args:
            query: Search query
            top_k: Number of results
            document_types: Filter by document types
            namespaces: Filter by namespaces
            cluster_ids: Filter by cluster IDs
            min_score: Minimum similarity score

        Returns:
            List of search results
        """
        k = top_k or self.rag_top_k

        # Generate query embedding
        query_vector = self.embedder.generate_embedding(query)

        # Determine which collections to search
        collections = []
        if not document_types or "infrastructure" in document_types:
            collections.append(self.indexer.collection_infrastructure)
        if not document_types or "log" in document_types:
            collections.append(self.indexer.collection_logs)
        if not document_types or "doc" in document_types:
            collections.append(self.indexer.collection_docs)
        if not document_types or "k8s_resource" in document_types:
            collections.append(self.indexer.collection_k8s_resources)

        # Build filter conditions
        filter_conditions = []
        if namespaces:
            filter_conditions.append(
                {"field": "metadata.namespace", "match": {"any": namespaces}})
        if cluster_ids:
            filter_conditions.append(
                {"field": "metadata.cluster_id", "match": {"any": cluster_ids}})

        all_results = []

        for collection in collections:
            try:
                results = await self.indexer.search(
                    collection_name=collection,
                    query_vector=query_vector,
                    top_k=k,
                    filter_conditions={
                        "must": filter_conditions} if filter_conditions else None,
                    score_threshold=max(
                        min_score, self.rag_similarity_threshold),
                )
                all_results.extend(results)
            except Exception as e:
                logger.warning(
                    "collection_search_failed",
                    collection=collection,
                    error=str(e),
                )

        # Sort by score and limit
        all_results.sort(key=lambda x: x["score"], reverse=True)
        return all_results[:k]


# Singleton instance
_rag_pipeline: Optional[RAGPipeline] = None


def get_pipeline() -> RAGPipeline:
    """Get the singleton RAG pipeline instance."""
    global _rag_pipeline
    if _rag_pipeline is None:
        _rag_pipeline = RAGPipeline()
    return _rag_pipeline
