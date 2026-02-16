"""
AWS CloudWatch tools for monitoring and logs.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError, BotoCoreError

import structlog

logger = structlog.get_logger()


def get_cloudwatch_client(region: str = "us-east-1") -> Any:
    """Get a CloudWatch client."""
    return boto3.client("cloudwatch", region_name=region)


def get_logs_client(region: str = "us-east-1") -> Any:
    """Get a CloudWatch Logs client."""
    return boto3.client("logs", region_name=region)


async def get_metric_data(
    namespace: str,
    metric_name: str,
    region: str = "us-east-1",
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    period: int = 300,
    statistics: List[str] = ["Average", "Maximum", "Minimum"],
    dimensions: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Get metric data from CloudWatch.

    Args:
        namespace: CloudWatch namespace (e.g., AWS/EC2, AWS/EKS)
        metric_name: Metric name (e.g., CPUUtilization)
        region: AWS region
        start_time: Start time for the query
        end_time: End time for the query
        period: Period in seconds
        statistics: List of statistics to retrieve
        dimensions: List of dimensions for the metric

    Returns:
        Dictionary with metric data or error information
    """
    try:
        cw = get_cloudwatch_client(region)

        if not start_time:
            start_time = datetime.now() - timedelta(hours=1)
        if not end_time:
            end_time = datetime.now()

        kwargs = {
            "Namespace": namespace,
            "MetricName": metric_name,
            "StartTime": start_time,
            "EndTime": end_time,
            "Period": period,
            "Statistics": statistics,
        }

        if dimensions:
            kwargs["Dimensions"] = dimensions

        response = cw.get_metric_statistics(**kwargs)

        datapoints = []
        for dp in response.get("Datapoints", []):
            datapoints.append({
                "timestamp": dp.get("Timestamp").isoformat() if dp.get("Timestamp") else None,
                "average": dp.get("Average"),
                "maximum": dp.get("Maximum"),
                "minimum": dp.get("Minimum"),
                "sample_count": dp.get("SampleCount"),
                "sum": dp.get("Sum"),
            })

        # Sort by timestamp
        datapoints.sort(key=lambda x: x["timestamp"] or "")

        return {
            "success": True,
            "namespace": namespace,
            "metric_name": metric_name,
            "datapoints": datapoints,
            "count": len(datapoints),
            "region": region,
        }

    except (ClientError, BotoCoreError) as e:
        logger.error("cloudwatch_get_metric_error", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
        }

    except Exception as e:
        logger.error("cloudwatch_get_metric_error", error=str(e))
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


async def list_metrics(
    namespace: Optional[str] = None,
    metric_name: Optional[str] = None,
    region: str = "us-east-1",
    max_results: int = 100,
) -> Dict[str, Any]:
    """
    List available CloudWatch metrics.

    Args:
        namespace: Filter by namespace
        metric_name: Filter by metric name
        region: AWS region
        max_results: Maximum number of results

    Returns:
        Dictionary with metrics list or error information
    """
    try:
        cw = get_cloudwatch_client(region)

        kwargs = {"MaxResults": max_results}
        if namespace:
            kwargs["Namespace"] = namespace
        if metric_name:
            kwargs["MetricName"] = metric_name

        response = cw.list_metrics(**kwargs)

        metrics = []
        for metric in response.get("Metrics", []):
            metrics.append({
                "namespace": metric.get("Namespace"),
                "metric_name": metric.get("MetricName"),
                "dimensions": metric.get("Dimensions", []),
            })

        return {
            "success": True,
            "count": len(metrics),
            "metrics": metrics,
            "region": region,
        }

    except (ClientError, BotoCoreError) as e:
        logger.error("cloudwatch_list_metrics_error", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
        }

    except Exception as e:
        logger.error("cloudwatch_list_metrics_error", error=str(e))
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


async def get_logs(
    log_group_name: str,
    region: str = "us-east-1",
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    filter_pattern: Optional[str] = None,
    limit: int = 100,
) -> Dict[str, Any]:
    """
    Get logs from CloudWatch Logs.

    Args:
        log_group_name: CloudWatch log group name
        region: AWS region
        start_time: Start time for the query
        end_time: End time for the query
        filter_pattern: CloudWatch Logs filter pattern
        limit: Maximum number of log events to return

    Returns:
        Dictionary with log events or error information
    """
    try:
        logs = get_logs_client(region)

        if not start_time:
            start_time = datetime.now() - timedelta(hours=1)
        if not end_time:
            end_time = datetime.now()

        kwargs = {
            "logGroupName": log_group_name,
            "startTime": int(start_time.timestamp() * 1000),
            "endTime": int(end_time.timestamp() * 1000),
            "limit": limit,
        }

        if filter_pattern:
            kwargs["filterPattern"] = filter_pattern

        response = logs.filter_log_events(**kwargs)

        events = []
        for event in response.get("events", []):
            events.append({
                "timestamp": event.get("timestamp"),
                "message": event.get("message"),
                "ingestion_time": event.get("ingestionTime"),
                "log_stream_name": event.get("logStreamName"),
            })

        return {
            "success": True,
            "log_group": log_group_name,
            "count": len(events),
            "events": events,
            "region": region,
        }

    except (ClientError, BotoCoreError) as e:
        logger.error("cloudwatch_get_logs_error", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
        }

    except Exception as e:
        logger.error("cloudwatch_get_logs_error", error=str(e))
        return {"success": False, "error": str(e), "error_type": type(e).__name__}
