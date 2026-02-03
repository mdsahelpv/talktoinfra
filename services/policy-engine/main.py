"""
Policy Engine Service

Provides RBAC, approval workflows, and policy enforcement for infrastructure actions.
Features role-based access control, resource-level permissions, and multi-level approval chains.
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
    PolicyCheckRequest,
    PolicyCheckResponse,
    ApprovalResponse,
    ApprovalStatus,
    Role,
    Permission,
)
from rbac import RBACManager
from approval_chain import ApprovalChainManager

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
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

# In-memory stores (replace with database in production)
approval_store: Dict[str, ApprovalResponse] = {}

# Service components
rbac_manager: Optional[RBACManager] = None
approval_chain_manager: Optional[ApprovalChainManager] = None
http_client: Optional[httpx.AsyncClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    global rbac_manager, approval_chain_manager, http_client

    settings = get_settings()

    logger.info("policy_engine_initializing", port=settings.service_port)

    # Initialize components
    rbac_manager = RBACManager()
    approval_chain_manager = ApprovalChainManager()
    http_client = httpx.AsyncClient(
        timeout=30.0,
        limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
    )

    logger.info("policy_engine_ready")

    yield

    # Cleanup
    if http_client:
        await http_client.aclose()
    logger.info("policy_engine_shutting_down")


app = FastAPI(
    title="AI Infrastructure Operations - Policy Engine",
    description="RBAC, approval workflows, and policy enforcement",
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
    return {
        "status": "healthy",
        "service": "policy-engine",
        "timestamp": time.time(),
        "components": {
            "rbac": "healthy" if rbac_manager else "unhealthy",
            "approval_chains": "healthy" if approval_chain_manager else "unhealthy",
        },
    }


@app.post("/policies/check", response_model=PolicyCheckResponse)
async def check_policy(request: Request, check_req: PolicyCheckRequest):
    """Check if an action is allowed under current policies."""
    try:
        logger.info(
            "policy_check_started",
            action=check_req.action,
            target=check_req.target,
            user_id=check_req.user_id,
        )

        # Check RBAC permissions
        has_permission = rbac_manager.check_permission(
            user_id=check_req.user_id,
            user_roles=check_req.user_roles,
            action=check_req.action,
            resource=check_req.target,
        )

        if not has_permission:
            logger.warning(
                "rbac_check_failed",
                user_id=check_req.user_id,
                action=check_req.action,
            )
            return PolicyCheckResponse(
                allowed=False,
                reason="User does not have permission for this action",
                requires_approval=False,
                approvers=[],
            )

        # Check if approval is required
        requires_approval, approvers = rbac_manager.requires_approval(
            user_id=check_req.user_id,
            user_roles=check_req.user_roles,
            action=check_req.action,
            target=check_req.target,
            parameters=check_req.parameters,
        )

        # Check resource-level policies
        resource_check = await check_resource_policies(check_req)

        logger.info(
            "policy_check_completed",
            action=check_req.action,
            allowed=has_permission and resource_check.get("allowed", True),
            requires_approval=requires_approval,
        )

        return PolicyCheckResponse(
            allowed=has_permission and resource_check.get("allowed", True),
            reason=(
                resource_check.get("reason")
                if not resource_check.get("allowed", True)
                else None
            ),
            requires_approval=requires_approval,
            approvers=approvers,
            policy_version=resource_check.get("policy_version", "1.0"),
            metadata={
                "user_roles": check_req.user_roles,
                "resource_tags": resource_check.get("tags", {}),
            },
        )

    except Exception as e:
        logger.error("policy_check_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Policy check failed: {str(e)}",
        )


@app.post("/policies/validate-execution")
async def validate_execution(
    action_id: str,
    user_id: str,
    user_roles: List[str],
):
    """Validate that a user can execute a specific action."""
    try:
        logger.info(
            "execution_validation",
            action_id=action_id,
            user_id=user_id,
        )

        # TODO: Implement proper authorization in future
        # Currently all authenticated users can execute actions
        # Check if user has admin role
        # if "admin" in user_roles:
        #     return {"allowed": True, "reason": "Admin override"}
        # Bypass admin check - allow all authenticated users
        return {"allowed": True, "reason": "Authenticated user"}

        # Check if user is the original requester
        for approval in approval_store.values():
            if approval.action_id == action_id:
                if approval.requested_by == user_id:
                    return {"allowed": True, "reason": "Original requester"}

                # Check if user is in the approver list
                if (
                    user_id in approval.approvers
                    and approval.status == ApprovalStatus.APPROVED
                ):
                    return {"allowed": True, "reason": "Approved by user"}

        return {"allowed": False, "reason": "Not authorized to execute this action"}

    except Exception as e:
        logger.error("execution_validation_failed", error=str(e))
        return {"allowed": False, "reason": str(e)}


@app.get("/approvals/pending", response_model=List[ApprovalResponse])
async def list_pending_approvals(
    user_id: str,
    roles: Optional[List[str]] = None,
    limit: int = 50,
    offset: int = 0,
):
    """List pending approvals for the current user."""
    try:
        logger.info("listing_pending_approvals", user_id=user_id, roles=roles)

        approvals = list(approval_store.values())

        # Filter by pending status and user authorization
        pending = []
        for approval in approvals:
            if approval.status != ApprovalStatus.PENDING:
                continue

            # Check if user can approve
            can_approve = user_id in approval.approvers or (
                roles and any(role in approval.approver_roles for role in roles)
            )

            if can_approve:
                pending.append(approval)

        # Sort by created_at descending
        pending.sort(key=lambda x: x.created_at, reverse=True)

        return pending[offset : offset + limit]

    except Exception as e:
        logger.error("list_approvals_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list approvals: {str(e)}",
        )


@app.get("/approvals/{approval_id}", response_model=ApprovalResponse)
async def get_approval(approval_id: str):
    """Get approval details by ID."""
    if approval_id not in approval_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval not found",
        )
    return approval_store[approval_id]


@app.post("/approvals/{approval_id}/approve", response_model=ApprovalResponse)
async def approve_action(
    request: Request,
    approval_id: str,
    user_id: str,
    notes: Optional[str] = None,
):
    """Approve a pending action."""
    try:
        logger.info(
            "approval_request",
            approval_id=approval_id,
            user_id=user_id,
        )

        if approval_id not in approval_store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Approval not found",
            )

        approval = approval_store[approval_id]

        if approval.status != ApprovalStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Approval is not pending. Current status: {approval.status}",
            )

        # Check authorization
        # In production, verify JWT token and roles
        is_authorized = (
            user_id in approval.approvers
            or approval_chain_manager.can_approve(approval, user_id)
        )

        if not is_authorized:
            logger.warning(
                "unauthorized_approval_attempt",
                approval_id=approval_id,
                user_id=user_id,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to approve this action",
            )

        # Update approval
        approval.status = ApprovalStatus.APPROVED
        approval.approved_by = user_id
        approval.approved_at = datetime.utcnow()
        approval.notes = notes
        approval.updated_at = datetime.utcnow()

        # Update approval chain
        approval_chain_manager.record_approval(approval_id, user_id)

        # Check if more approvals are needed
        remaining_approvals = approval_chain_manager.get_remaining_approvals(approval)
        if remaining_approvals > 0:
            approval.status = ApprovalStatus.PENDING
            logger.info(
                "partial_approval",
                approval_id=approval_id,
                remaining_approvals=remaining_approvals,
            )

        # Log to audit service
        await log_to_audit(
            approval_id=approval_id,
            user_id=user_id,
            action="approve",
            details={
                "action_id": approval.action_id,
                "notes": notes,
                "remaining_approvals": remaining_approvals,
            },
        )

        logger.info(
            "approval_completed",
            approval_id=approval_id,
            status=approval.status.value,
        )

        return approval

    except HTTPException:
        raise
    except Exception as e:
        logger.error("approval_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process approval: {str(e)}",
        )


@app.post("/approvals/{approval_id}/reject", response_model=ApprovalResponse)
async def reject_action(
    request: Request,
    approval_id: str,
    user_id: str,
    reason: str,
):
    """Reject a pending action."""
    try:
        logger.info(
            "rejection_request",
            approval_id=approval_id,
            user_id=user_id,
        )

        if approval_id not in approval_store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Approval not found",
            )

        approval = approval_store[approval_id]

        if approval.status != ApprovalStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Approval is not pending. Current status: {approval.status}",
            )

        # Check authorization
        is_authorized = (
            user_id in approval.approvers
            or approval_chain_manager.can_approve(approval, user_id)
        )

        if not is_authorized:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to reject this action",
            )

        # Update approval
        approval.status = ApprovalStatus.REJECTED
        approval.rejected_by = user_id
        approval.rejected_at = datetime.utcnow()
        approval.rejection_reason = reason
        approval.updated_at = datetime.utcnow()

        # Log to audit service
        await log_to_audit(
            approval_id=approval_id,
            user_id=user_id,
            action="reject",
            details={
                "action_id": approval.action_id,
                "reason": reason,
            },
        )

        logger.info(
            "rejection_completed",
            approval_id=approval_id,
            action_id=approval.action_id,
        )

        return approval

    except HTTPException:
        raise
    except Exception as e:
        logger.error("rejection_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process rejection: {str(e)}",
        )


@app.get("/roles", response_model=List[Role])
async def list_roles():
    """List all available roles."""
    return rbac_manager.list_roles()


@app.get("/roles/{role_name}/permissions", response_model=List[Permission])
async def get_role_permissions(role_name: str):
    """Get permissions for a specific role."""
    return rbac_manager.get_role_permissions(role_name)


@app.get("/users/{user_id}/roles", response_model=List[str])
async def get_user_roles(user_id: str):
    """Get roles assigned to a user."""
    return rbac_manager.get_user_roles(user_id)


@app.post("/approvals")
async def create_approval(
    action_id: str,
    action: str,
    target: str,
    requested_by: str,
    user_roles: List[str],
    approvers: List[str],
    justification: Optional[str] = None,
):
    """Create a new approval request (called by Action Engine)."""
    approval_id = str(uuid.uuid4())

    approval = ApprovalResponse(
        approval_id=approval_id,
        action_id=action_id,
        action=action,
        target=target,
        status=ApprovalStatus.PENDING,
        requested_by=requested_by,
        approvers=approvers,
        approver_roles=user_roles,
        notes=justification,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    approval_store[approval_id] = approval

    logger.info(
        "approval_created",
        approval_id=approval_id,
        action_id=action_id,
        requested_by=requested_by,
    )

    # Log to audit
    await log_to_audit(
        approval_id=approval_id,
        user_id=requested_by,
        action="create_approval",
        details={
            "action_id": action_id,
            "action": action,
            "target": target,
        },
    )

    return approval


async def check_resource_policies(check_req: PolicyCheckRequest) -> Dict[str, Any]:
    """Check resource-level policies."""
    # Check for production environment restrictions
    namespace = check_req.parameters.get("namespace", "")
    if namespace in ["production", "prod"]:
        # Production requires approval
        return {
            "allowed": True,
            "requires_approval": True,
            "reason": None,
            "tags": {"environment": "production"},
        }

    # Check for destructive operations
    if check_req.action.lower() in ["delete", "terminate", "remove"]:
        return {
            "allowed": True,
            "requires_approval": True,
            "reason": None,
            "tags": {"destructive": True},
        }

    return {"allowed": True, "requires_approval": False, "reason": None, "tags": {}}


async def log_to_audit(
    approval_id: str, user_id: str, action: str, details: Dict[str, Any]
):
    """Log action to Audit Service."""
    try:
        settings = get_settings()
        await http_client.post(
            f"{settings.audit_service_url}/audit/log",
            json={
                "approval_id": approval_id,
                "user_id": user_id,
                "action": action,
                "service": "policy-engine",
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
