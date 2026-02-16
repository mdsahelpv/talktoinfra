"""
Proactive Insights Service.

AI-powered trend analysis and health scoring:
- Trend analysis predictions
- Health scoring per cluster
- Proactive issue detection
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import structlog

from app.config import get_settings
from app.models_self_healing import (
    ProactiveInsight,
    ClusterHealthScore,
)

logger = structlog.get_logger()


class ProactiveInsightsService:
    """Service for proactive AI-powered insights."""

    def __init__(self):
        """Initialize the proactive insights service."""
        self.settings = get_settings()

    async def analyze_cluster_health(
        self,
        cluster_id: str,
    ) -> Dict[str, Any]:
        """Analyze cluster health and generate insights.

        Args:
            cluster_id: The cluster to analyze

        Returns:
            Health analysis results
        """
        logger.info("analyzing_cluster_health", cluster_id=cluster_id)

        # Get recent metrics for the cluster
        metrics = await self._get_cluster_metrics(cluster_id)

        if not metrics:
            return {
                "cluster_id": cluster_id,
                "status": "no_data",
                "message": "No metrics available for analysis",
            }

        # Calculate health scores
        health_scores = await self._calculate_health_scores(cluster_id, metrics)

        # Generate insights
        insights = await self._generate_insights(cluster_id, metrics, health_scores)

        return {
            "cluster_id": cluster_id,
            "health_scores": health_scores,
            "insights": insights,
            "analyzed_at": datetime.utcnow().isoformat(),
        }

    async def _get_cluster_metrics(
        self,
        cluster_id: str,
    ) -> Dict[str, Any]:
        """Get recent metrics for a cluster.

        Args:
            cluster_id: The cluster ID

        Returns:
            Cluster metrics
        """
        # Query metrics from database or metrics service
        # For now, return placeholder
        return {
            "cpu_usage": [],
            "memory_usage": [],
            "pod_count": [],
            "node_count": [],
        }

    async def _calculate_health_scores(
        self,
        cluster_id: str,
        metrics: Dict[str, Any],
    ) -> Dict[str, float]:
        """Calculate health scores for a cluster.

        Args:
            cluster_id: The cluster ID
            metrics: Cluster metrics

        Returns:
            Health scores
        """
        # Calculate scores based on metrics
        # Each score is 0-100

        cpu_usage = metrics.get("cpu_usage", [])
        memory_usage = metrics.get("memory_usage", [])

        # CPU score (inverse of average usage)
        cpu_score = 100.0
        if cpu_usage:
            avg_cpu = sum(cpu_usage) / len(cpu_usage)
            cpu_score = max(0, 100 - avg_cpu)

        # Memory score
        memory_score = 100.0
        if memory_usage:
            avg_memory = sum(memory_usage) / len(memory_usage)
            memory_score = max(0, 100 - avg_memory)

        # Availability score (based on pod count stability)
        pod_count = metrics.get("pod_count", [])
        availability_score = 100.0
        if pod_count:
            # Check for pod failures
            avg_pods = sum(pod_count) / len(pod_count)
            min_pods = min(pod_count) if pod_count else 0
            if avg_pods > 0:
                availability_score = (min_pods / avg_pods) * 100

        # Capacity score (based on node count)
        node_count = metrics.get("node_count", [])
        capacity_score = 100.0
        if node_count and max(node_count, default=0) > 0:
            # Assume 80% utilization is optimal
            capacity_score = 80.0

        # Reliability score (based on error rates)
        reliability_score = 100.0  # Would calculate from error metrics

        # Overall score (weighted average)
        overall_score = (
            cpu_score * 0.25 +
            memory_score * 0.25 +
            availability_score * 0.20 +
            capacity_score * 0.15 +
            reliability_score * 0.15
        )

        return {
            "overall": round(overall_score, 2),
            "cpu": round(cpu_score, 2),
            "memory": round(memory_score, 2),
            "availability": round(availability_score, 2),
            "capacity": round(capacity_score, 2),
            "reliability": round(reliability_score, 2),
        }

    async def _generate_insights(
        self,
        cluster_id: str,
        metrics: Dict[str, Any],
        health_scores: Dict[str, float],
    ) -> List[Dict[str, Any]]:
        """Generate proactive insights.

        Args:
            cluster_id: The cluster ID
            metrics: Cluster metrics
            health_scores: Calculated health scores

        Returns:
            List of insights
        """
        insights = []

        # Check CPU trends
        if health_scores.get("cpu", 100) < 50:
            insights.append({
                "type": "resource",
                "severity": "critical",
                "title": "High CPU Usage",
                "description": f"CPU usage is at {100 - health_scores['cpu']:.1f}%, "
                "which may impact application performance.",
                "recommendation": "Consider scaling horizontally or optimizing workloads.",
            })

        # Check memory trends
        if health_scores.get("memory", 100) < 50:
            insights.append({
                "type": "resource",
                "severity": "critical",
                "title": "High Memory Usage",
                "description": f"Memory usage is at {100 - health_scores['memory']:.1f}%.",
                "recommendation": "Consider increasing memory limits or scaling.",
            })

        # Check availability
        if health_scores.get("availability", 100) < 90:
            insights.append({
                "type": "reliability",
                "severity": "warning",
                "title": "Pod Stability Issues",
                "description": "Pod count fluctuation detected, indicating potential "
                "stability issues.",
                "recommendation": "Review pod crash logs and resource limits.",
            })

        # Predictive insights (based on trends)
        cpu_trend = self._calculate_trend(metrics.get("cpu_usage", []))
        if cpu_trend == "increasing":
            insights.append({
                "type": "prediction",
                "severity": "warning",
                "title": "CPU Usage Trending Up",
                "description": "CPU usage has been consistently increasing over the "
                "past hour.",
                "recommendation": "Plan for scaling or resource increase.",
            })

        return insights

    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction from values.

        Args:
            values: List of metric values

        Returns:
            Trend: increasing, stable, or decreasing
        """
        if len(values) < 3:
            return "stable"

        # Compare recent average to older average
        recent = values[-3:]
        older = values[:3]

        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)

        if older_avg > 0:
            change_percent = ((recent_avg - older_avg) / older_avg) * 100

            if change_percent > 10:
                return "increasing"
            elif change_percent < -10:
                return "decreasing"

        return "stable"

    async def get_trend_predictions(
        self,
        cluster_id: str,
        metric_name: str,
        hours_ahead: int = 24,
    ) -> Dict[str, Any]:
        """Get trend predictions for a metric.

        Args:
            cluster_id: The cluster ID
            metric_name: The metric name
            hours_ahead: Hours to predict ahead

        Returns:
            Prediction data
        """
        logger.info(
            "generating_prediction",
            cluster_id=cluster_id,
            metric=metric_name,
            hours_ahead=hours_ahead,
        )

        # Get historical data
        historical = await self._get_historical_data(cluster_id, metric_name)

        if not historical:
            return {
                "metric": metric_name,
                "prediction": None,
                "message": "Insufficient data for prediction",
            }

        # Simple linear regression for trend
        trend = self._calculate_trend(historical)

        # Calculate predicted values
        recent_avg = sum(historical[-10:]) / min(10, len(historical))

        # Project forward
        if trend == "increasing":
            predicted = recent_avg * 1.2  # 20% increase
        elif trend == "decreasing":
            predicted = recent_avg * 0.8  # 20% decrease
        else:
            predicted = recent_avg

        return {
            "metric": metric_name,
            "cluster_id": cluster_id,
            "current_value": recent_avg,
            "predicted_value": round(predicted, 2),
            "trend": trend,
            "confidence": 0.75 if len(historical) > 20 else 0.5,
            "hours_ahead": hours_ahead,
        }

    async def _get_historical_data(
        self,
        cluster_id: str,
        metric_name: str,
    ) -> List[float]:
        """Get historical data for a metric.

        Args:
            cluster_id: The cluster ID
            metric_name: The metric name

        Returns:
            Historical values
        """
        # Query from metrics table
        # For now, return placeholder
        return []

    async def generate_daily_report(
        self,
    ) -> Dict[str, Any]:
        """Generate daily health and insights report for all clusters.

        Returns:
            Daily report
        """
        logger.info("generating_daily_report")

        # Get all clusters
        clusters = await self._get_all_clusters()

        cluster_reports = []
        for cluster in clusters:
            health_analysis = await self.analyze_cluster_health(cluster["id"])
            cluster_reports.append(health_analysis)

        return {
            "generated_at": datetime.utcnow().isoformat(),
            "clusters": cluster_reports,
            "summary": {
                "total_clusters": len(cluster_reports),
                "healthy_clusters": sum(
                    1 for r in cluster_reports
                    if r.get("health_scores", {}).get("overall", 0) >= 80
                ),
                "warning_clusters": sum(
                    1 for r in cluster_reports
                    if 50 <= r.get("health_scores", {}).get("overall", 0) < 80
                ),
                "critical_clusters": sum(
                    1 for r in cluster_reports
                    if r.get("health_scores", {}).get("overall", 0) < 50
                ),
            },
        }

    async def _get_all_clusters(self) -> List[Dict[str, Any]]:
        """Get all monitored clusters.

        Returns:
            List of clusters
        """
        # Query from cluster health table
        return []


# Singleton instance
_proactive_insights_service: Optional[ProactiveInsightsService] = None


def get_proactive_insights_service() -> ProactiveInsightsService:
    """Get the proactive insights service singleton."""
    global _proactive_insights_service
    if _proactive_insights_service is None:
        _proactive_insights_service = ProactiveInsightsService()
    return _proactive_insights_service
