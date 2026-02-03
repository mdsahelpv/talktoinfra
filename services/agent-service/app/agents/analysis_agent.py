"""
Analysis Agent for insights, pattern detection, and trend analysis.
Read-only agent safe for auto-execution.
"""

import json
from abc import ABC
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from app.tools.registry import ToolRegistry, get_registry
from app.tools.k8s.read_tools import list_pods, get_pod, get_logs, describe_resource


class AnalysisType(str, Enum):
    """Types of analysis operations."""

    INSIGHT = "insight"  # General insights and observations
    PATTERN = "pattern"  # Pattern detection
    ROOT_CAUSE = "root_cause"  # Root cause analysis
    TREND = "trend"  # Trend analysis
    ANOMALY = "anomaly"  # Anomaly detection
    PREDICTION = "prediction"  # Predictive analysis


@dataclass
class AnalysisResult:
    """Result of an analysis operation."""

    analysis_type: AnalysisType
    title: str
    summary: str
    findings: List[Dict[str, Any]]
    recommendations: List[str]
    confidence: float
    data_points: int
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "analysis_type": self.analysis_type.value,
            "title": self.title,
            "summary": self.summary,
            "findings": self.findings,
            "recommendations": self.recommendations,
            "confidence": self.confidence,
            "data_points": self.data_points,
            "metadata": self.metadata,
        }


