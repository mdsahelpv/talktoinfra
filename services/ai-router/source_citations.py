"""
Source Citations Module - Prevents AI Hallucinations

Every AI answer must include source citations that:
- Link to the original data source
- Show confidence scores
- Display retrieval timestamps
- Allow users to verify information
"""

import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import structlog

logger = structlog.get_logger()


@dataclass
class SourceCitation:
    """Represents a single source citation for AI responses."""

    id: str
    # "discovered_host", "k8s_pod", "k8s_deployment", "aws_instance", etc.
    type: str
    name: str
    description: str
    retrieved_at: str = field(
        default_factory=lambda: datetime.utcnow().isoformat())
    confidence: float = 0.0
    score: float = 0.0  # Vector search score
    source: str = ""  # "discovery_scan", "k8s_watcher", "cloud_api"
    source_id: str = ""  # Original ID in source system
    raw_data: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "description": self.description,
            "retrieved_at": self.retrieved_at,
            "confidence": self.confidence,
            "score": self.score,
            "source": self.source,
            "source_id": self.source_id,
            "raw_data": self.raw_data,
            "metadata": self.metadata,
        }

    @classmethod
    def from_rag_result(cls, doc: Dict[str, Any]) -> "SourceCitation":
        """Create citation from RAG retrieval result."""
        payload = doc.get("payload", {})
        return cls(
            id=doc.get("id", ""),
            type=payload.get("resource_type", "unknown"),
            name=payload.get("name", payload.get("hostname", "Unknown")),
            description=payload.get("description", ""),
            confidence=doc.get("score", 0.0),
            score=doc.get("score", 0.0),
            source=payload.get("source", "unknown"),
            source_id=payload.get("source_id", ""),
            raw_data=payload.get("structured_data"),
            metadata={
                "discovered_at": payload.get("discovered_at"),
                "last_seen_at": payload.get("last_seen_at"),
                "scan_job_id": payload.get("scan_job_id"),
            },
        )


@dataclass
class CitationSet:
    """A set of source citations for a single response."""

    sources: List[SourceCitation] = field(default_factory=list)
    query_time_ms: float = 0.0
    retrieved_count: int = 0

    def add_source(self, source: SourceCitation) -> None:
        """Add a source to the citation set."""
        self.sources.append(source)
        self.retrieved_count = len(self.sources)

    def add_sources(self, sources: List[SourceCitation]) -> None:
        """Add multiple sources."""
        self.sources.extend(sources)
        self.retrieved_count = len(self.sources)

    def get_high_confidence_sources(self, threshold: float = 0.7) -> List[SourceCitation]:
        """Get sources above confidence threshold."""
        return [s for s in self.sources if s.confidence >= threshold]

    def get_sources_by_type(self, source_type: str) -> List[SourceCitation]:
        """Get sources filtered by type."""
        return [s for s in self.sources if s.type == source_type]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "sources": [s.to_dict() for s in self.sources],
            "retrieved_count": self.retrieved_count,
            "query_time_ms": self.query_time_ms,
        }


class CitationFormatter:
    """Formats citations for display in AI responses."""

    @staticmethod
    def format_citation_text(citation: SourceCitation) -> str:
        """Format a single citation for display."""
        confidence_indicator = CitationFormatter._get_confidence_indicator(
            citation.confidence)
        return f"[{confidence_indicator}] {citation.name} ({citation.type}): {citation.description}"

    @staticmethod
    def format_citations_for_response(citations: List[SourceCitation]) -> str:
        """Format all citations for inclusion in AI response."""
        if not citations:
            return "\n\n**Sources:** No sources retrieved."

        lines = ["\n\n**Sources:**"]
        for i, citation in enumerate(citations, 1):
            confidence = CitationFormatter._get_confidence_indicator(
                citation.confidence)
            source_label = CitationFormatter._get_source_label(citation.source)
            lines.append(
                f"{i}. {confidence} **{citation.name}** ({citation.type}) - {citation.description}"
            )
            if citation.source_id:
                lines[-1] += f" [{source_label}]"

        lines.append(
            f"\n*Retrieved {len(citations)} sources at {datetime.utcnow().isoformat()}*")
        return "\n".join(lines)

    @staticmethod
    def _get_confidence_indicator(confidence: float) -> str:
        """Get confidence indicator emoji."""
        if confidence >= 0.9:
            return "✅"
        elif confidence >= 0.7:
            return "✓"
        elif confidence >= 0.5:
            return "○"
        else:
            return "?"

    @staticmethod
    def _get_source_label(source: str) -> str:
        """Get human-readable source label."""
        labels = {
            "discovery_scan": "Discovery Scan",
            "k8s_watcher": "Kubernetes",
            "cloud_api": "Cloud API",
            "manual_entry": "Manual Entry",
        }
        return labels.get(source, source.replace("_", " ").title())

    @staticmethod
    def format_ui_card(citation: SourceCitation) -> Dict[str, Any]:
        """Format citation for UI display card."""
        return {
            "id": citation.id,
            "icon": CitationFormatter._get_type_icon(citation.type),
            "name": citation.name,
            "type": citation.type,
            "description": citation.description,
            "confidence": citation.confidence,
            "confidence_label": CitationFormatter._get_confidence_label(citation.confidence),
            "source": citation.source,
            "retrieved_at": citation.retrieved_at,
            "metadata": citation.metadata,
        }

    @staticmethod
    def _get_type_icon(resource_type: str) -> str:
        """Get icon for resource type."""
        icons = {
            "discovered_host": "🖥️",
            "k8s_pod": "📦",
            "k8s_deployment": "🚀",
            "k8s_service": "🌐",
            "k8s_node": "🧠",
            "k8s_namespace": "📁",
            "aws_instance": "☁️",
            "aws_rds": "🗄️",
            "azure_vm": "☁️",
            "gcp_instance": "☁️",
        }
        return icons.get(resource_type, "📄")

    @staticmethod
    def _get_confidence_label(confidence: float) -> str:
        """Get human-readable confidence label."""
        if confidence >= 0.9:
            return "High"
        elif confidence >= 0.7:
            return "Medium"
        elif confidence >= 0.5:
            return "Low"
        else:
            return "Uncertain"


