"""
Smart Suggestions API for Discovery Service.

Analyzes scan results and generates onboarding recommendations
with confidence scores for infrastructure patterns.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.middleware import UserContext, get_current_user
from app.services.cloud_detector import CloudDetector, get_cloud_detector
from app.services.k8s_detector import K8sDetector, get_k8s_detector
from app.services.onboarding_integration import (
    OnboardingIntegration,
    OnboardingSuggestion,
    get_onboarding_integration,
)

logger = structlog.get_logger()
router = APIRouter()


# Database port patterns
DATABASE_PORTS: Dict[str, List[int]] = {
    "postgresql": [5432, 5433],
    "mysql": [3306, 3307],
    "mongodb": [27017, 27018],
    "redis": [6379, 6380],
    "elasticsearch": [9200, 9300],
    "oracle": [1521],
    "sqlserver": [1433, 1434],
    "cassandra": [9042, 9160],
    "rabbitmq": [5672, 15672],
    "kafka": [9092, 9093],
}

# Load balancer patterns
LB_PORTS: List[int] = [80, 443, 8080, 8443, 3000, 3001, 5000, 8000]


# Response schemas


class SuggestionCard(BaseModel):
    """Suggestion card for frontend display."""

    id: str
    type: str
    confidence: float
    title: str
    description: str
    recommendation: str
    suggested_name: str
    api_endpoint: Optional[str] = None
    port: Optional[int] = None
    host_count: int = 1
    hosts: List[str] = []
    cloud_provider: Optional[str] = None
    metadata: Dict[str, Any] = {}


class SuggestionsResponse(BaseModel):
    """Response containing all suggestions for a scan."""

    scan_id: UUID
    total_suggestions: int
    k8s_suggestions: List[SuggestionCard] = []
    cloud_suggestions: List[SuggestionCard] = []
    database_suggestions: List[SuggestionCard] = []
    load_balancer_suggestions: List[SuggestionCard] = []
    generated_at: datetime


class OnboardingExecuteRequest(BaseModel):
    """Request to execute onboarding for a suggestion."""

    suggestion_id: str
    suggestion_type: str
    suggested_name: str
    api_endpoint: Optional[str] = None
    port: Optional[int] = None
    hosts: List[str] = []
    cloud_provider: Optional[str] = None
    metadata: Dict[str, Any] = {}


class OnboardingExecuteResponse(BaseModel):
    """Response from executing onboarding."""

    success: bool
    suggestion_id: str
    cluster_id: Optional[str] = None
    message: str
    details: Optional[Dict[str, Any]] = None


def get_job_manager(request: Request):
    """Get job manager from app state."""
    return request.app.state.job_manager


def get_k8s_detector_singleton() -> K8sDetector:
    """Get K8s detector singleton."""
    return get_k8s_detector()


def get_cloud_detector_singleton() -> CloudDetector:
    """Get cloud detector singleton."""
    return get_cloud_detector()


def get_onboarding_integration_singleton() -> OnboardingIntegration:
    """Get onboarding integration singleton."""
    return get_onboarding_integration()


@router.get(
    "/discovery/{scan_id}/suggestions",
    response_model=SuggestionsResponse,
    responses={404: {"model": None}, 403: {"model": None}},
)
async def get_scan_suggestions(
    scan_id: UUID,
    job_manager=Depends(get_job_manager),
    k8s_detector: K8sDetector = Depends(get_k8s_detector_singleton),
    cloud_detector: CloudDetector = Depends(get_cloud_detector_singleton),
    onboarding_integration: OnboardingIntegration = Depends(
        get_onboarding_integration_singleton),
    current_user: UserContext = Depends(get_current_user),
) -> SuggestionsResponse:
    """Get onboarding suggestions for a completed scan.

    Analyzes scan results to detect:
    - Kubernetes clusters
    - Cloud provider resources (AWS, Azure, GCP)
    - Database servers
    - Load balancers

    Returns suggestions with confidence scores and recommended actions.
    """
    # Get scan job
    job = await job_manager.get_job(scan_id)
    if not job:
        raise HTTPException(status_code=404, detail="Scan job not found")

    # Check authorization
    if not current_user.is_admin and job.created_by != current_user.user_id:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to access this scan",
        )

    # Check if scan is complete
    if job.status not in ["completed", "failed", "cancelled"]:
        raise HTTPException(
            status_code=400,
            detail=f"Scan is still {job.status}. Suggestions not available yet.",
        )

    if job.status != "completed":
        return SuggestionsResponse(
            scan_id=scan_id,
            total_suggestions=0,
            generated_at=datetime.utcnow(),
        )

    # Get scan results
    hosts = await job_manager.get_job_results(scan_id, alive_only=True)

    logger.info(
        "generating_suggestions",
        scan_id=str(scan_id),
        host_count=len(hosts),
    )

    # Generate suggestions
    k8s_suggestions: List[SuggestionCard] = []
    cloud_suggestions: List[SuggestionCard] = []
    database_suggestions: List[SuggestionCard] = []
    lb_suggestions: List[SuggestionCard] = []

    # Detect K8s clusters
    k8s_clusters = k8s_detector.detect_clusters(hosts, scan_id)
    for cluster in k8s_clusters:
        if cluster.confidence_score < 0.3:
            continue

        api_endpoint = cluster.api_endpoints[0] if cluster.api_endpoints else None
        port = 6443 if api_endpoint else None

        suggestion = onboarding_integration.create_onboarding_suggestion(
            suggestion_type="k8s_cluster",
            ip_addresses=cluster.node_ips or cluster.api_endpoints,
            api_endpoint=api_endpoint,
            port=port,
            confidence=cluster.confidence_score,
            extra_metadata=k8s_detector.get_detection_metadata(cluster),
        )

        k8s_suggestions.append(SuggestionCard(
            id=suggestion.suggestion_id,
            type="k8s_cluster",
            confidence=suggestion.confidence,
            title=suggestion.title,
            description=suggestion.description,
            recommendation=suggestion.recommendation,
            suggested_name=suggestion.suggested_name,
            api_endpoint=suggestion.api_endpoint,
            port=suggestion.port,
            host_count=len(suggestion.hosts),
            hosts=suggestion.hosts,
            metadata=suggestion.metadata,
        ))

    # Detect cloud accounts
    cloud_accounts = cloud_detector.detect_cloud_accounts(hosts, scan_id)
    for account in cloud_accounts:
        if account.confidence_score < 0.3:
            continue

        suggestion_type = f"{account.provider}_account"
        suggestion = onboarding_integration.create_onboarding_suggestion(
            suggestion_type=suggestion_type,
            ip_addresses=account.hosts,
            confidence=account.confidence_score,
            cloud_provider=account.provider,
            extra_metadata=cloud_detector.get_detection_metadata(account),
        )

        cloud_suggestions.append(SuggestionCard(
            id=suggestion.suggestion_id,
            type=suggestion_type,
            confidence=suggestion.confidence,
            title=suggestion.title,
            description=suggestion.description,
            recommendation=suggestion.recommendation,
            suggested_name=suggestion.suggested_name,
            host_count=len(suggestion.hosts),
            hosts=suggestion.hosts,
            cloud_provider=suggestion.cloud_provider,
            metadata=suggestion.metadata,
        ))

    # Detect databases
    database_hosts = _detect_databases(hosts)
    for db_type, db_hosts in database_hosts.items():
        if not db_hosts:
            continue

        suggestion = onboarding_integration.create_onboarding_suggestion(
            suggestion_type="database",
            ip_addresses=db_hosts,
            confidence=0.7,
            extra_metadata={"database_type": db_type,
                            "host_count": len(db_hosts)},
        )

        database_suggestions.append(SuggestionCard(
            id=suggestion.suggestion_id,
            type="database",
            confidence=suggestion.confidence,
            title=suggestion.title,
            description=suggestion.description,
            recommendation=suggestion.recommendation,
            suggested_name=suggestion.suggested_name,
            host_count=len(suggestion.hosts),
            hosts=suggestion.hosts,
            metadata=suggestion.metadata,
        ))

    # Detect load balancers
    lb_hosts = _detect_load_balancers(hosts)
    if lb_hosts:
        suggestion = onboarding_integration.create_onboarding_suggestion(
            suggestion_type="load_balancer",
            ip_addresses=lb_hosts,
            confidence=0.6,
            extra_metadata={"host_count": len(lb_hosts)},
        )

        lb_suggestions.append(SuggestionCard(
            id=suggestion.suggestion_id,
            type="load_balancer",
            confidence=suggestion.confidence,
            title=suggestion.title,
            description=suggestion.description,
            recommendation=suggestion.recommendation,
            suggested_name=suggestion.suggested_name,
            host_count=len(suggestion.hosts),
            hosts=suggestion.hosts,
            metadata=suggestion.metadata,
        ))

    total = (
        len(k8s_suggestions)
        + len(cloud_suggestions)
        + len(database_suggestions)
        + len(lb_suggestions)
    )

    logger.info(
        "suggestions_generated",
        scan_id=str(scan_id),
        total=total,
        k8s=len(k8s_suggestions),
        cloud=len(cloud_suggestions),
        databases=len(database_suggestions),
        load_balancers=len(lb_suggestions),
    )

    return SuggestionsResponse(
        scan_id=scan_id,
        total_suggestions=total,
        k8s_suggestions=k8s_suggestions,
        cloud_suggestions=cloud_suggestions,
        database_suggestions=database_suggestions,
        load_balancer_suggestions=lb_suggestions,
        generated_at=datetime.utcnow(),
    )


@router.post(
    "/discovery/suggestions/execute",
    response_model=OnboardingExecuteResponse,
    responses={400: {"model": None}},
)
async def execute_onboarding(
    request: OnboardingExecuteRequest,
    onboarding_integration: OnboardingIntegration = Depends(
        get_onboarding_integration_singleton),
    current_user: UserContext = Depends(get_current_user),
) -> OnboardingExecuteResponse:
    """Execute onboarding for a suggestion.

    Creates the appropriate onboarding based on suggestion type.
    """
    logger.info(
        "executing_onboarding",
        suggestion_id=request.suggestion_id,
        suggestion_type=request.suggestion_type,
        user_id=current_user.user_id,
    )

    try:
        # Create suggestion object
        suggestion = OnboardingSuggestion(
            suggestion_id=request.suggestion_id,
            type=request.suggestion_type,
            confidence=0.8,
            title=f"{request.suggestion_type.title()} Detected",
            description=f"Found at {', '.join(request.hosts[:3])}",
            recommendation="Ready for onboarding",
            suggested_name=request.suggested_name,
            api_endpoint=request.api_endpoint,
            port=request.port,
            hosts=request.hosts,
            cloud_provider=request.cloud_provider,
            metadata=request.metadata,
        )

        # Execute onboarding
        result = await onboarding_integration.onboard_suggestion(
            suggestion=suggestion,
            user_id=current_user.user_id,
        )

        return OnboardingExecuteResponse(
            success=True,
            suggestion_id=request.suggestion_id,
            cluster_id=result.get("cluster_id"),
            message=result.get("message"),
            details=result,
        )

    except Exception as e:
        logger.error(
            "onboarding_execution_failed",
            suggestion_id=request.suggestion_id,
            error=str(e),
        )
        return OnboardingExecuteResponse(
            success=False,
            suggestion_id=request.suggestion_id,
            message=f"Failed to execute onboarding: {str(e)}",
        )


def _detect_databases(hosts: List) -> Dict[str, List[str]]:
    """Detect database servers from hosts.

    Args:
        hosts: List of discovered hosts

    Returns:
        Dictionary of database type to list of IP addresses
    """
    databases: Dict[str, List[str]] = {}

    for host in hosts:
        port_list = getattr(host, "ports", []) or []
        open_ports = [p.port for p in port_list if p.status == "open"]

        for db_type, ports in DATABASE_PORTS.items():
            if any(p in open_ports for p in ports):
                if db_type not in databases:
                    databases[db_type] = []
                if str(host.ip_address) not in databases[db_type]:
                    databases[db_type].append(str(host.ip_address))

    return databases


def _detect_load_balancers(hosts: List) -> List[str]:
    """Detect load balancers from hosts.

    Args:
        hosts: List of discovered hosts

    Returns:
        List of load balancer IP addresses
    """
    lb_ips: List[str] = []

    for host in hosts:
        port_list = getattr(host, "ports", []) or []
        open_ports = [p.port for p in port_list if p.status == "open"]

        # Check for common LB ports
        lb_port_count = sum(1 for p in open_ports if p in LB_PORTS)

        if lb_port_count >= 2:
            # Likely a load balancer
            lb_ips.append(str(host.ip_address))

    return lb_ips
