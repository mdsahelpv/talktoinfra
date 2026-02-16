"""
Hierarchical RAG service for context window management.

This module implements a 3-level hierarchical RAG system:
- Level 1: Semantic search (vector similarity)
- Level 2: Structured query fallback
- Level 3: Hybrid RAG with structured data

The system automatically determines the best approach based on the query type.
"""

import hashlib
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import structlog

from config import get_settings

logger = structlog.get_logger()


class QueryClassifier:
    """Classifies queries to determine the best RAG strategy."""

    # Query patterns for different strategies
    LIST_PATTERNS = [
        r"^list\s+all\s+",
        r"^show\s+me\s+all\s+",
        r"^what\s+(servers|hosts|pods|services|deployments|nodes)\s+do\s+i\s+have",
        r"^get\s+all\s+",
        r"^find\s+all\s+",
    ]

    AGGREGATE_PATTERNS = [
        r"^how\s+many\s+",
        r"^count\s+",
        r"^total\s+",
        r"^sum\s+",
        r"^average\s+",
    ]

    DETAIL_PATTERNS = [
        r"^show\s+me\s+details?\s+(of|for)\s+",
        r"^what\s+is\s+(the\s+)?(status|config|info)\s+(of|for)\s+",
        r"^describe\s+",
    ]

    COMPARISON_PATTERNS = [
        r"^compare\s+",
        r"^difference\s+between\s+",
        r"^vs\.?\s+",
    ]

    def __init__(self):
        """Initialize the query classifier."""
        self._list_re = [re.compile(p, re.IGNORECASE)
                         for p in self.LIST_PATTERNS]
        self._aggregate_re = [
            re.compile(p, re.IGNORECASE) for p in self.AGGREGATE_PATTERNS
        ]
        self._detail_re = [re.compile(p, re.IGNORECASE)
                           for p in self.DETAIL_PATTERNS]
        self._comparison_re = [
            re.compile(p, re.IGNORECASE) for p in self.COMPARISON_PATTERNS
        ]

    def classify(self, query: str) -> str:
        """Classify a query to determine the best RAG strategy.

        Args:
            query: User query string

        Returns:
            Query type: "list", "aggregate", "detail", "comparison", "semantic"
        """
        query = query.strip()

        # Check for list patterns
        for pattern in self._list_re:
            if pattern.match(query):
                return "list"

        # Check for aggregate patterns
        for pattern in self._aggregate_re:
            if pattern.match(query):
                return "aggregate"

        # Check for detail patterns
        for pattern in self._detail_re:
            if pattern.match(query):
                return "detail"

        # Check for comparison patterns
        for pattern in self._comparison_re:
            if pattern.match(query):
                return "comparison"

        # Default to semantic search
        return "semantic"

    def extract_filters(self, query: str) -> Dict[str, Any]:
        """Extract filter criteria from query.

        Args:
            query: User query string

        Returns:
            Dictionary of extracted filters
        """
        filters = {}

        # Extract namespace
        namespace_match = re.search(
            r"in\s+(namespace|ns)\s+(\w+)", query, re.IGNORECASE
        )
        if namespace_match:
            filters["namespace"] = namespace_match.group(2)

        # Extract cluster
        cluster_match = re.search(
            r"in\s+(cluster|k8s)\s+(\w+)", query, re.IGNORECASE
        )
        if cluster_match:
            filters["cluster_id"] = cluster_match.group(2)

        # Extract status
        status_match = re.search(
            r"(status|state)\s+(is\s+)?(\w+)", query, re.IGNORECASE
        )
        if status_match:
            filters["status"] = status_match.group(3)

        # Extract labels
        label_matches = re.findall(
            r"label[sd]?\s+(\w+)\s*=\s*(\w+)", query, re.IGNORECASE
        )
        if label_matches:
            filters["labels"] = {k: v for k, v in label_matches}

        return filters