class SourceCitationEngine:
    """Engine for managing source citations in AI responses."""

    def __init__(self, confidence_threshold: float = 0.5):
        """Initialize citation engine.

        Args:
            confidence_threshold: Minimum confidence for including sources
        """
        self.confidence_threshold = confidence_threshold

    async def create_citations_from_rag(
        self,
        rag_results: List[Dict[str, Any]],
        query_start_time: float,
    ) -> CitationSet:
        """Create citation set from RAG retrieval results.

        Args:
            rag_results: Results from RAG retrieval
            query_start_time: Timestamp when query started

        Returns:
            CitationSet with all sources
        """
        citations = CitationSet()
        citations.query_time_ms = (time.time() - query_start_time) * 1000

        for doc in rag_results:
            citation = SourceCitation.from_rag_result(doc)

            # Only include if above confidence threshold
            if citation.confidence >= self.confidence_threshold:
                citations.add_source(citation)

        logger.info(
            "citations_created",
            total_results=len(rag_results),
            included_sources=citations.retrieved_count,
            query_time_ms=citations.query_time_ms,
        )

        return citations

    def format_response_with_citations(
        self,
        response_text: str,
        citations: CitationSet,
        include_raw_data: bool = False,
    ) -> Dict[str, Any]:
        """Format the final response with citations.

        Args:
            response_text: The AI-generated response
            citations: CitationSet with sources
            include_raw_data: Whether to include raw data in response

        Returns:
            Formatted response with citations
        """
        # Format citations for display
        citation_text = CitationFormatter.format_citations_for_response(
            citations.sources)

        # Combine response with citations
        full_response = response_text + citation_text

        # Prepare sources for UI
        sources_for_ui = [
            CitationFormatter.format_ui_card(c) for c in citations.sources
        ]

        return {
            "response": full_response,
            "sources": sources_for_ui,
            "source_count": citations.retrieved_count,
            "query_time_ms": citations.query_time_ms,
            "confidence_distribution": self._get_confidence_distribution(citations),
        }

    def _get_confidence_distribution(self, citations: CitationSet) -> Dict[str, int]:
        """Get distribution of confidence levels."""
        distribution = {"high": 0, "medium": 0, "low": 0, "uncertain": 0}
        for c in citations.sources:
            if c.confidence >= 0.9:
                distribution["high"] += 1
            elif c.confidence >= 0.7:
                distribution["medium"] += 1
            elif c.confidence >= 0.5:
                distribution["low"] += 1
            else:
                distribution["uncertain"] += 1
        return distribution

    def check_hallucination_risk(
        self,
        citations: CitationSet,
        response_text: str,
    ) -> Dict[str, Any]:
        """Check if response might contain hallucinations.

        Args:
            citations: Citation set for the response
            response_text: The generated response

        Returns:
            Risk assessment dictionary
        """
        risk_factors = []
        risk_level = "low"

        # Check if no sources were retrieved
        if citations.retrieved_count == 0:
            risk_factors.append("No sources retrieved for response")
            risk_level = "high"

        # Check confidence levels
        high_conf_count = len(citations.get_high_confidence_sources(0.7))
        if citations.retrieved_count > 0 and high_conf_count == 0:
            risk_factors.append("All sources have low confidence")
            risk_level = "high"

        # Check for uncertainty markers in response
        uncertainty_markers = [
            "I think", "probably", "might be", "could be",
            "perhaps", "possibly", "I believe", "seems like",
        ]
        has_uncertainty = any(marker.lower() in response_text.lower()
                              for marker in uncertainty_markers)
        if has_uncertainty and citations.retrieved_count == 0:
            risk_factors.append("Response contains uncertainty but no sources")
            risk_level = "high"

        return {
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "source_count": citations.retrieved_count,
            "high_confidence_sources": high_conf_count,
        }
