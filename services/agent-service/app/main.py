"""
Agent Service - Main FastAPI Application
API endpoints for agent execution, task management, and approvals.
"""

import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import (
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    BackgroundTasks,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import structlog

# Import agent components
from app.agents.registry import get_agent_registry, list_available_agents
from app.agents.query_agent import get_query_agent
from app.agents.analysis_agent import get_analysis_agent, AnalysisType
from app.agents.planning_agent import get_planning_agent
from app.agents.action_agent import get_action_agent, ActionStatus

# Import utilities
from app.config import get_settings

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

# In-memory task storage (replace with database in production)
_task_store: Dict[str, Dict[str, Any]] = {}
_approval_store: Dict[str, Dict[str, Any]] = {}
_active_connections: List[WebSocket] = []


# Pydantic Models for API


class ExecuteRequest(BaseModel):
    """Request to execute an agent task."""

    agent_type: str = Field(
        ..., description="Type of agent: query, analysis, planning, action"
    )
    query: str = Field(
        ..., min_length=1, max_length=10000, description="User query or command"
    )
    namespace: str = Field(default="default", description="Kubernetes namespace")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Additional parameters"
    )
    context: Dict[str, Any] = Field(
        default_factory=dict, description="Additional context"
    )
    dry_run: bool = Field(default=True, description="Perform dry-run for action agents")
    auto_execute: bool = Field(
        default=False, description="Auto-execute if safe (read-only only)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "agent_type": "query",
                "query": "Show me pods in default namespace",
                "namespace": "default",
                "auto_execute": True,
            }
        }


class ExecuteResponse(BaseModel):
    """Response from agent execution."""

    task_id: str
    agent_type: str
    status: str
    response: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    requires_approval: bool = False
    approval_id: Optional[str] = None
    dry_run_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: int
    timestamp: str


class TaskStatusResponse(BaseModel):
    """Response for task status query."""

    task_id: str
    status: str
    agent_type: str
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ApprovalRequest(BaseModel):
    """Request to approve an action."""

    approved_by: str = Field(..., description="User ID of approver")
    notes: Optional[str] = Field(default=None, description="Approval notes")


class ApprovalResponse(BaseModel):
    """Response from approval action."""

    approval_id: str
    action_id: str
    status: str
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    notes: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


class AgentInfoResponse(BaseModel):
    """Response with agent information."""

    agents: List[Dict[str, Any]]
    total: int


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
    version: str
    timestamp: str
    uptime_seconds: int


# Application lifespan handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("agent_service_starting")

    # Initialize agent registry
    registry = get_agent_registry()
    logger.info("agent_registry_initialized", agents=len(registry.list_agents()))

    yield

    # Cleanup
    logger.info("agent_service_shutting_down")


# Create FastAPI app
app = FastAPI(
    title="Agent Service",
    description="AI-powered agents for infrastructure management with safety controls",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Helper functions


def _generate_task_id() -> str:
    """Generate unique task ID."""
    return f"task-{uuid.uuid4().hex[:12]}"


def _generate_approval_id() -> str:
    """Generate unique approval ID."""
    return f"approval-{uuid.uuid4().hex[:12]}"


async def _broadcast_task_update(
    task_id: str, status: str, result: Optional[Dict] = None
):
    """Broadcast task update to all connected WebSocket clients."""
    message = {
        "type": "task_update",
        "task_id": task_id,
        "status": status,
        "timestamp": datetime.utcnow().isoformat(),
        "result": result,
    }

    disconnected = []
    for ws in _active_connections:
        try:
            await ws.send_json(message)
        except:
            disconnected.append(ws)

    # Remove disconnected clients
    for ws in disconnected:
        if ws in _active_connections:
            _active_connections.remove(ws)


# API Endpoints


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "agent-service",
        "version": "1.0.0",
        "description": "AI-powered agents for infrastructure management",
        "docs_url": "/docs",
        "health": "/health",
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        service="agent-service",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat(),
        uptime_seconds=0,  # Would track actual uptime
    )


@app.get("/api/v1/agents", response_model=AgentInfoResponse)
async def list_agents():
    """
    List all available agents and their capabilities.

    Returns information about all registered agents including:
    - Agent types
    - Capabilities
    - Safety properties (read-only, requires approval, etc.)
    """
    try:
        agents = list_available_agents()
        return AgentInfoResponse(
            agents=agents,
            total=len(agents),
        )
    except Exception as e:
        logger.error("list_agents_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list agents: {str(e)}")


