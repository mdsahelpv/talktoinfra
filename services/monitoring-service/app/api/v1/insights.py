"""
Proactive Insights API Endpoints.

REST API for cluster health analysis, trend predictions, and AI insights.
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.services.proactive_insights import get_proactive_insights_service

router = APIRouter()


# Response Schemas
class HealthScoreResponse(BaseModel):
    """Health score response."""
    overall: float
    cpu: float
    memory: float
    availability: float
    capacity: float
    reliability: float


class InsightResponse(BaseModel):
    """Insight response."""
    type: str
    severity: str
    title: str
    description: str
    recommendation: Optional[str] = None


class ClusterHealthResponse(BaseModel):
    """Cluster health analysis response."""
    cluster_id: str
    health_scores: HealthScoreResponse
    insights: List[InsightResponse]
    analyzed_at: str


class PredictionResponse(BaseModel):
    """Trend prediction response."""
    metric: str
    cluster_id: str
    current_value: float
    predicted_value: float
    trend: str
    confidence: float
    hours_ahead: int


class DailyReportResponse(BaseModel):
    """Daily report response."""
    generated_at: str
    clusters: List[dict]
    summary: dict


# API Endpoints
@router.get("/clusters/{cluster_id}/health", response_model=ClusterHealthResponse)
async def get_cluster_health(
    cluster_id: str,
) -> ClusterHealthResponse:
    """Get health analysis for a cluster.

    This endpoint analyzes cluster metrics and generates:
    - Health scores (0-100) for various dimensions
    - Proactive insights and recommendations

    Args:
        cluster_id: The cluster ID

    Returns:
        Health analysis with scores and insights
    """
    service = get_proactive_insights_service()
    result = await service.analyze_cluster_health(cluster_id)

    if result.get("status") == "no_data":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No metrics available for cluster {cluster_id}",
        )

    return ClusterHealthResponse(
        cluster_id=result["cluster_id"],
        health_scores=HealthScoreResponse(**result["health_scores"]),
        insights=[InsightResponse(**i) for i in result.get("insights", [])],
        analyzed_at=result["analyzed_at"],
    )


@router.get("/clusters/{cluster_id}/predictions/{metric}")
async def get_metric_predictions(
    cluster_id: str,
    metric: str,
    hours_ahead: int = 24,
) -> PredictionResponse:
    """Get trend predictions for a metric.

    This endpoint analyzes historical metric data and predicts
    future values using simple trend analysis.

    Args:
        cluster_id: The cluster ID
        metric: The metric name (e.g., cpu_usage, memory_usage)
        hours_ahead: Number of hours to predict ahead

    Returns:
        Prediction with trend and confidence
    """
    service = get_proactive_insights_service()
    result = await service.get_trend_predictions(
        cluster_id=cluster_id,
        metric_name=metric,
        hours_ahead=hours_ahead,
    )

    if result.get("prediction") is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Insufficient data for predicting {metric}",
        )

    return PredictionResponse(**result)


@router.get("/clusters/{cluster_id}/insights")
async def get_cluster_insights(
    cluster_id: str,
    severity: Optional[str] = None,
    status: Optional[str] = None,
) -> List[InsightResponse]:
    """Get active insights for a cluster.

    Args:
        cluster_id: The cluster ID
        severity: Filter by severity (info, warning, critical)
        status: Filter by status (active, acknowledged, resolved)

    Returns:
        List of insights
    """
    # Would query from database
    return []


@router.post("/clusters/{cluster_id}/insights/{insight_id}/acknowledge")
async def acknowledge_insight(
    cluster_id: str,
    insight_id: int,
    acknowledged_by: str,
) -> dict:
    """Acknowledge an insight.

    Args:
        cluster_id: The cluster ID
        insight_id: Insight ID
        acknowledged_by: User acknowledging

    Returns:
        Acknowledgment confirmation
    """
    # Would update in database
    return {
        "insight_id": insight_id,
        "status": "acknowledged",
        "acknowledged_by": acknowledged_by,
        "acknowledged_at": "2026-02-16T12:00:00Z",
    }


@router.post("/clusters/{cluster_id}/insights/{insight_id}/resolve")
async def resolve_insight(
    cluster_id: str,
    insight_id: int,
    resolved_by: str,
    resolution: str,
) -> dict:
    """Resolve an insight.

    Args:
        cluster_id: The cluster ID
        insight_id: Insight ID
        resolved_by: User resolving
        resolution: Resolution description

    Returns:
        Resolution confirmation
    """
    # Would update in database
    return {
        "insight_id": insight_id,
        "status": "resolved",
        "resolved_by": resolved_by,
        "resolution": resolution,
        "resolved_at": "2026-02-16T12:00:00Z",
    }


@router.get("/report/daily", response_model=DailyReportResponse)
async def get_daily_report() -> DailyReportResponse:
    """Get daily health and insights report.

    This endpoint generates a comprehensive daily report for
    all monitored clusters including health scores and insights.

    Returns:
        Daily report with cluster summaries
    """
    service = get_proactive_insights_service()
    result = await service.generate_daily_report()

    return DailyReportResponse(**result)


@router.get("/trends/{cluster_id}")
async def get_cluster_trends(
    cluster_id: str,
    metrics: Optional[str] = None,
) -> dict:
    """Get trend analysis for cluster metrics.

    Args:
        cluster_id: The cluster ID
        metrics: Comma-separated list of metrics (default: cpu,memory,disk)

    Returns:
        Trend analysis for each metric
    """
    if metrics is None:
        metrics_list = ["cpu_usage", "memory_usage", "pod_count"]
    else:
        metrics_list = metrics.split(",")

    service = get_proactive_insights_service()
    trends = {}

    for metric in metrics_list:
        prediction = await service.get_trend_predictions(
            cluster_id=cluster_id,
            metric_name=metric.strip(),
            hours_ahead=24,
        )
        if prediction.get("prediction") is not None:
            trends[metric] = {
                "trend": prediction["trend"],
                "current": prediction["current_value"],
                "predicted": prediction["predicted_value"],
                "confidence": prediction["confidence"],
            }

    return {
        "cluster_id": cluster_id,
        "trends": trends,
        "analyzed_at": "2026-02-16T12:00:00Z",
    }
