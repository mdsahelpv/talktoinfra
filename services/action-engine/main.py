"""
Action Engine Service

Executes infrastructure actions with dry-run support and rollback capabilities.
Integrates with Policy Engine for validation and supports sandbox execution.
"""

import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
import structlog
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from models import (
    ActionRequest,
    ActionResponse,
    RollbackResult,
    ActionStatus,
)
from executor import ActionExecutor
from rollback import RollbackManager
from sandbox import SandboxEnvironment

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# In-memory action store (replace with database in production)
action_store: Dict[str, ActionResponse] = {}

# Service components
executor: Optional[ActionExecutor] = None
rollback_manager: Optional[RollbackManager] = None
sandbox: Optional[SandboxEnvironment] = None
http_client: Optional[httpx.AsyncClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    global executor, rollback_manager, sandbox, http_client

    settings = get_settings()

    logger.info("action_engine_initializing", port=settings.service_port)

    # Initialize components
    executor = ActionExecutor()
    rollback_manager = RollbackManager()
    sandbox = SandboxEnvironment()
    http_client = httpx.AsyncClient(
        timeout=30.0,
        limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
    )

    logger.info("action_engine_ready")

    yield

    # Cleanup
    if http_client:
        await http_client.aclose()
    logger.info("action_engine_shutting_down")


app = FastAPI(
    title="AI Infrastructure Operations - Action Engine",
    description="Execute infrastructure actions with dry-run and rollback support",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log all requests with context."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
    )
    try:
        logger.info("request_started")
        response = await call_next(request)
        logger.info("request_completed", status_code=response.status_code)
        return response
    finally:
        structlog.contextvars.clear_contextvars()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    health = {
        "status": "healthy",
        "service": "action-engine",
        "timestamp": time.time(),
        "components": {
            "executor": "healthy" if executor else "unhealthy",
            "sandbox": "healthy" if sandbox else "unhealthy",
            "rollback": "healthy" if rollback_manager else "unhealthy",
        },
    }
    return health


@app.post("/actions/dry-run", response_model=ActionResponse)
async def dry_run_action(request: Request, action_req: ActionRequest):
    """Simulate action execution without making actual changes."""
    try:
        action_id = str(uuid.uuid4())
        logger.info(
            "dry_run_started",
            action_id=action_id,
            action=action_req.action,
            target=action_req.target,
            user_id=action_req.user_id,
        )

        # Validate with Policy Engine
        policy_check = await validate_with_policy_engine(action_req)
        if not policy_check.get("allowed", False):
            logger.warning(
                "policy_check_failed",
                action_id=action_id,
                reason=policy_check.get("reason"),
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Policy check failed: {policy_check.get('reason')}",
            )

        # Execute dry-run in sandbox
        dry_run_result = await sandbox.execute_dry_run(
            action=action_req.action,
            target=action_req.target,
            parameters=action_req.parameters,
        )

        # Check if approval is required
        requires_approval = policy_check.get("requires_approval", False)
        approvers = policy_check.get("approvers", [])

        # Create action record
        action_response = ActionResponse(
            action_id=action_id,
            status=(
                ActionStatus.PENDING_APPROVAL
                if requires_approval
                else ActionStatus.APPROVED
            ),
            action=action_req.action,
            target=action_req.target,
            parameters=action_req.parameters,
            dry_run_result=dry_run_result,
            requires_approval=requires_approval,
            approvers=approvers,
            requested_by=action_req.user_id,
            created_at=datetime.utcnow(),
        )

        # Store action
        action_store[action_id] = action_response

        # Log to audit service
        await log_to_audit(
            action_id=action_id,
            user_id=action_req.user_id,
            action="dry_run",
            details={
                "action_type": action_req.action,
                "target": action_req.target,
                "requires_approval": requires_approval,
            },
        )

        logger.info(
            "dry_run_completed",
            action_id=action_id,
            requires_approval=requires_approval,
        )

        return action_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("dry_run_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dry-run failed: {str(e)}",
        )


@app.post("/actions/execute", response_model=ActionResponse)
async def execute_action(
    request: Request,
    action_id: str,
    user_id: str,
    user_roles: List[str],
):
    """Execute an approved action."""
    try:
        logger.info(
            "action_execution_started",
            action_id=action_id,
            user_id=user_id,
        )

        # Get action from store
        if action_id not in action_store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Action not found",
            )

        action = action_store[action_id]

        # Check if action is approved
        if action.status != ActionStatus.APPROVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Action is not approved. Current status: {action.status}",
            )

        # Validate execution permissions
        policy_check = await validate_execution_permissions(
            action_id, user_id, user_roles
        )
        if not policy_check.get("allowed", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to execute this action",
            )

        # Update status
        action.status = ActionStatus.EXECUTING
        action.started_at = datetime.utcnow()

        # Create rollback point
        rollback_point = await rollback_manager.create_rollback_point(action)
        action.rollback_point_id = rollback_point.get("id")

        # Execute action
        try:
            result = await executor.execute(
                action=action.action,
                target=action.target,
                parameters=action.parameters,
            )

            action.status = ActionStatus.COMPLETED
            action.result = result
            action.completed_at = datetime.utcnow()

            logger.info(
                "action_execution_completed",
                action_id=action_id,
                success=result.success,
            )

        except Exception as exec_error:
            action.status = ActionStatus.FAILED
            action.error = str(exec_error)
            action.completed_at = datetime.utcnow()

            logger.error(
                "action_execution_failed",
                action_id=action_id,
                error=str(exec_error),
            )

        # Log to audit service
        await log_to_audit(
            action_id=action_id,
            user_id=user_id,
            action="execute",
            details={
                "status": action.status.value,
                "success": action.result.success if action.result else False,
                "error": action.error,
            },
        )

        return action

    except HTTPException:
        raise
    except Exception as e:
        logger.error("action_execution_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Action execution failed: {str(e)}",
        )