class ContextWindowManager:
    """Manages context window for LLM consumption."""

    # Token limits for different models
    MODEL_TOKEN_LIMITS = {
        "gpt-4": 8192,
        "gpt-4-turbo": 128000,
        "gpt-3.5-turbo": 16385,
        "claude-3-opus": 200000,
        "claude-3-sonnet": 200000,
        "claude-3-haiku": 200000,
        "default": 4096,
    }

    # Reserve tokens for system prompt and response
    RESERVED_TOKENS = 1000

    def __init__(self, model_name: str = "default"):
        """Initialize the context window manager.

        Args:
            model_name: Name of the LLM model
        """
        self.model_name = model_name
        self.max_tokens = self.MODEL_TOKEN_LIMITS.get(
            model_name, self.MODEL_TOKEN_LIMITS["default"]
        )
        self.available_tokens = self.max_tokens - self.RESERVED_TOKENS

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.

        Args:
            text: Input text

        Returns:
            Estimated token count
        """
        # Rough estimate: ~4 characters per token
        return len(text) // 4

    def fit_context(
        self,
        documents: List[Dict[str, Any]],
        query: str,
    ) -> Tuple[List[Dict[str, Any]], str]:
        """Fit documents into context window.

        Args:
            documents: List of documents with content and metadata
            query: Original query

        Returns:
            Tuple of (selected documents, context text)
        """
        # Calculate available tokens
        query_tokens = self.estimate_tokens(query)
        available = self.available_tokens - query_tokens

        # Sort documents by relevance score
        sorted_docs = sorted(
            documents, key=lambda x: x.get("score", 0.0), reverse=True
        )

        selected = []
        used_tokens = 0

        for doc in sorted_docs:
            content = doc.get("payload", {}).get("content", "")
            doc_tokens = self.estimate_tokens(content)

            if used_tokens + doc_tokens <= available:
                selected.append(doc)
                used_tokens += doc_tokens
            elif used_tokens < available:
                # Truncate content to fit
                remaining = available - used_tokens
                truncated_content = content[: remaining * 4]
                doc_copy = doc.copy()
                doc_copy["payload"] = doc["payload"].copy()
                doc_copy["payload"]["content"] = truncated_content + "..."
                doc_copy["truncated"] = True
                selected.append(doc_copy)
                break

        # Build context text
        context_parts = []
        for i, doc in enumerate(selected):
            content = doc.get("payload", {}).get("content", "")
            title = doc.get("payload", {}).get("title", "")
            source_type = doc.get("payload", {}).get("source_type", "unknown")
            source_id = doc.get("payload", {}).get("source_id", "")

            context_parts.append(
                f"[Source {i+1}] {title}\n"
                f"Type: {source_type} | ID: {source_id}\n"
                f"{content}"
            )

        context_text = "\n\n---\n\n".join(context_parts)

        logger.info(
            "context_window_fitted",
            total_docs=len(documents),
            selected_docs=len(selected),
            estimated_tokens=used_tokens,
        )

        return selected, context_text


class HierarchicalRAGService:
    """Implements hierarchical RAG with multiple levels of retrieval."""

    def __init__(
        self,
        pipeline=None,
        knowledge_graph=None,
    ):
        """Initialize the hierarchical RAG service.

        Args:
            pipeline: RAG pipeline instance
            knowledge_graph: Knowledge graph service instance
        """
        settings = get_settings()

        self.pipeline = pipeline
        self.knowledge_graph = knowledge_graph

        self.query_classifier = QueryClassifier()
        self.context_manager = ContextWindowManager()

        self.rag_similarity_threshold = settings.rag_similarity_threshold
        self.rag_top_k = settings.rag_top_k

    async def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        force_level: Optional[int] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Perform hierarchical RAG search.

        Args:
            query: User query
            top_k: Number of results
            force_level: Force a specific RAG level (1, 2, or 3)
            **kwargs: Additional search parameters

        Returns:
            Search results with level information
        """
        k = top_k or self.rag_top_k

        # Classify the query
        query_type = self.query_classifier.classify(query)
        filters = self.query_classifier.extract_filters(query)

        logger.info(
            "hierarchical_rag_search",
            query=query[:100],
            query_type=query_type,
            filters=filters,
            force_level=force_level,
        )

        # Determine which level to use
        if force_level:
            level = force_level
        elif query_type == "list":
            # Use Level 2/3 for list queries (structured fallback)
            level = 2
        elif query_type == "aggregate":
            # Use Level 3 for aggregate queries
            level = 3
        else:
            # Default to Level 1 (semantic search)
            level = 1

        # Execute search based on level
        if level == 1:
            return await self._level1_semantic_search(query, k, filters, **kwargs)
        elif level == 2:
            return await self._level2_structured_fallback(query, k, filters, **kwargs)
        elif level == 3:
            return await self._level3_hybrid_search(query, k, filters, **kwargs)
        else:
            # Fallback to Level 1
            return await self._level1_semantic_search(query, k, filters, **kwargs)

    async def _level1_semantic_search(
        self,
        query: str,
        top_k: int,
        filters: Dict[str, Any],
        **kwargs,
    ) -> Dict[str, Any]:
        """Level 1: Semantic search using vector similarity.

        Args:
            query: User query
            top_k: Number of results
            filters: Extracted filters

        Returns:
            Search results
        """
        if not self.pipeline:
            return {
                "level": 1,
                "query_type": "semantic",
                "results": [],
                "error": "Pipeline not available",
            }

        try:
            # Add extracted filters to search params
            search_kwargs = kwargs.copy()
            if filters.get("namespace"):
                search_kwargs["namespaces"] = [filters["namespace"]]
            if filters.get("cluster_id"):
                search_kwargs["cluster_ids"] = [filters["cluster_id"]]

            results = await self.pipeline.search(
                query=query,
                top_k=top_k,
                min_score=self.rag_similarity_threshold,
                **search_kwargs,
            )

            # Fit to context window
            selected, context_text = self.context_manager.fit_context(
                results, query
            )

            return {
                "level": 1,
                "query_type": "semantic",
                "results": selected,
                "total_results": len(results),
                "context_text": context_text,
                "strategy": "semantic_vector_search",
            }

        except Exception as e:
            logger.error("level1_search_failed", error=str(e))
            return {
                "level": 1,
                "query_type": "semantic",
                "results": [],
                "error": str(e),
            }

    async def _level2_structured_fallback(
        self,
        query: str,
        top_k: int,
        filters: Dict[str, Any],
        **kwargs,
    ) -> Dict[str, Any]:
        """Level 2: Structured query fallback for "list all" queries.

        Args:
            query: User query
            top_k: Number of results
            filters: Extracted filters

        Returns:
            Search results
        """
        # For list queries, we need to query the database directly
        # This is a placeholder - in production, this would query PostgreSQL
        logger.info(
            "level2_structured_fallback",
            query=query[:100],
            filters=filters,
        )

        # Try semantic search first with lower threshold
        if self.pipeline:
            try:
                results = await self.pipeline.search(
                    query=query,
                    top_k=top_k * 2,  # Get more results for list queries
                    min_score=0.3,  # Lower threshold for list queries
                    **kwargs,
                )

                # Fit to context window
                selected, context_text = self.context_manager.fit_context(
                    results, query
                )

                return {
                    "level": 2,
                    "query_type": "list",
                    "results": selected,
                    "total_results": len(results),
                    "context_text": context_text,
                    "strategy": "structured_fallback_with_semantic",
                }
            except Exception as e:
                logger.warning("level2_semantic_fallback_failed", error=str(e))

        return {
            "level": 2,
            "query_type": "list",
            "results": [],
            "context_text": "",
            "strategy": "structured_query",
            "note": "Structured query not implemented - using semantic fallback",
        }

    async def _level3_hybrid_search(
        self,
        query: str,
        top_k: int,
        filters: Dict[str, Any],
        **kwargs,
    ) -> Dict[str, Any]:
        """Level 3: Hybrid RAG combining semantic and structured queries.

        Args:
            query: User query
            top_k: Number of results
            filters: Extracted filters

        Returns:
            Search results
        """
        logger.info(
            "level3_hybrid_search",
            query=query[:100],
            filters=filters,
        )

        all_results = []

        # Level 1: Semantic search
        if self.pipeline:
            try:
                semantic_results = await self.pipeline.search(
                    query=query,
                    top_k=top_k,
                    min_score=self.rag_similarity_threshold,
                    **kwargs,
                )
                all_results.extend(semantic_results)
            except Exception as e:
                logger.warning("level3_semantic_failed", error=str(e))

        # Level 2: Knowledge graph traversal (if available)
        if self.knowledge_graph:
            try:
                # Extract entities from query
                # This is a simplified version
                graph_results = await self._search_knowledge_graph(
                    query, filters, top_k
                )
                all_results.extend(graph_results)
            except Exception as e:
                logger.warning("level3_graph_failed", error=str(e))

        # Deduplicate and rank results
        seen_ids = set()
        unique_results = []
        for result in all_results:
            doc_id = result.get("payload", {}).get("document_id", "")
            if doc_id not in seen_ids:
                seen_ids.add(doc_id)
                unique_results.append(result)

        # Sort by score
        unique_results.sort(key=lambda x: x.get("score", 0.0), reverse=True)

        # Limit to top_k
        final_results = unique_results[:top_k]

        # Fit to context window
        selected, context_text = self.context_manager.fit_context(
            final_results, query
        )

        return {
            "level": 3,
            "query_type": "hybrid",
            "results": selected,
            "total_results": len(unique_results),
            "context_text": context_text,
            "strategy": "hybrid_semantic_plus_graph",
        }

    async def _search_knowledge_graph(
        self,
        query: str,
        filters: Dict[str, Any],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """Search the knowledge graph for relevant entities.

        Args:
            query: User query
            filters: Extracted filters
            top_k: Number of results

        Returns:
            List of results from knowledge graph
        """
        # This would query the knowledge graph
        # For now, return empty list
        return []

    async def get_context_for_llm(
        self,
        query: str,
        top_k: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get formatted context for LLM consumption.

        Args:
            query: User query
            top_k: Number of results

        Returns:
            Context response with citations
        """
        result = await self.search(query, top_k=top_k)

        # Build citations
        citations = []
        for i, r in enumerate(result.get("results", [])):
            payload = r.get("payload", {})
            citations.append({
                "source_num": i + 1,
                "source_type": payload.get("source_type", "unknown"),
                "source_id": payload.get("source_id", ""),
                "title": payload.get("title", ""),
                "score": r.get("score", 0.0),
            })

        return {
            "query": query,
            "context_text": result.get("context_text", ""),
            "citations": citations,
            "level": result.get("level", 1),
            "strategy": result.get("strategy", "unknown"),
        }


# Singleton instance
_hierarchical_rag_service: Optional[HierarchicalRAGService] = None


def get_hierarchical_rag() -> HierarchicalRAGService:
    """Get the singleton hierarchical RAG service instance."""
    global _hierarchical_rag_service
    if _hierarchical_rag_service is None:
        _hierarchical_rag_service = HierarchicalRAGService()
    return _hierarchical_rag_service
