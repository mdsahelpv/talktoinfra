"""
Self-Healing Service.

Automated infrastructure remediation for Kubernetes:
- Auto-restart CrashLoopBackOff pods
- Auto-scale HPA
- Auto-retry failed jobs
- Runbook automation
"""

import asyncio
import httpx
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import structlog

from app.config import get_settings
from app.models_self_healing import (
    SelfHealingRule,
    SelfHealingAction,
    Runbook,
    RunbookExecution,
)

logger = structlog.get_logger()


class SelfHealingService:
    """Service for automated infrastructure remediation."""

    def __init__(self):
        """Initialize the self-healing service."""
        self.settings = get_settings()
        self._action_engine_url = self.settings.action_engine_url

    async def check_and_execute_self_healing(
        self,
        cluster_id: str,
        namespace: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Check conditions and execute self-healing actions.

        Args:
            cluster_id: The cluster to check
            namespace: Optional namespace filter

        Returns:
            List of actions taken
        """
        actions_taken = []

        # Get problematic pods
        problematic_pods = await self._get_crashloop_pods(cluster_id, namespace)
        for pod in problematic_pods:
            action = await self._handle_crashloop_pod(cluster_id, pod)
            if action:
                actions_taken.append(action)

        # Get failed jobs
        failed_jobs = await self._get_failed_jobs(cluster_id, namespace)
        for job in failed_jobs:
            action = await self._handle_failed_job(cluster_id, job)
            if action:
                actions_taken.append(action)

        # Check HPA recommendations
        hpa_recommendations = await self._check_hpa_scaling(cluster_id, namespace)
        for rec in hpa_recommendations:
            action = await self._handle_hpa_scaling(cluster_id, rec)
            if action:
                actions_taken.append(action)

        return actions_taken

    async def _get_crashloop_pods(
        self,
        cluster_id: str,
        namespace: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get pods in CrashLoopBackOff state.

        Args:
            cluster_id: The cluster to check
            namespace: Optional namespace filter

        Returns:
            List of pods in CrashLoopBackOff
        """
        try:
            async with httpx.AsyncClient() as client:
                # Query action engine or directly query K8s
                response = await client.get(
                    f"{self._action_engine_url}/api/v1/resources/pods",
                    params={
                        "cluster_id": cluster_id,
                        "namespace": namespace,
                        "status": "CrashLoopBackOff",
                    },
                    timeout=30.0,
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("items", [])
                return []
        except Exception as e:
            logger.error(
                "failed_to_get_crashloop_pods",
                cluster_id=cluster_id,
                error=str(e),
            )
            return []

    async def _handle_crashloop_pod(
        self,
        cluster_id: str,
        pod: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Handle a pod in CrashLoopBackOff state.

        Args:
            cluster_id: The cluster ID
            pod: Pod information

        Returns:
            Action result
        """
        pod_name = pod.get("name")
        pod_namespace = pod.get("namespace")
        restart_count = pod.get("restart_count", 0)

        logger.info(
            "handling_crashloop_pod",
            pod=pod_name,
            namespace=pod_namespace,
            restarts=restart_count,
        )

        # Check if we should auto-restart (e.g., more than 3 restarts)
        if restart_count < 3:
            logger.info(
                "pod_restart_count_low",
                pod=pod_name,
                restarts=restart_count,
            )
            return None

        # Execute restart action via action engine
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self._action_engine_url}/api/v1/actions/execute",
                    json={
                        "action_type": "restart_pod",
                        "parameters": {
                            "cluster_id": cluster_id,
                            "namespace": pod_namespace,
                            "pod_name": pod_name,
                        },
                        "dry_run": False,
                    },
                    timeout=60.0,
                )

                if response.status_code == 200:
                    result = response.json()
                    logger.info(
                        "pod_restart_executed",
                        pod=pod_name,
                        result=result,
                    )
                    return {
                        "type": "auto_restart_pod",
                        "pod": pod_name,
                        "namespace": pod_namespace,
                        "status": "success",
                        "result": result,
                    }
                else:
                    logger.error(
                        "pod_restart_failed",
                        pod=pod_name,
                        status=response.status_code,
                    )
                    return {
                        "type": "auto_restart_pod",
                        "pod": pod_name,
                        "namespace": pod_namespace,
                        "status": "failed",
                        "error": f"HTTP {response.status_code}",
                    }

        except Exception as e:
            logger.error(
                "pod_restart_error",
                pod=pod_name,
                error=str(e),
            )
            return {
                "type": "auto_restart_pod",
                "pod": pod_name,
                "namespace": pod_namespace,
                "status": "error",
                "error": str(e),
            }

    async def _get_failed_jobs(
        self,
        cluster_id: str,
        namespace: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get failed Kubernetes jobs.

        Args:
            cluster_id: The cluster to check
            namespace: Optional namespace filter

        Returns:
            List of failed jobs
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self._action_engine_url}/api/v1/resources/jobs",
                    params={
                        "cluster_id": cluster_id,
                        "namespace": namespace,
                        "status": "failed",
                    },
                    timeout=30.0,
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("items", [])
                return []
        except Exception as e:
            logger.error(
                "failed_to_get_failed_jobs",
                cluster_id=cluster_id,
                error=str(e),
            )
            return []

    async def _handle_failed_job(
        self,
        cluster_id: str,
        job: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Handle a failed job by retrying it.

        Args:
            cluster_id: The cluster ID
            job: Job information

        Returns:
            Action result
        """
        job_name = job.get("name")
        job_namespace = job.get("namespace")

        logger.info(
            "handling_failed_job",
            job=job_name,
            namespace=job_namespace,
        )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self._action_engine_url}/api/v1/actions/execute",
                    json={
                        "action_type": "retry_job",
                        "parameters": {
                            "cluster_id": cluster_id,
                            "namespace": job_namespace,
                            "job_name": job_name,
                        },
                        "dry_run": False,
                    },
                    timeout=60.0,
                )

                if response.status_code == 200:
                    result = response.json()
                    logger.info(
                        "job_retry_executed",
                        job=job_name,
                        result=result,
                    )
                    return {
                        "type": "auto_retry_job",
                        "job": job_name,
                        "namespace": job_namespace,
                        "status": "success",
                        "result": result,
                    }
                else:
                    return {
                        "type": "auto_retry_job",
                        "job": job_name,
                        "namespace": job_namespace,
                        "status": "failed",
                        "error": f"HTTP {response.status_code}",
                    }

        except Exception as e:
            logger.error(
                "job_retry_error",
                job=job_name,
                error=str(e),
            )
            return {
                "type": "auto_retry_job",
                "job": job_name,
                "namespace": job_namespace,
                "status": "error",
                "error": str(e),
            }

    async def _check_hpa_scaling(
        self,
        cluster_id: str,
        namespace: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Check HPA for scaling recommendations.

        Args:
            cluster_id: The cluster to check
            namespace: Optional namespace filter

        Returns:
            List of HPA scaling recommendations
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self._action_engine_url}/api/v1/resources/hpa",
                    params={
                        "cluster_id": cluster_id,
                        "namespace": namespace,
                    },
                    timeout=30.0,
                )
                if response.status_code == 200:
                    data = response.json()
                    recommendations = []

                    for hpa in data.get("items", []):
                        current_replicas = hpa.get("current_replicas", 0)
                        max_replicas = hpa.get("max_replicas", 10)
                        cpu_percent = hpa.get("cpu_percent", 0)

                        # Recommend scaling if CPU is consistently high
                        if cpu_percent > 80 and current_replicas < max_replicas:
                            recommendations.append({
                                "hpa_name": hpa.get("name"),
                                "namespace": hpa.get("namespace"),
                                "current_replicas": current_replicas,
                                "max_replicas": max_replicas,
                                "cpu_percent": cpu_percent,
                                "recommended_replicas": min(
                                    current_replicas + 1,
                                    max_replicas
                                ),
                            })

                    return recommendations
                return []
        except Exception as e:
            logger.error(
                "failed_to_check_hpa",
                cluster_id=cluster_id,
                error=str(e),
            )
            return []

    async def _handle_hpa_scaling(
        self,
        cluster_id: str,
        recommendation: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Execute HPA scaling recommendation.

        Args:
            cluster_id: The cluster ID
            recommendation: Scaling recommendation

        Returns:
            Action result
        """
        hpa_name = recommendation.get("hpa_name")
        namespace = recommendation.get("namespace")
        replicas = recommendation.get("recommended_replicas")

        logger.info(
            "executing_hpa_scale",
            hpa=hpa_name,
            namespace=namespace,
            replicas=replicas,
        )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self._action_engine_url}/api/v1/actions/execute",
                    json={
                        "action_type": "scale_hpa",
                        "parameters": {
                            "cluster_id": cluster_id,
                            "namespace": namespace,
                            "hpa_name": hpa_name,
                            "replicas": replicas,
                        },
                        "dry_run": False,
                    },
                    timeout=60.0,
                )

                if response.status_code == 200:
                    result = response.json()
                    logger.info(
                        "hpa_scale_executed",
                        hpa=hpa_name,
                        result=result,
                    )
                    return {
                        "type": "auto_scale_hpa",
                        "hpa": hpa_name,
                        "namespace": namespace,
                        "replicas": replicas,
                        "status": "success",
                        "result": result,
                    }
                else:
                    return {
                        "type": "auto_scale_hpa",
                        "hpa": hpa_name,
                        "namespace": namespace,
                        "replicas": replicas,
                        "status": "failed",
                        "error": f"HTTP {response.status_code}",
                    }

        except Exception as e:
            logger.error(
                "hpa_scale_error",
                hpa=hpa_name,
                error=str(e),
            )
            return {
                "type": "auto_scale_hpa",
                "hpa": hpa_name,
                "namespace": namespace,
                "replicas": replicas,
                "status": "error",
                "error": str(e),
            }

    async def execute_runbook(
        self,
        runbook_id: int,
        trigger_data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a runbook.

        Args:
            runbook_id: The runbook ID to execute
            trigger_data: Data that triggered the runbook
            context: Execution context

        Returns:
            Execution result
        """
        logger.info(
            "executing_runbook",
            runbook_id=runbook_id,
            trigger=trigger_data,
        )

        # This would fetch the runbook from DB and execute steps
        # For now, return a placeholder
        return {
            "runbook_id": runbook_id,
            "status": "executed",
            "steps_completed": [],
        }


# Singleton instance
_self_healing_service: Optional[SelfHealingService] = None


def get_self_healing_service() -> SelfHealingService:
    """Get the self-healing service singleton."""
    global _self_healing_service
    if _self_healing_service is None:
        _self_healing_service = SelfHealingService()
    return _self_healing_service
