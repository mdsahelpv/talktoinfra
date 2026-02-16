"""
Self-Healing API Endpoints.

REST API for automated self-healing configuration and execution.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.services.self_healing import get_self_healing_service

router = APIRouter()


# Request/Response Schemas
class SelfHealingCheckRequest(BaseModel):
    """Request to trigger self-healing check."""
    cluster_id: str
    namespace: Optional[str] = None


class SelfHealingActionResponse(BaseModel):
    """Response for a self-healing action."""
    type: str
    pod: Optional[str] = None
    job: Optional[str] = None
    hpa: Optional[str] = None
    namespace: Optional[str] = None
    status: str
    result: Optional[dict] = None
    error: Optional[str] = None


class SelfHealingRuleBase(BaseModel):
    """Base schema for self-healing rules."""
    name: str
    description: Optional[str] = None
    rule_type: str  # auto_restart_pod, auto_scale_hpa, auto_retry_job
    enabled: bool = True
    condition_type: str
    condition_value: dict
    action_type: str
    action_config: dict = {}
    max_retries: int = 3
    retry_interval_seconds: int = 60
    cooldown_seconds: int = 300


class SelfHealingRuleCreate(SelfHealingRuleBase):
    """Schema for creating a self-healing rule."""
    cluster_id: Optional[str] = None
    namespace: Optional[str] = None
    label_selector: dict = {}


class SelfHealingRuleResponse(SelfHealingRuleBase):
    """Response for a self-healing rule."""
    id: int
    cluster_id: Optional[str] = None
    namespace: Optional[str] = None
    label_selector: dict = {}
    notify_on_action: bool = True
    notify_channels: list = []
    created_at: str
    updated_at: str
    last_triggered: Optional[str] = None


class RunbookBase(BaseModel):
    """Base schema for runbooks."""
    name: str
    description: Optional[str] = None
    trigger_type: str
    trigger_condition: dict
    steps: list
    enabled: bool = True
    require_approval: bool = False
    timeout_seconds: int = 600
    rollback_on_failure: bool = True
    rollback_steps: list = []


class RunbookCreate(RunbookBase):
    """Schema for creating a runbook."""
    pass


class RunbookResponse(RunbookBase):
    """Response for a runbook."""
    id: int
    times_executed: int = 0
    success_count: int = 0
    failure_count: int = 0
    last_executed: Optional[str] = None
    created_at: str
    updated_at: str


# API Endpoints
@router.post("/check", response_model=List[SelfHealingActionResponse])
async def trigger_self_healing_check(
    request: SelfHealingCheckRequest,
) -> List[SelfHealingActionResponse]:
    """Trigger a self-healing check for a cluster.

    This endpoint checks for:
    - CrashLoopBackOff pods (auto-restart)
    - Failed jobs (auto-retry)
    - HPA scaling recommendations

    Args:
        request: Self-healing check request

    Returns:
        List of actions taken
    """
    service = get_self_healing_service()

    actions = await service.check_and_execute_self_healing(
        cluster_id=request.cluster_id,
        namespace=request.namespace,
    )

    return [SelfHealingActionResponse(**action) for action in actions]


@router.get("/rules", response_model=List[SelfHealingRuleResponse])
async def list_self_healing_rules(
    cluster_id: Optional[str] = None,
    rule_type: Optional[str] = None,
    enabled: Optional[bool] = None,
) -> List[SelfHealingRuleResponse]:
    """List self-healing rules.

    Args:
        cluster_id: Filter by cluster
        rule_type: Filter by rule type
        enabled: Filter by enabled status

    Returns:
        List of self-healing rules
    """
    # Would query database
    return []


@router.post("/rules", response_model=SelfHealingRuleResponse)
async def create_self_healing_rule(
    rule: SelfHealingRuleCreate,
) -> SelfHealingRuleResponse:
    """Create a new self-healing rule.

    Args:
        rule: Rule to create

    Returns:
        Created rule
    """
    # Would save to database
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Database integration pending",
    )


@router.get("/rules/{rule_id}", response_model=SelfHealingRuleResponse)
async def get_self_healing_rule(
    rule_id: int,
) -> SelfHealingRuleResponse:
    """Get a self-healing rule by ID.

    Args:
        rule_id: Rule ID

    Returns:
        The rule
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Database integration pending",
    )


@router.delete("/rules/{rule_id}")
async def delete_self_healing_rule(
    rule_id: int,
) -> dict:
    """Delete a self-healing rule.

    Args:
        rule_id: Rule ID

    Returns:
        Deletion confirmation
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Database integration pending",
    )


@router.get("/runbooks", response_model=List[RunbookResponse])
async def list_runbooks(
    trigger_type: Optional[str] = None,
    enabled: Optional[bool] = None,
) -> List[RunbookResponse]:
    """List runbooks.

    Args:
        trigger_type: Filter by trigger type
        enabled: Filter by enabled status

    Returns:
        List of runbooks
    """
    return []


@router.post("/runbooks", response_model=RunbookResponse)
async def create_runbook(
    runbook: RunbookCreate,
) -> RunbookResponse:
    """Create a new runbook.

    Args:
        runbook: Runbook to create

    Returns:
        Created runbook
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Database integration pending",
    )


@router.post("/runbooks/{runbook_id}/execute")
async def execute_runbook(
    runbook_id: int,
    trigger_data: dict = {},
    context: dict = {},
) -> dict:
    """Execute a runbook.

    Args:
        runbook_id: Runbook ID
        trigger_data: Data that triggered the runbook
        context: Execution context

    Returns:
        Execution result
    """
    service = get_self_healing_service()
    result = await service.execute_runbook(runbook_id, trigger_data, context)
    return result