@app.post("/api/v1/agents/execute", response_model=ExecuteResponse)
async def execute_agent(
    request: ExecuteRequest,
    background_tasks: BackgroundTasks,
):
    """
    Execute an agent task.

    This endpoint routes the request to the appropriate agent:
    - **query**: Read-only queries (pods, logs, resources)
    - **analysis**: Insights, patterns, root cause analysis
    - **planning**: Create execution plans with risk assessment
    - **action**: Infrastructure modifications (requires approval)

    **Safety Rules:**
    - Query/Analysis/Planning agents are read-only and can auto-execute
    - Action agents ALWAYS require dry-run + approval
    - No auto-execution for infrastructure modifications
    """
    task_id = _generate_task_id()
    start_time = datetime.utcnow()

    logger.info(
        "execute_request",
        task_id=task_id,
        agent_type=request.agent_type,
        query=request.query[:100],
        namespace=request.namespace,
    )

    try:
        # Validate agent type
        agent_type_str = request.agent_type.lower()
        valid_types = ["query", "analysis", "planning", "action"]

        if agent_type_str not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid agent_type: {request.agent_type}. Valid types: {valid_types}",
            )

        # Store initial task state
        _task_store[task_id] = {
            "task_id": task_id,
            "agent_type": agent_type_str,
            "query": request.query,
            "status": "executing",
            "created_at": start_time.isoformat(),
            "updated_at": start_time.isoformat(),
            "result": None,
            "error": None,
        }

        # Route to appropriate agent
        if agent_type_str == "query":
            result = await _execute_query_agent(request, task_id)
        elif agent_type_str == "analysis":
            result = await _execute_analysis_agent(request, task_id)
        elif agent_type_str == "planning":
            result = await _execute_planning_agent(request, task_id)
        elif agent_type_str == "action":
            result = await _execute_action_agent(request, task_id)
        else:
            raise HTTPException(
                status_code=400, detail=f"Unknown agent type: {agent_type_str}"
            )

        # Calculate execution time
        execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        # Update task store
        _task_store[task_id].update(
            {
                "status": result.get("status", "completed"),
                "updated_at": datetime.utcnow().isoformat(),
                "result": result,
                "execution_time_ms": execution_time,
            }
        )

        # Broadcast update
        background_tasks.add_task(
            _broadcast_task_update,
            task_id,
            result.get("status", "completed"),
            result,
        )

        return ExecuteResponse(
            task_id=task_id,
            agent_type=agent_type_str,
            status=result.get("status", "completed"),
            response=result.get("response"),
            result=result.get("result"),
            requires_approval=result.get("requires_approval", False),
            approval_id=result.get("approval_id"),
            dry_run_result=result.get("dry_run_result"),
            error=result.get("error"),
            execution_time_ms=execution_time,
            timestamp=datetime.utcnow().isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("execute_failed", task_id=task_id, error=str(e))

        # Update task store with error
        _task_store[task_id].update(
            {
                "status": "failed",
                "updated_at": datetime.utcnow().isoformat(),
                "error": str(e),
            }
        )

        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")


async def _execute_query_agent(request: ExecuteRequest, task_id: str) -> Dict[str, Any]:
    """Execute query agent."""
    agent = get_query_agent()

    result = await agent.execute_query(request.query)

    if result.get("success"):
        return {
            "status": "completed",
            "response": f"Query executed successfully. Found {len(result.get('result', [])) if isinstance(result.get('result'), list) else 'results'}.",
            "result": result,
            "requires_approval": False,
        }
    else:
        return {
            "status": "failed",
            "error": result.get("error", "Query failed"),
            "result": result,
            "requires_approval": False,
        }


async def _execute_analysis_agent(
    request: ExecuteRequest, task_id: str
) -> Dict[str, Any]:
    """Execute analysis agent."""
    agent = get_analysis_agent()

    # Detect analysis type from query or use default
    analysis_type = None
    query_lower = request.query.lower()

    if "pattern" in query_lower or "correlation" in query_lower:
        analysis_type = AnalysisType.PATTERN
    elif "root cause" in query_lower or "why" in query_lower:
        analysis_type = AnalysisType.ROOT_CAUSE
    elif "trend" in query_lower or "over time" in query_lower:
        analysis_type = AnalysisType.TREND
    elif "anomaly" in query_lower or "unusual" in query_lower:
        analysis_type = AnalysisType.ANOMALY
    elif "predict" in query_lower or "forecast" in query_lower:
        analysis_type = AnalysisType.PREDICTION

    result = await agent.analyze(
        query=request.query,
        context={"namespace": request.namespace, **request.context},
        analysis_type=analysis_type,
    )

    return {
        "status": "completed",
        "response": result.summary,
        "result": result.to_dict(),
        "requires_approval": False,
    }


async def _execute_planning_agent(
    request: ExecuteRequest, task_id: str
) -> Dict[str, Any]:
    """Execute planning agent."""
    agent = get_planning_agent()

    # Extract action details from query or parameters
    action = request.parameters.get("action", "update")
    target = request.parameters.get("target", "unknown")
    resource_type = request.parameters.get("resource_type", "deployment")

    plan = await agent.create_plan(
        action=action,
        target=target,
        resource_type=resource_type,
        namespace=request.namespace,
        parameters=request.parameters,
        context=request.context,
    )

    return {
        "status": "completed",
        "response": f"Plan created: {plan.title}. {plan.total_steps} steps, {plan.risk_assessment.overall_risk} risk.",
        "result": plan.to_dict(),
        "requires_approval": False,  # Planning is read-only
    }


async def _execute_action_agent(
    request: ExecuteRequest, task_id: str
) -> Dict[str, Any]:
    """Execute action agent."""
    agent = get_action_agent()

    # Extract action details
    action = request.parameters.get("action", "update")
    target = request.parameters.get("target", "unknown")
    resource_type = request.parameters.get("resource_type", "deployment")

    # Execute action (always requires approval)
    result = await agent.execute_action(
        action=action,
        target=target,
        resource_type=resource_type,
        namespace=request.namespace,
        parameters=request.parameters,
        requested_by=request.context.get("user_id", "anonymous"),
        skip_approval=False,  # NEVER skip approval
    )

    # If awaiting approval, store the action
    if result.status == ActionStatus.AWAITING_APPROVAL:
        approval_id = result.approval_id or _generate_approval_id()

        _approval_store[approval_id] = {
            "approval_id": approval_id,
            "action_id": result.action_id,
            "task_id": task_id,
            "status": "pending",
            "action": action,
            "target": target,
            "namespace": request.namespace,
            "dry_run_result": (
                result.dry_run_result.to_dict() if result.dry_run_result else None
            ),
            "impact_analysis": result.impact_analysis.to_dict(),
            "requested_at": datetime.utcnow().isoformat(),
        }

        return {
            "status": "awaiting_approval",
            "response": f"Action {action} on {target} requires approval. Review the dry-run results and impact analysis.",
            "result": result.to_dict(),
            "requires_approval": True,
            "approval_id": approval_id,
            "dry_run_result": (
                result.dry_run_result.to_dict() if result.dry_run_result else None
            ),
        }

    # If dry-run failed
    if result.status == ActionStatus.FAILED and result.dry_run_result:
        return {
            "status": "failed",
            "error": result.execution_error or "Dry-run failed",
            "result": result.to_dict(),
            "requires_approval": False,
            "dry_run_result": (
                result.dry_run_result.to_dict() if result.dry_run_result else None
            ),
        }

    return {
        "status": result.status.value,
        "response": f"Action {action} on {target} - {result.status.value}",
        "result": result.to_dict(),
        "requires_approval": result.requires_approval,
    }


@app.get("/api/v1/agents/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    Get the status of a task.

    Returns current status and results for a previously submitted task.
    """
    if task_id not in _task_store:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    task = _task_store[task_id]

    return TaskStatusResponse(
        task_id=task_id,
        status=task.get("status", "unknown"),
        agent_type=task.get("agent_type", "unknown"),
        created_at=task.get("created_at"),
        updated_at=task.get("updated_at"),
        completed_at=task.get("completed_at"),
        result=task.get("result"),
        error=task.get("error"),
    )


@app.post(
    "/api/v1/agents/approvals/{approval_id}/approve", response_model=ApprovalResponse
)
async def approve_action(
    approval_id: str,
    request: ApprovalRequest,
    background_tasks: BackgroundTasks,
):
    """
    Approve a pending action.

    This endpoint approves an action that is awaiting approval.
    Once approved, the action will be executed.

    **IMPORTANT:** Only approvers with proper authorization can approve actions.
    """
    if approval_id not in _approval_store:
        raise HTTPException(status_code=404, detail=f"Approval {approval_id} not found")

    approval = _approval_store[approval_id]

    if approval.get("status") != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Approval {approval_id} is not pending (status: {approval.get('status')})",
        )

    try:
        # Get the action agent and approve
        agent = get_action_agent()
        action_result = await agent.approve_action(
            action_id=approval["action_id"],
            approved_by=request.approved_by,
            notes=request.notes,
        )

        # Update approval store
        approval.update(
            {
                "status": "approved",
                "approved_by": request.approved_by,
                "approved_at": datetime.utcnow().isoformat(),
                "notes": request.notes,
                "result": action_result.to_dict(),
            }
        )

        # Update associated task
        task_id = approval.get("task_id")
        if task_id and task_id in _task_store:
            _task_store[task_id].update(
                {
                    "status": action_result.status.value,
                    "updated_at": datetime.utcnow().isoformat(),
                    "completed_at": (
                        datetime.utcnow().isoformat()
                        if action_result.status
                        in [
                            ActionStatus.COMPLETED,
                            ActionStatus.FAILED,
                            ActionStatus.ROLLED_BACK,
                        ]
                        else None
                    ),
                    "result": action_result.to_dict(),
                }
            )

            # Broadcast update
            background_tasks.add_task(
                _broadcast_task_update,
                task_id,
                action_result.status.value,
                action_result.to_dict(),
            )

        logger.info(
            "action_approved",
            approval_id=approval_id,
            action_id=approval["action_id"],
            approved_by=request.approved_by,
        )

        return ApprovalResponse(
            approval_id=approval_id,
            action_id=approval["action_id"],
            status="approved",
            approved_by=request.approved_by,
            approved_at=datetime.utcnow().isoformat(),
            notes=request.notes,
            result=action_result.to_dict(),
        )

    except Exception as e:
        logger.error("approval_failed", approval_id=approval_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Approval failed: {str(e)}")


@app.post("/api/v1/agents/approvals/{approval_id}/reject")
async def reject_action(
    approval_id: str,
    rejected_by: str,
    reason: str,
    background_tasks: BackgroundTasks,
):
    """
    Reject a pending action.

    This endpoint rejects an action that is awaiting approval.
    Once rejected, the action will not be executed.
    """
    if approval_id not in _approval_store:
        raise HTTPException(status_code=404, detail=f"Approval {approval_id} not found")

    approval = _approval_store[approval_id]

    if approval.get("status") != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Approval {approval_id} is not pending (status: {approval.get('status')})",
        )

    try:
        # Get the action agent and reject
        agent = get_action_agent()
        action_result = await agent.reject_action(
            action_id=approval["action_id"],
            rejected_by=rejected_by,
            reason=reason,
        )

        # Update approval store
        approval.update(
            {
                "status": "rejected",
                "rejected_by": rejected_by,
                "rejected_at": datetime.utcnow().isoformat(),
                "rejection_reason": reason,
                "result": action_result.to_dict(),
            }
        )

        # Update associated task
        task_id = approval.get("task_id")
        if task_id and task_id in _task_store:
            _task_store[task_id].update(
                {
                    "status": "rejected",
                    "updated_at": datetime.utcnow().isoformat(),
                    "completed_at": datetime.utcnow().isoformat(),
                    "error": f"Rejected by {rejected_by}: {reason}",
                }
            )

            # Broadcast update
            background_tasks.add_task(
                _broadcast_task_update,
                task_id,
                "rejected",
            )

        logger.info(
            "action_rejected",
            approval_id=approval_id,
            action_id=approval["action_id"],
            rejected_by=rejected_by,
            reason=reason,
        )

        return {
            "approval_id": approval_id,
            "action_id": approval["action_id"],
            "status": "rejected",
            "rejected_by": rejected_by,
            "rejected_at": datetime.utcnow().isoformat(),
            "reason": reason,
        }

    except Exception as e:
        logger.error("rejection_failed", approval_id=approval_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Rejection failed: {str(e)}")


@app.get("/api/v1/agents/approvals/pending")
async def list_pending_approvals():
    """
    List all pending approvals.

    Returns all actions awaiting approval with their details.
    """
    pending = [
        {
            "approval_id": aid,
            "action": a["action"],
            "target": a["target"],
            "namespace": a["namespace"],
            "requested_at": a["requested_at"],
            "dry_run_summary": (
                a.get("dry_run_result", {}).get("changes_preview", [])
                if a.get("dry_run_result")
                else []
            ),
        }
        for aid, a in _approval_store.items()
        if a.get("status") == "pending"
    ]

    return {
        "approvals": pending,
        "total": len(pending),
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates.

    Connect to this endpoint to receive real-time updates about:
    - Task status changes
    - Approval requests
    - Execution progress
    """
    await websocket.accept()
    _active_connections.append(websocket)

    try:
        # Send initial connection message
        await websocket.send_json(
            {
                "type": "connected",
                "message": "Connected to Agent Service WebSocket",
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        # Keep connection alive and handle client messages
        while True:
            try:
                data = await websocket.receive_json()

                # Handle subscription requests
                if data.get("action") == "subscribe":
                    await websocket.send_json(
                        {
                            "type": "subscribed",
                            "channels": data.get("channels", ["all"]),
                        }
                    )

                # Handle ping
                elif data.get("action") == "ping":
                    await websocket.send_json(
                        {
                            "type": "pong",
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )

            except WebSocketDisconnect:
                break
            except Exception as e:
                await websocket.send_json(
                    {
                        "type": "error",
                        "error": str(e),
                    }
                )

    except WebSocketDisconnect:
        pass
    finally:
        if websocket in _active_connections:
            _active_connections.remove(websocket)


# Error handlers


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    logger.error("http_exception", status=exc.status_code, detail=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error("unhandled_exception", error=str(exc))
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=settings.environment == "development",
    )
