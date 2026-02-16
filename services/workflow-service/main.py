"""
Workflow Service - Multi-Step Workflow Engine

Enables complex infrastructure workflows:
- Deploy with database migration
- Blue-green deployments
- Rollback support
- Approval chains
- Conditional execution
"""

import time
import uuid
from contextlib import asynccontextmanager
from typing import Dict, List, Any, Optional
from enum import Enum

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import get_settings
from redis_client import get_redis_client, init_redis_client, close_redis_client
from state_cache import RedisStateCache
from tasks import (
    execute_workflow_task,
    set_storage_refs,
    workflow_executions,
    workflow_definitions,
)
from rollback import get_rollback_engine, ExecutionHistory

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


# ============ Enums ============


class WorkflowStatus(str, Enum):
    """Workflow execution status."""

    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLING_BACK = "rolling_back"


class StepType(str, Enum):
    """Types of workflow steps."""

    ACTION = "action"  # Execute an action (K8s deployment, etc.)
    CONDITION = "condition"  # Conditional branching
    WAIT = "wait"  # Wait for duration or event
    APPROVAL = "approval"  # Require approval to proceed
    PARALLEL = "parallel"  # Execute multiple steps in parallel
    NOTIFICATION = "notification"  # Send notification


class StepStatus(str, Enum):
    """Step execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING = "waiting"  # Waiting for approval/event


# ============ Pydantic Models ============


class WorkflowStep(BaseModel):
    """A single step in a workflow."""

    id: str = Field(default_factory=lambda: f"step_{uuid.uuid4().hex[:8]}")
    name: str
    type: StepType
    description: str = ""
    order: int

    # Step configuration
    config: Dict[str, Any] = Field(default_factory=dict)

    # Conditional execution
    condition: Optional[str] = None  # JSONPath expression
    condition_values: Dict[str, Any] = Field(default_factory=dict)

    # Error handling
    on_failure: str = "stop"  # "stop", "continue", "rollback"
    retry_count: int = 0
    retry_delay_seconds: int = 60

    # Parallel execution (for PARALLEL type)
    parallel_steps: List["WorkflowStep"] = []

    # Execution state
    status: StepStatus = StepStatus.PENDING
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class WorkflowDefinition(BaseModel):
    """Workflow template definition."""

    id: str = Field(default_factory=lambda: f"wf_{uuid.uuid4().hex[:8]}")
    name: str
    description: str = ""
    version: int = 1

    # Workflow steps (ordered)
    steps: List[WorkflowStep] = []

    # Entry point (first step ID or name)
    entry_point: str = ""

    # Workflow metadata
    created_by: str = ""
    tags: List[str] = []
    is_template: bool = False

    # Parameters
    parameters: Dict[str, Any] = Field(default_factory=dict)
    parameter_schema: Dict[str, Any] = Field(default_factory=dict)


class WorkflowExecution(BaseModel):
    """A running instance of a workflow."""

    id: str = Field(default_factory=lambda: f"exec_{uuid.uuid4().hex[:8]}")
    workflow_id: str
    workflow_version: int

    # Execution state
    status: WorkflowStatus = WorkflowStatus.RUNNING
    current_step_id: Optional[str] = None

    # Execution context
    parameters: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)

    # Results
    results: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = []

    # Timestamps
    created_at: str = Field(
        default_factory=lambda: time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    )
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    # Audit
    created_by: str = ""
    approved_by: Optional[str] = None


# Forward reference for circular dependency
WorkflowStep.model_rebuild()


# ============ FastAPI App ============

settings = get_settings()

# Initialize Redis client and state cache
redis_client = get_redis_client()
state_cache = RedisStateCache(redis_client, ttl=settings.state_cache_ttl)

# Execution history storage (in-memory for now, can be backed by Redis/DB)
execution_histories: Dict[str, ExecutionHistory] = {}

app = FastAPI(
    title="Workflow Service",
    description="Multi-step workflow engine for infrastructure automation",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    logger.info("workflow_service_starting", port=settings.service_port)

    # Initialize Redis client
    try:
        redis_client = await init_redis_client(
            host=settings.redis_host, port=settings.redis_port, db=settings.redis_db
        )
        # Test Redis connection
        redis_client.ping()
        logger.info(
            "redis_connection_established",
            host=settings.redis_host,
            port=settings.redis_port,
        )
    except Exception as e:
        logger.warning("redis_connection_failed", error=str(e))

    # Set storage references for Celery tasks
    set_storage_refs(workflow_executions, workflow_definitions)

    yield

    # Close Redis connection on shutdown
    await close_redis_client()
    logger.info("workflow_service_stopping")


app.router.lifespan_context = lifespan


# ============ Health Check ============


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    redis_status = "healthy"
    try:
        redis_client.ping()
    except Exception as e:
        redis_status = f"unhealthy: {e}"

    return {
        "status": "healthy",
        "service": settings.service_name,
        "version": "1.0.0",
        "redis": redis_status,
    }


# ============ Workflow Definition CRUD ============


@app.post("/api/v1/workflows")
async def create_workflow(workflow: WorkflowDefinition) -> Dict[str, Any]:
    """Create a new workflow definition."""
    logger.info("creating_workflow", name=workflow.name)

    # Set entry point to first step if not specified
    if not workflow.entry_point and workflow.steps:
        workflow.entry_point = workflow.steps[0].id

    workflow_definitions[workflow.id] = workflow

    logger.info("workflow_created", id=workflow.id, name=workflow.name)
    return {"id": workflow.id, "workflow": workflow.model_dump()}


@app.get("/api/v1/workflows")
async def list_workflows(
    skip: int = 0,
    limit: int = 20,
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """List workflow definitions."""
    workflows = list(workflow_definitions.values())

    if tags:
        workflows = [w for w in workflows if any(t in w.tags for t in tags)]

    return {
        "items": [
            w.model_dump(exclude={"steps"}) for w in workflows[skip: skip + limit]
        ],
        "total": len(workflows),
        "skip": skip,
        "limit": limit,
    }


@app.get("/api/v1/workflows/{workflow_id}")
async def get_workflow(workflow_id: str) -> Dict[str, Any]:
    """Get a workflow definition by ID."""
    if workflow_id not in workflow_definitions:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return {"workflow": workflow_definitions[workflow_id].model_dump()}


@app.put("/api/v1/workflows/{workflow_id}")
async def update_workflow(
    workflow_id: str, workflow: WorkflowDefinition
) -> Dict[str, Any]:
    """Update a workflow definition."""
    if workflow_id not in workflow_definitions:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Increment version
    workflow.version = workflow_definitions[workflow_id].version + 1
    workflow_definitions[workflow_id] = workflow

    logger.info("workflow_updated", id=workflow_id, version=workflow.version)
    return {"id": workflow_id, "workflow": workflow.model_dump()}


@app.delete("/api/v1/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str) -> Dict[str, Any]:
    """Delete a workflow definition."""
    if workflow_id not in workflow_definitions:
        raise HTTPException(status_code=404, detail="Workflow not found")

    del workflow_definitions[workflow_id]
    logger.info("workflow_deleted", id=workflow_id)
    return {"status": "deleted", "id": workflow_id}


# ============ Workflow Execution ============


@app.post("/api/v1/workflows/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: str,
    parameters: Optional[Dict[str, Any]] = None,
    approved_by: Optional[str] = None,
) -> Dict[str, Any]:
    """Start a workflow execution synchronously."""
    if workflow_id not in workflow_definitions:
        raise HTTPException(status_code=404, detail="Workflow not found")

    workflow = workflow_definitions[workflow_id]

    # Create execution instance
    execution = WorkflowExecution(
        workflow_id=workflow_id,
        workflow_version=workflow.version,
        parameters=parameters or {},
        created_by=workflow.created_by,
        approved_by=approved_by,
    )

    # Add to execution store
    workflow_executions[execution.id] = execution

    logger.info(
        "workflow_execution_started",
        execution_id=execution.id,
        workflow_id=workflow_id,
    )

    # TODO: Start async execution (Celery task)
    # For now, return execution info
    return {
        "execution_id": execution.id,
        "status": execution.status,
        "created_at": execution.created_at,
    }


@app.post("/api/v1/workflows/{workflow_id}/execute-async")
async def execute_workflow_async(
    workflow_id: str,
    parameters: Optional[Dict[str, Any]] = None,
    approved_by: Optional[str] = None,
) -> Dict[str, Any]:
    """Start a workflow execution asynchronously using Celery.

    This endpoint triggers an async workflow execution and returns
    immediately with the execution ID and task ID for tracking.
    """
    if workflow_id not in workflow_definitions:
        raise HTTPException(status_code=404, detail="Workflow not found")

    workflow = workflow_definitions[workflow_id]

    # Create execution instance
    execution = WorkflowExecution(
        workflow_id=workflow_id,
        workflow_version=workflow.version,
        parameters=parameters or {},
        created_by=workflow.created_by,
        approved_by=approved_by,
    )

    # Add to execution store
    workflow_executions[execution.id] = execution

    # Cache initial state in Redis
    initial_state = {
        "execution_id": execution.id,
        "workflow_id": execution.workflow_id,
        "status": execution.status.value,
        "current_step_id": execution.current_step_id,
        "parameters": execution.parameters,
        "results": {},
        "errors": [],
        "steps": [
            {
                "id": step.id,
                "name": step.name,
                "status": step.status.value,
                "order": step.order,
            }
            for step in workflow.steps
        ],
        "total_steps": len(workflow.steps),
        "completed_steps": 0,
        "progress_percent": 0,
        "created_at": execution.created_at,
        "started_at": execution.started_at,
        "completed_at": None,
    }
    await state_cache.set_execution_state(workflow_id, execution.id, initial_state)

    logger.info(
        "workflow_async_execution_started",
        execution_id=execution.id,
        workflow_id=workflow_id,
    )

    # Trigger async Celery task
    task = execute_workflow_task.delay(workflow_id, execution.id)

    return {
        "execution_id": execution.id,
        "task_id": task.id,
        "status": execution.status,
        "created_at": execution.created_at,
        "message": "Workflow execution started asynchronously",
    }


@app.get("/api/v1/workflows/{workflow_id}/executions/{execution_id}/status")
async def get_execution_status(
    workflow_id: str,
    execution_id: str,
) -> Dict[str, Any]:
    """Get the status of a workflow execution.

    Returns the current execution state including:
    - Status (running, completed, failed, etc.)
    - Current step
    - Results so far
    - Errors (if any)
    """
    if workflow_id not in workflow_definitions:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Try to get from Redis cache first
    cached_state = await state_cache.get_execution_state(workflow_id, execution_id)
    if cached_state:
        logger.debug("execution_state_from_cache", execution_id=execution_id)
        return cached_state

    # Fall back to in-memory storage
    if execution_id not in workflow_executions:
        raise HTTPException(status_code=404, detail="Execution not found")

    execution = workflow_executions[execution_id]

    return {
        "execution_id": execution.id,
        "workflow_id": execution.workflow_id,
        "status": execution.status,
        "current_step_id": execution.current_step_id,
        "parameters": execution.parameters,
        "results": execution.results,
        "errors": execution.errors,
        "created_at": execution.created_at,
        "started_at": execution.started_at,
        "completed_at": execution.completed_at,
    }

    # Check if execution belongs to the workflow
    if execution.workflow_id != workflow_id:
        raise HTTPException(
            status_code=400,
            detail="Execution does not belong to the specified workflow",
        )

    return {
        "execution_id": execution.id,
        "workflow_id": execution.workflow_id,
        "status": execution.status,
        "current_step_id": execution.current_step_id,
        "parameters": execution.parameters,
        "results": execution.results,
        "errors": execution.errors,
        "created_at": execution.created_at,
        "started_at": execution.started_at,
        "completed_at": execution.completed_at,
    }


@app.get("/api/v1/executions/{execution_id}/task-status")
async def get_task_status(execution_id: str) -> Dict[str, Any]:
    """Get the Celery task status for an execution.

    Returns the Celery task status including:
    - Task state (PENDING, STARTED, SUCCESS, FAILURE, etc.)
    - Task result (if completed)
    - Task traceback (if failed)
    """
    # Find the task ID for this execution
    # In a production system, you'd store the task_id with the execution
    # For now, we need to find it from the execution's context
    task_id = None

    for key, value in workflow_executions.items():
        if key == execution_id:
            # Check if we stored a task_id
            task_id = getattr(value, "celery_task_id", None)
            break

    if task_id is None:
        raise HTTPException(
            status_code=404, detail="No Celery task found for this execution"
        )

    # Get task status from Celery
    from tasks import get_task_status as celery_get_status

    status_result = celery_get_status.delay(task_id)

    return {
        "execution_id": execution_id,
        "task_id": task_id,
        "celery_status": status_result.status,
    }


@app.get("/api/v1/executions")
async def list_executions(
    workflow_id: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
) -> Dict[str, Any]:
    """List workflow executions."""
    executions = list(workflow_executions.values())

    if workflow_id:
        executions = [e for e in executions if e.workflow_id == workflow_id]

    if status:
        executions = [e for e in executions if e.status.value == status]

    return {
        "items": [e.model_dump() for e in executions[skip: skip + limit]],
        "total": len(executions),
        "skip": skip,
        "limit": limit,
    }


@app.get("/api/v1/executions/{execution_id}")
async def get_execution(execution_id: str) -> Dict[str, Any]:
    """Get workflow execution details."""
    if execution_id not in workflow_executions:
        raise HTTPException(status_code=404, detail="Execution not found")

    return {"execution": workflow_executions[execution_id].model_dump()}


@app.post("/api/v1/executions/{execution_id}/cancel")
async def cancel_execution(execution_id: str) -> Dict[str, Any]:
    """Cancel a running workflow execution."""
    if execution_id not in workflow_executions:
        raise HTTPException(status_code=404, detail="Execution not found")

    execution = workflow_executions[execution_id]

    if execution.status not in [WorkflowStatus.RUNNING, WorkflowStatus.PAUSED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel execution in {execution.status.value} status",
        )

    execution.status = WorkflowStatus.CANCELLED
    execution.completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    logger.info("workflow_execution_cancelled", execution_id=execution_id)
    return {
        "execution_id": execution_id,
        "status": WorkflowStatus.CANCELLED.value,
    }


@app.post("/api/v1/executions/{execution_id}/rollback")
async def rollback_execution(execution_id: str) -> Dict[str, Any]:
    """Rollback a completed or failed workflow execution.

    Executes compensating actions for each step that was executed,
    in reverse order, to undo the workflow's effects.
    """
    if execution_id not in workflow_executions:
        raise HTTPException(status_code=404, detail="Execution not found")

    execution = workflow_executions[execution_id]

    if execution.status not in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED]:
        raise HTTPException(
            status_code=400, detail="Can only rollback completed or failed executions"
        )

    # Get the workflow definition
    workflow = workflow_definitions.get(execution.workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    execution.status = WorkflowStatus.ROLLING_BACK

    # Get the rollback engine
    rollback_engine = get_rollback_engine()

    # Get step results from execution
    step_results = execution.results

    # Execute rollback
    rollback_result = await rollback_engine.rollback_workflow(
        execution_id=execution_id,
        workflow_id=execution.workflow_id,
        steps=[step.model_dump() for step in workflow.steps],
        step_results=step_results,
        context=execution.context,
    )

    # Update execution status
    if rollback_result.get("failed_rollbacks"):
        execution.status = WorkflowStatus.FAILED
    else:
        execution.status = WorkflowStatus.COMPLETED

    execution.completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    logger.info(
        "workflow_execution_rollback_completed",
        execution_id=execution_id,
        steps_rolled_back=rollback_result.get("total_steps_rolled_back"),
        failed_rollbacks=len(rollback_result.get("failed_rollbacks", [])),
    )

    return {
        "execution_id": execution_id,
        "status": execution.status.value,
        "rollback_result": rollback_result,
    }


@app.get("/api/v1/executions/{execution_id}/history")
async def get_execution_history(execution_id: str) -> Dict[str, Any]:
    """Get the execution history for a workflow execution.

    Returns the complete history including:
    - All events that occurred during execution
    - Step results
    - Rollback history (if applicable)
    """
    if execution_id not in workflow_executions:
        raise HTTPException(status_code=404, detail="Execution not found")

    execution = workflow_executions[execution_id]

    # Get history from storage if available
    history = execution_histories.get(execution_id)

    if not history:
        # Create a new history from execution data
        history = ExecutionHistory(execution_id, execution.workflow_id)
        # Populate with existing events/results
        for step_id, result in execution.results.items():
            history.record_step_result(step_id, result)

    return {
        "execution_id": execution_id,
        "history": history.to_dict(),
    }


# ============ Workflow Templates ============

TEMPLATE_KUBERNETES_DEPLOYMENT = WorkflowDefinition(
    name="Kubernetes Deployment",
    description="Deploy an application to Kubernetes with health checks",
    steps=[
        WorkflowStep(
            name="Build Docker Image",
            type=StepType.ACTION,
            order=0,
            config={"action": "build_docker", "dockerfile": "Dockerfile"},
        ),
        WorkflowStep(
            name="Push to Registry",
            type=StepType.ACTION,
            order=1,
            config={"action": "push_image"},
            on_failure="continue",
        ),
        WorkflowStep(
            name="Update Kubernetes",
            type=StepType.ACTION,
            order=2,
            config={"action": "kubectl_apply",
                    "manifest": "k8s/deployment.yaml"},
        ),
        WorkflowStep(
            name="Wait for Rollout",
            type=StepType.WAIT,
            order=3,
            config={"duration_seconds": 60},
        ),
        WorkflowStep(
            name="Verify Health",
            type=StepType.ACTION,
            order=4,
            config={"action": "kubectl_rollout_status"},
        ),
    ],
    tags=["kubernetes", "deployment"],
)

TEMPLATE_BLUE_GREEN = WorkflowDefinition(
    name="Blue-Green Deployment",
    description="Zero-downtime deployment using blue-green strategy",
    steps=[
        WorkflowStep(
            name="Deploy Green Version",
            type=StepType.ACTION,
            order=0,
            config={"action": "kubectl_apply", "manifest": "k8s/green.yaml"},
        ),
        WorkflowStep(
            name="Wait for Green Ready",
            type=StepType.WAIT,
            order=1,
            config={"duration_seconds": 30},
        ),
        WorkflowStep(
            name="Approval Required",
            type=StepType.APPROVAL,
            order=2,
            description="Approve traffic switch to green version",
        ),
        WorkflowStep(
            name="Switch Traffic",
            type=StepType.ACTION,
            order=3,
            config={"action": "kubectl_service_switch", "service": "myapp"},
        ),
        WorkflowStep(
            name="Verify Traffic",
            type=StepType.ACTION,
            order=4,
            config={"action": "verify_traffic"},
        ),
    ],
    tags=["kubernetes", "blue-green", "zero-downtime"],
)

TEMPLATE_DATABASE_MIGRATION = WorkflowDefinition(
    name="Database Migration with Rollback",
    description="Run database migration with automatic rollback on failure",
    steps=[
        WorkflowStep(
            name="Backup Database",
            type=StepType.ACTION,
            order=0,
            config={"action": "pg_dump"},
        ),
        WorkflowStep(
            name="Dry Run Migration",
            type=StepType.ACTION,
            order=1,
            config={"action": "alembic_upgrade", "dry_run": True},
        ),
        WorkflowStep(
            name="Approval Required",
            type=StepType.APPROVAL,
            order=2,
            description="Approve production database migration",
        ),
        WorkflowStep(
            name="Run Migration",
            type=StepType.ACTION,
            order=3,
            config={"action": "alembic_upgrade"},
            on_failure="rollback",
        ),
        WorkflowStep(
            name="Verify Schema",
            type=StepType.ACTION,
            order=4,
            config={"action": "verify_schema"},
        ),
    ],
    tags=["database", "migration", "postgresql"],
)


# Register default templates
for template in [
    TEMPLATE_KUBERNETES_DEPLOYMENT,
    TEMPLATE_BLUE_GREEN,
    TEMPLATE_DATABASE_MIGRATION,
]:
    workflow_definitions[template.id] = template


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=settings.service_port)
