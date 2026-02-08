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
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import get_settings

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
    ACTION = "action"           # Execute an action (K8s deployment, etc.)
    CONDITION = "condition"     # Conditional branching
    WAIT = "wait"              # Wait for duration or event
    APPROVAL = "approval"       # Require approval to proceed
    PARALLEL = "parallel"       # Execute multiple steps in parallel
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
    created_at: str = Field(default_factory=lambda: time.strftime(
        "%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    # Audit
    created_by: str = ""
    approved_by: Optional[str] = None


# Forward reference for circular dependency
WorkflowStep.model_rebuild()


# ============ In-Memory Storage (replace with database) ============

workflow_definitions: Dict[str, WorkflowDefinition] = {}
workflow_executions: Dict[str, WorkflowExecution] = {}


# ============ FastAPI App ============

settings = get_settings()

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
    yield
    logger.info("workflow_service_stopping")


app.router.lifespan_context = lifespan


# ============ Health Check ============

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.service_name,
        "version": "1.0.0",
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
        "items": [w.model_dump(exclude={"steps"}) for w in workflows[skip:skip + limit]],
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
async def update_workflow(workflow_id: str, workflow: WorkflowDefinition) -> Dict[str, Any]:
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
    parameters: Dict[str, Any] = None,
    approved_by: str = None,
) -> Dict[str, Any]:
    """Start a workflow execution."""
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
        "items": [e.model_dump() for e in executions[skip:skip + limit]],
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
            detail=f"Cannot cancel execution in {execution.status.value} status"
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
    """Rollback a completed or failed workflow execution."""
    if execution_id not in workflow_executions:
        raise HTTPException(status_code=404, detail="Execution not found")

    execution = workflow_executions[execution_id]

    if execution.status not in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED]:
        raise HTTPException(
            status_code=400,
            detail=f"Can only rollback completed or failed executions"
        )

    execution.status = WorkflowStatus.ROLLING_BACK

    logger.info("workflow_execution_rollback_started",
                execution_id=execution_id)
    return {
        "execution_id": execution_id,
        "status": WorkflowStatus.ROLLING_BACK.value,
        "message": "Rollback initiated",
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
for template in [TEMPLATE_KUBERNETES_DEPLOYMENT, TEMPLATE_BLUE_GREEN, TEMPLATE_DATABASE_MIGRATION]:
    workflow_definitions[template.id] = template


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.service_port)