@app.post("/actions/{action_id}/rollback", response_model=RollbackResult)
async def rollback_action(action_id: str, user_id: str, user_roles: List[str]):
    """Rollback a completed action."""
    try:
        logger.info(
            "rollback_started",
            action_id=action_id,
            user_id=user_id,
        )

        if action_id not in action_store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Action not found",
            )

        action = action_store[action_id]

        if not action.rollback_point_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No rollback point available for this action",
            )

        # Execute rollback
        result = await rollback_manager.rollback(
            rollback_point_id=action.rollback_point_id,
            action=action,
        )

        # Update action status
        action.status = ActionStatus.ROLLED_BACK
        action.rolled_back_at = datetime.utcnow()
        action.rolled_back_by = user_id

        # Log to audit
        await log_to_audit(
            action_id=action_id,
            user_id=user_id,
            action="rollback",
            details={
                "rollback_point_id": action.rollback_point_id,
                "success": result.success,
            },
        )

        logger.info(
            "rollback_completed",
            action_id=action_id,
            success=result.success,
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error("rollback_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rollback failed: {str(e)}",
        )


@app.get("/actions/{action_id}", response_model=ActionResponse)
async def get_action(action_id: str):
    """Get action details by ID."""
    if action_id not in action_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action not found",
        )
    return action_store[action_id]


@app.get("/actions", response_model=List[ActionResponse])
async def list_actions(
    user_id: Optional[str] = None,
    status: Optional[ActionStatus] = None,
    limit: int = 50,
    offset: int = 0,
):
    """List actions with optional filters."""
    actions = list(action_store.values())

    if user_id:
        actions = [a for a in actions if a.requested_by == user_id]

    if status:
        actions = [a for a in actions if a.status == status]

    # Sort by created_at descending
    actions.sort(key=lambda x: x.created_at, reverse=True)

    return actions[offset : offset + limit]


async def validate_with_policy_engine(action_req: ActionRequest) -> Dict[str, Any]:
    """Validate action against Policy Engine."""
    try:
        settings = get_settings()
        response = await http_client.post(
            f"{settings.policy_engine_url}/policies/check",
            json={
                "action": action_req.action,
                "target": action_req.target,
                "user_id": action_req.user_id,
                "user_roles": action_req.user_roles,
                "parameters": action_req.parameters,
            },
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        logger.error("policy_engine_communication_error", error=str(e))
        # Fail open for safety, but log the error
        return {"allowed": True, "requires_approval": True, "approvers": ["admin"]}


async def validate_execution_permissions(
    action_id: str, user_id: str, user_roles: List[str]
) -> Dict[str, Any]:
    """Validate user can execute the action."""
    try:
        settings = get_settings()
        response = await http_client.post(
            f"{settings.policy_engine_url}/policies/validate-execution",
            json={
                "action_id": action_id,
                "user_id": user_id,
                "user_roles": user_roles,
            },
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        logger.error("policy_validation_error", error=str(e))
        return {"allowed": False}


async def log_to_audit(
    action_id: str, user_id: str, action: str, details: Dict[str, Any]
):
    """Log action to Audit Service."""
    try:
        settings = get_settings()
        await http_client.post(
            f"{settings.audit_service_url}/audit/log",
            json={
                "action_id": action_id,
                "user_id": user_id,
                "action": action,
                "service": "action-engine",
                "details": details,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
    except httpx.HTTPError as e:
        logger.error("audit_logging_failed", error=str(e))


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(app, host="0.0.0.0", port=settings.service_port)
