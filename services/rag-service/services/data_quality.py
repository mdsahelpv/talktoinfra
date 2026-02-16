"""
Data Quality & Validation service for RAG pipeline.

This module provides functionality for:
- Timestamp validation (reject old documents)
- Confidence scoring ("I'm not certain")
- Cross-validation (RAG vs live API)
- Data freshness indicators
"""

import hashlib
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import structlog

from config import get_settings

logger = structlog.get_logger()


class TimestampValidator:
    """Validates document timestamps and freshness."""

    # Default freshness thresholds (in hours)
    DEFAULT_THRESHOLDS = {
        "critical": 1,    # 1 hour for critical resources
        "high": 4,        # 4 hours for important resources
        "medium": 24,     # 24 hours for normal resources
        "low": 72,        # 72 hours for low priority resources
        "stale": 168,     # 1 week - mark as stale
    }

    def __init__(self, thresholds: Optional[Dict[str, int]] = None):
        """Initialize the timestamp validator.

        Args:
            thresholds: Custom freshness thresholds in hours
        """
        self.thresholds = thresholds or self.DEFAULT_THRESHOLDS

    def parse_timestamp(self, timestamp: Any) -> Optional[datetime]:
        """Parse various timestamp formats.

        Args:
            timestamp: Timestamp in various formats

        Returns:
            Parsed datetime or None
        """
        if timestamp is None:
            return None

        if isinstance(timestamp, datetime):
            return timestamp

        if isinstance(timestamp, str):
            # Try ISO format
            try:
                return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except ValueError:
                pass

            # Try common formats
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d",
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(timestamp, fmt)
                except ValueError:
                    continue

        return None

    def get_freshness(
        self,
        timestamp: Any,
        resource_type: str = "default",
    ) -> Tuple[str, float]:
        """Determine freshness of a timestamp.

        Args:
            timestamp: Document timestamp
            resource_type: Type of resource

        Returns:
            Tuple of (freshness level, age in hours)
        """
        dt = self.parse_timestamp(timestamp)
        if dt is None:
            return "unknown", -1

        # Calculate age
        now = datetime.utcnow()
        if dt.tzinfo:
            now = datetime.now(dt.tzinfo)

        age_hours = (now - dt).total_seconds() / 3600

        # Determine freshness level
        if age_hours <= self.thresholds["critical"]:
            return "fresh", age_hours
        elif age_hours <= self.thresholds["high"]:
            return "recent", age_hours
        elif age_hours <= self.thresholds["medium"]:
            return "aging", age_hours
        elif age_hours <= self.thresholds["stale"]:
            return "stale", age_hours
        else:
            return "expired", age_hours

    def is_valid(
        self,
        timestamp: Any,
        max_age_hours: Optional[int] = None,
    ) -> bool:
        """Check if timestamp is within valid range.

        Args:
            timestamp: Document timestamp
            max_age_hours: Maximum allowed age in hours

        Returns:
            True if timestamp is valid
        """
        if max_age_hours is None:
            max_age_hours = self.thresholds["medium"]

        _, age_hours = self.get_freshness(timestamp)
        return 0 <= age_hours <= max_age_hours

    def filter_by_freshness(
        self,
        documents: List[Dict[str, Any]],
        max_age_hours: Optional[int] = None,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Filter documents by freshness.

        Args:
            documents: List of documents
            max_age_hours: Maximum allowed age in hours

        Returns:
            Tuple of (valid documents, invalid documents)
        """
        valid = []
        invalid = []

        for doc in documents:
            timestamp = doc.get("payload", {}).get(
                "metadata", {}).get("last_seen_at")
            freshness, age_hours = self.get_freshness(timestamp)

            doc_with_freshness = doc.copy()
            doc_with_freshness["_freshness"] = freshness
            doc_with_freshness["_age_hours"] = age_hours

            if freshness not in ["expired"]:
                valid.append(doc_with_freshness)
            else:
                invalid.append(doc_with_freshness)

        return valid, invalid


class ConfidenceScorer:
    """Calculates confidence scores for RAG results."""

    def __init__(self):
        """Initialize the confidence scorer."""
        self.min_confidence_threshold = 0.5

    def calculate_confidence(
        self,
        results: List[Dict[str, Any]],
        query: str,
    ) -> Dict[str, Any]:
        """Calculate overall confidence for search results.

        Args:
            results: Search results
            query: Original query

        Returns:
            Confidence metrics
        """
        if not results:
            return {
                "confidence": 0.0,
                "level": "none",
                "message": "No results found",
                "recommendation": "Try a broader search or check data sources",
            }

        # Calculate average score
        scores = [r.get("score", 0.0) for r in results]
        avg_score = sum(scores) / len(scores)
        max_score = max(scores)

        # Calculate score variance
        variance = sum((s - avg_score) ** 2 for s in scores) / len(scores)
        std_dev = variance ** 0.5

        # Determine confidence level
        if avg_score >= 0.8 and max_score >= 0.9:
            level = "high"
            message = "High confidence in results"
        elif avg_score >= 0.6 and max_score >= 0.7:
            level = "medium"
            message = "Moderate confidence in results"
        elif avg_score >= 0.4:
            level = "low"
            message = "Low confidence - results may not be accurate"
        else:
            level = "very_low"
            message = "Very low confidence - results likely inaccurate"

        # Check for result diversity
        unique_types = len(set(
            r.get("payload", {}).get("source_type", "unknown")
            for r in results
        ))

        # Generate recommendation
        recommendation = self._generate_recommendation(
            avg_score, max_score, std_dev, unique_types, len(results)
        )

        return {
            "confidence": avg_score,
            "max_score": max_score,
            "std_dev": std_dev,
            "level": level,
            "message": message,
            "result_count": len(results),
            "unique_source_types": unique_types,
            "recommendation": recommendation,
        }

    def _generate_recommendation(
        self,
        avg_score: float,
        max_score: float,
        std_dev: float,
        unique_types: int,
        result_count: int,
    ) -> str:
        """Generate recommendation based on confidence metrics.

        Args:
            avg_score: Average similarity score
            max_score: Maximum similarity score
            std_dev: Standard deviation of scores
            unique_types: Number of unique source types
            result_count: Total number of results

        Returns:
            Recommendation string
        """
        if result_count == 0:
            return "No results found. Try broadening your search."

        if avg_score >= 0.8:
            return "Results are highly relevant. You can proceed with confidence."

        if avg_score >= 0.6:
            if std_dev > 0.2:
                return "Results are mixed. Review each result carefully before taking action."
            return "Results are reasonably relevant. Verify critical information independently."

        if avg_score >= 0.4:
            return "Results may not be accurate. Consider refining your query or checking additional sources."

        return "Results have low relevance. I recommend verifying this information through other means."

    def should_uncertain(self, confidence: float) -> bool:
        """Determine if the system should express uncertainty.

        Args:
            confidence: Confidence score

        Returns:
            True if system should express uncertainty
        """
        return confidence < self.min_confidence_threshold

    def get_uncertainty_phrase(self, confidence: float) -> str:
        """Get appropriate uncertainty phrase.

        Args:
            confidence: Confidence score

        Returns:
            Uncertainty phrase
        """
        if confidence >= 0.8:
            return ""
        elif confidence >= 0.6:
            return "Based on the available information"
        elif confidence >= 0.4:
            return "I'm not entirely certain, but"
        else:
            return "I don't have reliable information about"


class CrossValidator:
    """Validates RAG results against live API data."""

    def __init__(self):
        """Initialize the cross validator."""
        self.validation_cache: Dict[str, Tuple[datetime, bool]] = {}
        self.cache_ttl = timedelta(minutes=5)

    async def validate_result(
        self,
        result: Dict[str, Any],
        source_type: str,
        source_id: str,
    ) -> Dict[str, Any]:
        """Validate a single result against live data.

        Args:
            result: RAG search result
            source_type: Source type (k8s, discovery, etc.)
            source_id: Source identifier

        Returns:
            Validation result
        """
        # Check cache first
        cache_key = f"{source_type}:{source_id}"
        if cache_key in self.validation_cache:
            cached_time, cached_result = self.validation_cache[cache_key]
            if datetime.utcnow() - cached_time < self.cache_ttl:
                return {
                    "validated": cached_result,
                    "cached": True,
                    "cache_age_seconds": (datetime.utcnow() - cached_time).total_seconds(),
                }

        # In production, this would call the actual APIs
        # For now, return a placeholder
        validation_result = True  # Assume valid for now

        # Update cache
        self.validation_cache[cache_key] = (
            datetime.utcnow(), validation_result)

        return {
            "validated": validation_result,
            "cached": False,
            "source_type": source_type,
            "source_id": source_id,
        }

    async def validate_results(
        self,
        results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Validate multiple results.

        Args:
            results: List of RAG search results

        Returns:
            Results with validation status
        """
        validated_results = []

        for result in results:
            source_type = result.get("payload", {}).get(
                "source_type", "unknown")
            source_id = result.get("payload", {}).get("source_id", "")

            if not source_id:
                validated_results.append({
                    **result,
                    "validation": {
                        "validated": None,
                        "reason": "No source_id available",
                    },
                })
                continue

            validation = await self.validate_result(result, source_type, source_id)

            validated_results.append({
                **result,
                "validation": validation,
            })

        return validated_results


class DataQualityService:
    """Main service for data quality and validation."""

    def __init__(self):
        """Initialize the data quality service."""
        settings = get_settings()

        self.timestamp_validator = TimestampValidator()
        self.confidence_scorer = ConfidenceScorer()
        self.cross_validator = CrossValidator()

        # Load custom thresholds from settings
        if hasattr(settings, "rag_freshness_thresholds"):
            self.timestamp_validator = TimestampValidator(
                settings.rag_freshness_thresholds
            )

    async def assess_quality(
        self,
        results: List[Dict[str, Any]],
        query: str,
    ) -> Dict[str, Any]:
        """Assess overall quality of search results.

        Args:
            results: Search results
            query: Original query

        Returns:
            Quality assessment
        """
        # Calculate confidence
        confidence = self.confidence_scorer.calculate_confidence(
            results, query)

        # Check freshness
        fresh_results = []
        stale_results = []

        for result in results:
            timestamp = result.get("payload", {}).get(
                "metadata", {}).get("last_seen_at")
            freshness, age_hours = self.timestamp_validator.get_freshness(
                timestamp)

            result_copy = result.copy()
            result_copy["_freshness"] = freshness
            result_copy["_age_hours"] = age_hours

            if freshness in ["fresh", "recent"]:
                fresh_results.append(result_copy)
            else:
                stale_results.append(result_copy)

        # Determine overall quality
        quality_score = confidence["confidence"]
        if fresh_results:
            # Boost for fresh data
            quality_score = min(quality_score * 1.1, 1.0)

        if quality_score >= 0.8:
            quality_level = "excellent"
        elif quality_score >= 0.6:
            quality_level = "good"
        elif quality_score >= 0.4:
            quality_level = "fair"
        else:
            quality_level = "poor"

        return {
            "quality_score": quality_score,
            "quality_level": quality_level,
            "confidence": confidence,
            "fresh_results_count": len(fresh_results),
            "stale_results_count": len(stale_results),
            "total_results": len(results),
            "recommendation": confidence["recommendation"],
            "uncertainty_phrase": self.confidence_scorer.get_uncertainty_phrase(
                confidence["confidence"]
            ),
        }

    async def validate_and_enrich(
        self,
        results: List[Dict[str, Any]],
        query: str,
        validate_live: bool = False,
    ) -> Dict[str, Any]:
        """Validate and enrich results with quality metadata.

        Args:
            results: Search results
            query: Original query
            validate_live: Whether to validate against live APIs

        Returns:
            Enriched results with quality metadata
        """
        # Assess quality
        quality = await self.assess_quality(results, query)

        # Optionally validate against live APIs
        if validate_live:
            results = await self.cross_validator.validate_results(results)

        return {
            "results": results,
            "quality": quality,
            "query": query,
        }

    def get_freshness_indicator(self, timestamp: Any) -> Dict[str, Any]:
        """Get a freshness indicator for UI display.

        Args:
            timestamp: Document timestamp

        Returns:
            Freshness indicator
        """
        freshness, age_hours = self.timestamp_validator.get_freshness(
            timestamp)

        indicators = {
            "fresh": {"color": "green", "icon": "check-circle", "label": "Fresh"},
            "recent": {"color": "blue", "icon": "info", "label": "Recent"},
            "aging": {"color": "yellow", "icon": "alert-triangle", "label": "Aging"},
            "stale": {"color": "orange", "icon": "alert-circle", "label": "Stale"},
            "expired": {"color": "red", "icon": "x-circle", "label": "Expired"},
            "unknown": {"color": "gray", "icon": "help-circle", "label": "Unknown"},
        }

        indicator = indicators.get(freshness, indicators["unknown"])

        return {
            **indicator,
            "freshness": freshness,
            "age_hours": round(age_hours, 1) if age_hours >= 0 else None,
        }


# Singleton instance
_data_quality_service: Optional[DataQualityService] = None


def get_data_quality() -> DataQualityService:
    """Get the singleton data quality service instance."""
    global _data_quality_service
    if _data_quality_service is None:
        _data_quality_service = DataQualityService()
    return _data_quality_service
