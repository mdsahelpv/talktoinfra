"""
Pydantic models for Agent Service.
Type-safe data validation for agents, tasks, tools, and safety.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator
from uuid import UUID, uuid4


# Enums


class AgentType(str, Enum):
    """Types of agents."""

    QUERY = "query"  # Read-only information retrieval
    ANALYSIS = "analysis"  # Insights and recommendations
    PLANNING = "planning"  # Plan generation
    ACTION = "action"  # Infrastructure modifications
    COORDINATOR = "coordinator"  # Multi-agent workflows


class RiskLevel(str, Enum):
    """Risk levels for operations."""

    READ_ONLY = "read_only"  # Safe for auto-execution
    LOW = "low"  # Low risk
    MEDIUM = "medium"  # Medium risk
    HIGH = "high"  # High risk
    CRITICAL = "critical"  # Critical - multi-level approval


class TaskStatus(str, Enum):
    """Task lifecycle statuses."""

    PENDING = "pending"  # Queued
    PLANNING = "planning"  # Creating execution plan
    VALIDATING = "validating"  # Safety checks
    AWAITING_APPROVAL = "awaiting_approval"  # Waiting for human approval
    EXECUTING = "executing"  # Running tools
    VERIFYING = "verifying"  # Post-execution verification
    COMPLETED = "completed"  # Success
    FAILED = "failed"  # Error
    ROLLED_BACK = "rolled_back"  # Compensated


class ApprovalStatus(str, Enum):
    """Approval workflow statuses."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


# Agent Models


class AgentConfig(BaseModel):
    """Configuration for an agent."""

    agent_type: AgentType
    model: str = "llama3.3:70b"
    temperature: float = 0.1
    max_iterations: int = 10
    timeout_seconds: int = 300
    allowed_tools: List[str] = []
    blocked_tools: List[str] = []


class AgentInfo(BaseModel):
    """Information about an agent."""

    id: str
    agent_type: AgentType
    name: str
    description: str
    risk_level: RiskLevel
    requires_approval: bool
    allowed_tools: List[str]


# Task Models


class TaskRequest(BaseModel):
    """Request to execute a task."""

    query: str = Field(..., min_length=1, max_length=10000, description="User query")
    environment: str = Field(default="development", description="Target environment")
    context: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional context"
    )
    conversation_id: Optional[str] = Field(
        default=None, description="Conversation ID for context"
    )

    @validator("environment")
    def validate_environment(cls, v):
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of: {allowed}")
        return v


class Task(BaseModel):
    """Task definition."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    agent_type: AgentType
    query: str
    environment: str
    context: Optional[Dict[str, Any]] = None
    conversation_id: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    plan: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


class ExecutionStep(BaseModel):
    """Single step in execution plan."""

    step_number: int
    tool_name: str
    operation: str
    parameters: Dict[str, Any]
    description: str
    risk_level: RiskLevel
    requires_approval: bool
    dry_run_first: bool = True
    can_rollback: bool = False


class ExecutionPlan(BaseModel):
    """Execution plan for a task."""

    steps: List[ExecutionStep]
    estimated_duration_seconds: int = 0
    rollback_plan: Optional[List[Dict[str, Any]]] = None
    warnings: List[str] = []


class TaskResult(BaseModel):
    """Result of task execution."""

    success: bool
    response: Optional[str] = None
    plan: Optional[ExecutionPlan] = None
    step_results: List[Dict[str, Any]] = []
    requires_approval: bool = False
    approval_id: Optional[str] = None
    error_message: Optional[str] = None
    safety_result: Optional[Dict[str, Any]] = None
    execution_time_ms: Optional[int] = None

    @classmethod
    def success(cls, response: str, **kwargs):
        return cls(success=True, response=response, **kwargs)

    @classmethod
    def failed(cls, reason: str, **kwargs):
        return cls(success=False, error_message=reason, **kwargs)


class TaskResponse(BaseModel):
    """API response for task execution."""

    task_id: str
    status: TaskStatus
    agent_type: AgentType
    response: Optional[str] = None
    requires_approval: bool = False
    approval_id: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# Safety Models


class SafetyCheck(BaseModel):
    """Individual safety check result."""

    check_name: str
    passed: bool
    message: Optional[str] = None


class SafetyResult(BaseModel):
    """Result of safety validation."""

    allowed: bool
    risk_level: RiskLevel
    requires_approval: bool
    reason: Optional[str] = None
    approvers: Optional[List[str]] = None
    requires_justification: bool = False
    dry_run_required: bool = True
    checks_performed: List[str] = []
    warnings: List[str] = []
    safety_checks: List[SafetyCheck] = []


class ApprovalRequest(BaseModel):
    """Request for human approval."""

    task_id: str
    step_number: int
    action_type: str
    target: str
    dry_run_result: Dict[str, Any]
    risk_level: RiskLevel
    requester_id: str
    approvers: List[str]
    warnings: List[str] = []
    justification_required: bool = False
    expires_at: datetime


class ApprovalDecision(BaseModel):
    """Decision on approval request."""

    approval_id: str
    decision: str  # approve or reject
    notes: Optional[str] = None


class Approval(BaseModel):
    """Approval record."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    task_id: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    requester_id: str
    approvers: List[str]
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejected_by: Optional[str] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Tool Models


class ToolParameter(BaseModel):
    """Tool parameter definition."""

    name: str
    type: str
    description: str
    required: bool = True
    default: Optional[Any] = None
    validation: Optional[str] = None


class ToolDefinition(BaseModel):
    """Definition of a tool."""

    name: str
    description: str
    parameters: List[ToolParameter]
    return_type: str
    risk_level: RiskLevel
    requires_approval: bool
    can_dry_run: bool
    can_rollback: bool
    is_read_only: bool = False
    allowed_environments: List[str] = ["*"]
    blocked_namespaces: List[str] = []


class ToolCall(BaseModel):
    """A tool call in execution."""

    tool_name: str
    parameters: Dict[str, Any]
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None


# Workflow Models


class WorkflowStep(BaseModel):
    """Step in a workflow."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    agent_type: AgentType
    task_description: str
    depends_on: List[str] = []
    pre_approved: bool = False


class Workflow(BaseModel):
    """Multi-step workflow."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str
    steps: List[WorkflowStep]
    status: TaskStatus = TaskStatus.PENDING
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Skill Models


class SkillManifest(BaseModel):
    """Skill manifest definition."""

    id: str
    name: str
    version: str
    description: str
    author: str
    risk_level: RiskLevel
    requires_approval: bool
    tools: List[str]
    prompts: Dict[str, str]


class SkillInfo(BaseModel):
    """Skill information for API."""

    id: str
    name: str
    version: str
    description: str
    risk_level: RiskLevel
    is_builtin: bool