class AnalysisAgent:
    """
    Analysis Agent for infrastructure insights and pattern detection.
    Read-only agent safe for auto-execution.

    Capabilities:
    - Insights and pattern detection from infrastructure data
    - Root cause analysis for issues
    - Trend analysis over time
    - Anomaly detection
    - Predictive analysis
    """

    # Patterns for detecting analysis intent
    INSIGHT_PATTERNS = [
        (
            r"(?:what|tell me).*(?:insights|overview|summary|status)",
            AnalysisType.INSIGHT,
        ),
        (
            r"(?:show|find|detect).*(?:patterns|correlations|relationships)",
            AnalysisType.PATTERN,
        ),
        (
            r"(?:why|what caused|root cause|reason for).*(?:error|failure|crash|issue|problem)",
            AnalysisType.ROOT_CAUSE,
        ),
        (r"(?:trends?|changes?|over time|historical|past)", AnalysisType.TREND),
        (r"(?:anomalies?|unusual|abnormal|outliers?|suspicious)", AnalysisType.ANOMALY),
        (r"(?:predict|forecast|will|future|expect|upcoming)", AnalysisType.PREDICTION),
    ]

    def __init__(
        self, registry: Optional[ToolRegistry] = None, llm_client: Optional[Any] = None
    ):
        """
        Initialize the Analysis Agent.

        Args:
            registry: Optional tool registry to use
            llm_client: Optional LLM client for advanced analysis
        """
        self.registry = registry or get_registry()
        self.llm = llm_client
        self._analysis_history: List[Dict[str, Any]] = []

    async def analyze(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        analysis_type: Optional[AnalysisType] = None,
    ) -> AnalysisResult:
        """
        Perform analysis based on query.

        Args:
            query: Natural language analysis query
            context: Additional context for analysis
            analysis_type: Specific type of analysis, auto-detected if None

        Returns:
            AnalysisResult with findings and recommendations
        """
        context = context or {}

        # Detect analysis type if not provided
        if analysis_type is None:
            analysis_type = self._detect_analysis_type(query)

        # Route to appropriate analysis method
        if analysis_type == AnalysisType.INSIGHT:
            return await self._generate_insights(query, context)
        elif analysis_type == AnalysisType.PATTERN:
            return await self._detect_patterns(query, context)
        elif analysis_type == AnalysisType.ROOT_CAUSE:
            return await self._root_cause_analysis(query, context)
        elif analysis_type == AnalysisType.TREND:
            return await self._trend_analysis(query, context)
        elif analysis_type == AnalysisType.ANOMALY:
            return await self._anomaly_detection(query, context)
        elif analysis_type == AnalysisType.PREDICTION:
            return await self._predictive_analysis(query, context)
        else:
            return await self._general_analysis(query, context)

    def _detect_analysis_type(self, query: str) -> AnalysisType:
        """Detect the type of analysis requested."""
        import re

        query_lower = query.lower()

        for pattern, analysis_type in self.INSIGHT_PATTERNS:
            if re.search(pattern, query_lower):
                return analysis_type

        # Default to insight
        return AnalysisType.INSIGHT

    async def _generate_insights(
        self, query: str, context: Dict[str, Any]
    ) -> AnalysisResult:
        """Generate general insights about infrastructure state."""
        namespace = context.get("namespace", "default")
        resource_type = context.get("resource_type")

        findings = []
        data_points = 0

        # Collect pod data
        pods_result = await list_pods(namespace=namespace)
        if pods_result.get("success"):
            pods = pods_result.get("pods", [])
            data_points += len(pods)

            # Analyze pod states
            status_counts = {}
            for pod in pods:
                status = pod.get("status", "Unknown")
                status_counts[status] = status_counts.get(status, 0) + 1

            findings.append(
                {
                    "type": "pod_status_distribution",
                    "description": "Distribution of pod statuses",
                    "data": status_counts,
                }
            )

            # Find pods with issues
            problem_pods = [
                p for p in pods if p.get("status") not in ["Running", "Succeeded"]
            ]
            if problem_pods:
                findings.append(
                    {
                        "type": "problem_pods",
                        "description": f"Found {len(problem_pods)} pods with non-running status",
                        "data": [
                            {
                                "name": p["name"],
                                "status": p["status"],
                                "namespace": p["namespace"],
                            }
                            for p in problem_pods[:10]  # Limit to 10
                        ],
                    }
                )

            # Analyze resource usage patterns
            high_resource_pods = []
            for pod in pods:
                for container in pod.get("containers", []):
                    resources = container.get("resources", {})
                    if resources.get("limits") or resources.get("requests"):
                        high_resource_pods.append(
                            {
                                "pod": pod["name"],
                                "container": container["name"],
                                "resources": resources,
                            }
                        )

            if high_resource_pods:
                findings.append(
                    {
                        "type": "resource_usage",
                        "description": f"{len(high_resource_pods)} containers have resource specifications",
                        "data": high_resource_pods[:5],
                    }
                )

        # Generate summary
        total_pods = data_points
        running_pods = (
            status_counts.get("Running", 0) if pods_result.get("success") else 0
        )

        summary = (
            f"Infrastructure Overview for namespace '{namespace}': "
            f"{running_pods}/{total_pods} pods running. "
        )

        if problem_pods:
            summary += f"{len(problem_pods)} pods require attention. "

        recommendations = []
        if problem_pods:
            recommendations.append("Investigate non-running pods for potential issues")
            recommendations.append("Check pod logs for error messages")
        if running_pods < total_pods * 0.8:
            recommendations.append(
                "Low pod availability - consider scaling or investigating failures"
            )

        return AnalysisResult(
            analysis_type=AnalysisType.INSIGHT,
            title=f"Infrastructure Insights: {namespace}",
            summary=summary,
            findings=findings,
            recommendations=recommendations,
            confidence=0.85,
            data_points=data_points,
            metadata={"namespace": namespace, "query": query},
        )

    async def _detect_patterns(
        self, query: str, context: Dict[str, Any]
    ) -> AnalysisResult:
        """Detect patterns in infrastructure behavior."""
        namespace = context.get("namespace", "default")

        findings = []
        data_points = 0

        # Collect pod data for pattern analysis
        pods_result = await list_pods(namespace=namespace)
        if not pods_result.get("success"):
            return AnalysisResult(
                analysis_type=AnalysisType.PATTERN,
                title="Pattern Analysis",
                summary="Unable to collect data for pattern analysis",
                findings=[],
                recommendations=["Check Kubernetes API connectivity"],
                confidence=0.0,
                data_points=0,
                metadata={"error": pods_result.get("error")},
            )

        pods = pods_result.get("pods", [])
        data_points = len(pods)

        # Pattern 1: Node distribution
        node_distribution = {}
        for pod in pods:
            node = pod.get("node", "unknown")
            node_distribution[node] = node_distribution.get(node, 0) + 1

        findings.append(
            {
                "type": "node_distribution",
                "description": "Pod distribution across nodes",
                "data": node_distribution,
                "pattern": "cluster_balance",
            }
        )

        # Pattern 2: Label patterns
        label_patterns = {}
        for pod in pods:
            labels = pod.get("labels", {})
            for key, value in labels.items():
                pattern_key = f"{key}={value}"
                label_patterns[pattern_key] = label_patterns.get(pattern_key, 0) + 1

        common_labels = {k: v for k, v in label_patterns.items() if v > 1}
        if common_labels:
            findings.append(
                {
                    "type": "common_labels",
                    "description": "Most common label patterns",
                    "data": dict(
                        sorted(common_labels.items(), key=lambda x: x[1], reverse=True)[
                            :10
                        ]
                    ),
                    "pattern": "label_usage",
                }
            )

        # Pattern 3: Creation time clustering
        creation_times = []
        for pod in pods:
            created = pod.get("created")
            if created:
                try:
                    dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    creation_times.append(dt)
                except:
                    pass

        if creation_times:
            creation_times.sort()
            if len(creation_times) >= 2:
                time_range = creation_times[-1] - creation_times[0]
                findings.append(
                    {
                        "type": "creation_pattern",
                        "description": "Pod creation time pattern",
                        "data": {
                            "oldest": creation_times[0].isoformat(),
                            "newest": creation_times[-1].isoformat(),
                            "range_hours": time_range.total_seconds() / 3600,
                            "total_pods": len(creation_times),
                        },
                        "pattern": "deployment_pattern",
                    }
                )

        # Generate summary
        summary = (
            f"Pattern Analysis for namespace '{namespace}': "
            f"Analyzed {data_points} pods. "
            f"Pods distributed across {len(node_distribution)} nodes. "
        )

        recommendations = []

        # Check for imbalance
        if node_distribution:
            avg_pods = sum(node_distribution.values()) / len(node_distribution)
            max_pods = max(node_distribution.values())
            if max_pods > avg_pods * 1.5:
                recommendations.append(
                    "Consider rebalancing pods across nodes for better distribution"
                )

        if not common_labels:
            recommendations.append(
                "Pods lack consistent labeling - consider adding standard labels"
            )

        return AnalysisResult(
            analysis_type=AnalysisType.PATTERN,
            title=f"Pattern Analysis: {namespace}",
            summary=summary,
            findings=findings,
            recommendations=recommendations,
            confidence=0.80,
            data_points=data_points,
            metadata={"namespace": namespace, "query": query},
        )

    async def _root_cause_analysis(
        self, query: str, context: Dict[str, Any]
    ) -> AnalysisResult:
        """Perform root cause analysis for issues."""
        target_resource = context.get("resource_name") or context.get("pod_name")
        namespace = context.get("namespace", "default")
        resource_type = context.get("resource_type", "pod")

        findings = []
        data_points = 0

        if not target_resource:
            # Try to extract from query
            import re

            match = re.search(r"(?:pod|deployment|service)\s+(\S+)", query.lower())
            if match:
                target_resource = match.group(1)

        if not target_resource:
            return AnalysisResult(
                analysis_type=AnalysisType.ROOT_CAUSE,
                title="Root Cause Analysis",
                summary="No target resource specified for root cause analysis",
                findings=[],
                recommendations=[
                    "Please specify a resource name for root cause analysis"
                ],
                confidence=0.0,
                data_points=0,
                metadata={},
            )

        # Get resource details
        if resource_type == "pod":
            resource_result = await get_pod(
                pod_name=target_resource, namespace=namespace
            )
        else:
            resource_result = await describe_resource(
                resource_type=resource_type,
                resource_name=target_resource,
                namespace=namespace,
            )

        if not resource_result.get("success"):
            return AnalysisResult(
                analysis_type=AnalysisType.ROOT_CAUSE,
                title=f"Root Cause Analysis: {target_resource}",
                summary=f"Unable to retrieve resource: {resource_result.get('error', 'Unknown error')}",
                findings=[],
                recommendations=["Verify resource name and namespace"],
                confidence=0.0,
                data_points=0,
                metadata={"resource": target_resource, "namespace": namespace},
            )

        resource = resource_result.get("pod") or resource_result.get("resource", {})
        data_points += 1

        # Analyze status
        status = resource.get("status", "Unknown")
        conditions = resource.get("conditions", [])

        findings.append(
            {
                "type": "current_status",
                "description": f"Resource status: {status}",
                "data": {"status": status, "conditions": conditions},
            }
        )

        # Get logs if it's a pod
        if resource_type == "pod":
            logs_result = await get_logs(
                pod_name=target_resource,
                namespace=namespace,
                tail_lines=500,
            )

            if logs_result.get("success"):
                logs = logs_result.get("logs", "")
                data_points += len(logs.split("\n"))

                # Analyze logs for error patterns
                error_patterns = [
                    r"Error:\s*(.+)",
                    r"Exception:\s*(.+)",
                    r"Failed\s+to\s+(.+)",
                    r"Crash(?:LoopBackOff)?",
                    r"OOMKilled",
                    r"Evicted",
                ]

                log_errors = []
                for pattern in error_patterns:
                    import re

                    matches = re.findall(pattern, logs, re.IGNORECASE)
                    if matches:
                        log_errors.extend(matches[:5])  # Limit to 5 per pattern

                if log_errors:
                    findings.append(
                        {
                            "type": "log_errors",
                            "description": f"Found {len(log_errors)} error patterns in logs",
                            "data": log_errors[:10],
                        }
                    )

        # Generate analysis
        root_causes = []
        recommendations = []

        if status == "CrashLoopBackOff":
            root_causes.append("Application is crashing repeatedly (CrashLoopBackOff)")
            recommendations.append("Check application logs for startup errors")
            recommendations.append("Verify container image and configuration")
            recommendations.append("Check resource limits and requests")

        if status == "Pending":
            root_causes.append("Pod is pending - resource scheduling issue")
            recommendations.append("Check node capacity and resource availability")
            recommendations.append("Verify pod resource requests are not excessive")
            recommendations.append("Check for node selector or affinity constraints")

        if status == "ImagePullBackOff":
            root_causes.append("Container image cannot be pulled")
            recommendations.append("Verify image name and tag are correct")
            recommendations.append("Check image pull secrets if using private registry")
            recommendations.append("Verify network connectivity to registry")

        if any("OOMKilled" in str(err) for err in log_errors if isinstance(err, str)):
            root_causes.append("Container was killed due to out-of-memory (OOM)")
            recommendations.append("Increase memory limits for the container")
            recommendations.append("Investigate memory leaks in application")

        if not root_causes and log_errors:
            root_causes.append(
                f"Application errors detected in logs: {len(log_errors)} error patterns"
            )
            recommendations.append(
                "Review application logs for detailed error messages"
            )
            recommendations.append("Check application configuration and dependencies")

        if not root_causes:
            summary = f"No clear root cause identified for {target_resource}. Resource status is {status}."
            recommendations.append("Continue monitoring for more evidence")
            recommendations.append("Check related services and dependencies")
        else:
            summary = f"Root Cause Analysis for {target_resource}: " + "; ".join(
                root_causes
            )

        return AnalysisResult(
            analysis_type=AnalysisType.ROOT_CAUSE,
            title=f"Root Cause Analysis: {target_resource}",
            summary=summary,
            findings=findings,
            recommendations=recommendations,
            confidence=0.75 if root_causes else 0.4,
            data_points=data_points,
            metadata={
                "resource": target_resource,
                "namespace": namespace,
                "resource_type": resource_type,
            },
        )

    async def _trend_analysis(
        self, query: str, context: Dict[str, Any]
    ) -> AnalysisResult:
        """Analyze trends over time."""
        namespace = context.get("namespace", "default")

        findings = []
        data_points = 0

        # Collect current state
        pods_result = await list_pods(namespace=namespace)
        if pods_result.get("success"):
            pods = pods_result.get("pods", [])
            data_points = len(pods)

            # Analyze creation trend
            creation_times = []
            for pod in pods:
                created = pod.get("created")
                if created:
                    try:
                        dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                        creation_times.append(dt)
                    except:
                        pass

            if creation_times:
                creation_times.sort()
                now = datetime.utcnow()

                # Group by time periods
                recent_1h = sum(
                    1 for t in creation_times if (now - t) < timedelta(hours=1)
                )
                recent_24h = sum(
                    1 for t in creation_times if (now - t) < timedelta(hours=24)
                )
                recent_7d = sum(
                    1 for t in creation_times if (now - t) < timedelta(days=7)
                )

                findings.append(
                    {
                        "type": "creation_trend",
                        "description": "Pod creation trend over time",
                        "data": {
                            "last_1h": recent_1h,
                            "last_24h": recent_24h,
                            "last_7d": recent_7d,
                            "total": len(creation_times),
                            "oldest": creation_times[0].isoformat()
                            if creation_times
                            else None,
                        },
                    }
                )

                # Calculate trend
                if len(creation_times) >= 10:
                    # Simple trend: compare recent vs older
                    median_idx = len(creation_times) // 2
                    recent_half = creation_times[median_idx:]
                    older_half = creation_times[:median_idx]

                    if recent_half and older_half:
                        recent_span = recent_half[-1] - recent_half[0]
                        older_span = older_half[-1] - older_half[0]

                        if (
                            recent_span.total_seconds() > 0
                            and older_span.total_seconds() > 0
                        ):
                            recent_rate = len(recent_half) / (
                                recent_span.total_seconds() / 3600
                            )
                            older_rate = len(older_half) / (
                                older_span.total_seconds() / 3600
                            )

                            trend = (
                                "increasing"
                                if recent_rate > older_rate * 1.2
                                else "decreasing"
                                if recent_rate < older_rate * 0.8
                                else "stable"
                            )

                            findings.append(
                                {
                                    "type": "growth_trend",
                                    "description": f"Pod creation rate is {trend}",
                                    "data": {
                                        "trend": trend,
                                        "recent_rate_per_hour": round(recent_rate, 2),
                                        "older_rate_per_hour": round(older_rate, 2),
                                    },
                                }
                            )

        # Generate summary
        trend_data = next((f for f in findings if f["type"] == "growth_trend"), None)
        if trend_data:
            trend = trend_data["data"]["trend"]
            summary = f"Trend Analysis for {namespace}: Pod creation is {trend}. "
        else:
            summary = f"Trend Analysis for {namespace}: Insufficient data for trend detection. "

        summary += f"Total pods analyzed: {data_points}."

        recommendations = []
        if trend_data and trend_data["data"]["trend"] == "increasing":
            recommendations.append("Consider implementing auto-scaling policies")
            recommendations.append("Monitor resource consumption trends")

        return AnalysisResult(
            analysis_type=AnalysisType.TREND,
            title=f"Trend Analysis: {namespace}",
            summary=summary,
            findings=findings,
            recommendations=recommendations,
            confidence=0.70 if trend_data else 0.50,
            data_points=data_points,
            metadata={"namespace": namespace, "query": query},
        )

    async def _anomaly_detection(
        self, query: str, context: Dict[str, Any]
    ) -> AnalysisResult:
        """Detect anomalies in infrastructure."""
        namespace = context.get("namespace", "default")

        findings = []
        data_points = 0
        anomalies = []

        # Collect pod data
        pods_result = await list_pods(namespace=namespace)
        if pods_result.get("success"):
            pods = pods_result.get("pods", [])
            data_points = len(pods)

            # Anomaly 1: Unusual pod status distribution
            status_counts = {}
            for pod in pods:
                status = pod.get("status", "Unknown")
                status_counts[status] = status_counts.get(status, 0) + 1

            total = sum(status_counts.values())
            if total > 0:
                for status, count in status_counts.items():
                    ratio = count / total
                    if status not in ["Running", "Succeeded"] and ratio > 0.1:
                        anomalies.append(
                            {
                                "type": "status_anomaly",
                                "severity": "medium",
                                "description": f"{count} pods ({ratio * 100:.1f}%) in {status} state",
                                "data": {
                                    "status": status,
                                    "count": count,
                                    "ratio": ratio,
                                },
                            }
                        )

            # Anomaly 2: Resource usage anomalies
            pods_without_resources = []
            for pod in pods:
                for container in pod.get("containers", []):
                    resources = container.get("resources", {})
                    if not resources.get("limits") and not resources.get("requests"):
                        pods_without_resources.append(
                            {
                                "pod": pod["name"],
                                "container": container["name"],
                            }
                        )

            if pods_without_resources:
                anomalies.append(
                    {
                        "type": "resource_anomaly",
                        "severity": "low",
                        "description": f"{len(pods_without_resources)} containers without resource specifications",
                        "data": pods_without_resources[:5],
                    }
                )

            # Anomaly 3: Node distribution anomalies
            node_distribution = {}
            for pod in pods:
                node = pod.get("node", "unknown")
                node_distribution[node] = node_distribution.get(node, 0) + 1

            if node_distribution and len(node_distribution) > 1:
                avg = sum(node_distribution.values()) / len(node_distribution)
                for node, count in node_distribution.items():
                    if count > avg * 2:
                        anomalies.append(
                            {
                                "type": "distribution_anomaly",
                                "severity": "low",
                                "description": f"Node {node} has {count} pods (2x average)",
                                "data": {
                                    "node": node,
                                    "count": count,
                                    "average": round(avg, 1),
                                },
                            }
                        )

        # Add anomaly findings
        for anomaly in anomalies:
            findings.append(anomaly)

        # Generate summary
        if anomalies:
            high_severity = [a for a in anomalies if a["severity"] == "high"]
            medium_severity = [a for a in anomalies if a["severity"] == "medium"]

            summary = (
                f"Anomaly Detection for {namespace}: Found {len(anomalies)} anomalies. "
            )
            if high_severity:
                summary += f"{len(high_severity)} high severity issues require immediate attention. "
            if medium_severity:
                summary += f"{len(medium_severity)} medium severity issues detected. "
        else:
            summary = f"Anomaly Detection for {namespace}: No significant anomalies detected in {data_points} pods."

        recommendations = []
        for anomaly in anomalies:
            if anomaly["type"] == "status_anomaly":
                recommendations.append("Investigate pods with non-running status")
            elif anomaly["type"] == "resource_anomaly":
                recommendations.append(
                    "Set resource limits and requests for all containers"
                )
            elif anomaly["type"] == "distribution_anomaly":
                recommendations.append("Rebalance pod distribution across nodes")

        return AnalysisResult(
            analysis_type=AnalysisType.ANOMALY,
            title=f"Anomaly Detection: {namespace}",
            summary=summary,
            findings=findings,
            recommendations=list(set(recommendations)),  # Deduplicate
            confidence=0.75 if anomalies else 0.60,
            data_points=data_points,
            metadata={
                "namespace": namespace,
                "query": query,
                "anomaly_count": len(anomalies),
            },
        )

    async def _predictive_analysis(
        self, query: str, context: Dict[str, Any]
    ) -> AnalysisResult:
        """Perform predictive analysis."""
        namespace = context.get("namespace", "default")

        findings = []
        predictions = []

        # Collect current data
        pods_result = await list_pods(namespace=namespace)
        if pods_result.get("success"):
            pods = pods_result.get("pods", [])

            # Predict resource exhaustion
            pods_without_limits = sum(
                1
                for pod in pods
                for container in pod.get("containers", [])
                if not container.get("resources", {}).get("limits")
            )

            if pods_without_limits > 0:
                predictions.append(
                    {
                        "type": "resource_risk",
                        "probability": 0.6,
                        "description": f"{pods_without_limits} containers without resource limits risk exhausting node resources",
                        "timeframe": "medium-term",
                        "impact": "high",
                    }
                )

            # Predict scaling needs based on current load
            total_pods = len(pods)
            if total_pods > 20:
                predictions.append(
                    {
                        "type": "scaling_need",
                        "probability": 0.4,
                        "description": f"Current {total_pods} pods may require scaling infrastructure",
                        "timeframe": "long-term",
                        "impact": "medium",
                    }
                )

            # Predict issues from patterns
            error_pods = [
                p
                for p in pods
                if p.get("status") not in ["Running", "Succeeded", "Pending"]
            ]
            if error_pods:
                predictions.append(
                    {
                        "type": "failure_risk",
                        "probability": 0.7,
                        "description": f"Current {len(error_pods)} pods in error state may indicate systemic issues",
                        "timeframe": "immediate",
                        "impact": "high",
                    }
                )

        findings.extend(predictions)

        # Generate summary
        if predictions:
            high_impact = [p for p in predictions if p["impact"] == "high"]
            summary = (
                f"Predictive Analysis for {namespace}: {len(predictions)} predictions. "
            )
            if high_impact:
                summary += (
                    f"{len(high_impact)} high-impact predictions require attention."
                )
        else:
            summary = f"Predictive Analysis for {namespace}: No significant predictions at this time."

        recommendations = []
        for pred in predictions:
            if pred["type"] == "resource_risk":
                recommendations.append("Set resource limits for all containers")
            elif pred["type"] == "scaling_need":
                recommendations.append("Plan for infrastructure scaling")
            elif pred["type"] == "failure_risk":
                recommendations.append(
                    "Address current pod errors to prevent cascading failures"
                )

        return AnalysisResult(
            analysis_type=AnalysisType.PREDICTION,
            title=f"Predictive Analysis: {namespace}",
            summary=summary,
            findings=findings,
            recommendations=recommendations,
            confidence=0.60,
            data_points=len(pods) if pods_result.get("success") else 0,
            metadata={"namespace": namespace, "query": query},
        )

    async def _general_analysis(
        self, query: str, context: Dict[str, Any]
    ) -> AnalysisResult:
        """General analysis when specific type not detected."""
        return await self._generate_insights(query, context)

    def get_supported_analysis_types(self) -> List[Dict[str, str]]:
        """Get list of supported analysis types."""
        return [
            {"type": t.value, "description": self._get_analysis_description(t)}
            for t in AnalysisType
        ]

    def _get_analysis_description(self, analysis_type: AnalysisType) -> str:
        """Get description for an analysis type."""
        descriptions = {
            AnalysisType.INSIGHT: "Generate insights and overview of infrastructure state",
            AnalysisType.PATTERN: "Detect patterns and correlations in infrastructure data",
            AnalysisType.ROOT_CAUSE: "Perform root cause analysis for issues",
            AnalysisType.TREND: "Analyze trends and changes over time",
            AnalysisType.ANOMALY: "Detect anomalies and unusual behavior",
            AnalysisType.PREDICTION: "Make predictions about future infrastructure behavior",
        }
        return descriptions.get(analysis_type, "General analysis")


# Global agent instance
_analysis_agent: Optional[AnalysisAgent] = None


def get_analysis_agent(
    registry: Optional[ToolRegistry] = None, llm_client: Optional[Any] = None
) -> AnalysisAgent:
    """Get or create the global analysis agent instance."""
    global _analysis_agent
    if _analysis_agent is None:
        _analysis_agent = AnalysisAgent(registry, llm_client)
    return _analysis_agent
