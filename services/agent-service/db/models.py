"""
SQLAlchemy database models for Agent Service.
Persistent storage for tasks, approvals, and audit events.
"""

from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    DateTime,
    JSON,
    Integer,
    Boolean,
    ForeignKey,
    Text,
    ARRAY,
    Enum as SQLEnum,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()


class TaskStatusEnum(str, enum.Enum):
    PENDING = "pending"
    PLANNING = "planning"
    VALIDATING = "validating"
    AWAITING_APPROVAL = "awaiting_approval"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ApprovalStatusEnum(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class AgentTypeEnum(str, enum.Enum):
    QUERY = "query"
    ANALYSIS = "analysis"
    PLANNING = "planning"
    ACTION = "action"
    COORDINATOR = "coordinator"


class TaskModel(Base):
    """Task database model."""

    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(255), nullable=False, index=True)
    agent_type = Column(SQLEnum(AgentTypeEnum), nullable=False)
    query = Column(Text, nullable=False)
    environment = Column(String(50), nullable=False, default="development")
    context = Column(JSON, nullable=True)
    conversation_id = Column(String(36), nullable=True)

    status = Column(
        SQLEnum(TaskStatusEnum),
        nullable=False,
        default=TaskStatusEnum.PENDING,
        index=True,
    )
    plan = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    approvals = relationship(
        "ApprovalModel", back_populates="task", cascade="all, delete-orphan"
    )
    steps = relationship(
        "TaskStepModel", back_populates="task", cascade="all, delete-orphan"
    )
    audit_events = relationship("AuditEventModel", back_populates="task")


class TaskStepModel(Base):
    """Task step database model."""

    __tablename__ = "task_steps"

    id = Column(String(36), primary_key=True)
    task_id = Column(
        String(36),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_number = Column(Integer, nullable=False)
    tool_name = Column(String(255), nullable=False)
    operation = Column(String(255), nullable=False)
    parameters = Column(JSON, nullable=False)
    result = Column(JSON, nullable=True)
    status = Column(String(50), nullable=False, default="pending")
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    # Relationship
    task = relationship("TaskModel", back_populates="steps")


class ApprovalModel(Base):
    """Approval request database model."""

    __tablename__ = "approvals"

    id = Column(String(36), primary_key=True)
    task_id = Column(
        String(36),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action_type = Column(String(100), nullable=False)
    dry_run_result = Column(JSON, nullable=False)

    requester_id = Column(String(255), nullable=False, index=True)
    approvers = Column(ARRAY(String), nullable=False)

    status = Column(
        SQLEnum(ApprovalStatusEnum),
        nullable=False,
        default=ApprovalStatusEnum.PENDING,
        index=True,
    )
    approved_by = Column(String(255), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejected_by = Column(String(255), nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    task = relationship("TaskModel", back_populates="approvals")


class AuditEventModel(Base):
    """Audit event database model - immutable log."""

    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)

    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    agent_type = Column(String(50), nullable=True)
    action = Column(Text, nullable=True)
    details = Column(JSON, nullable=False, default={})

    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    success = Column(Boolean, nullable=False, default=True)

    # Hash chain for tamper detection
    previous_hash = Column(String(64), nullable=True)
    data_hash = Column(String(64), nullable=False)

    # Relationship
    task = relationship("TaskModel", back_populates="audit_events")


class SkillModel(Base):
    """Skill registry database model."""

    __tablename__ = "skills"

    id = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=False)
    version = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    author = Column(String(255), nullable=True)
    risk_level = Column(String(50), nullable=False)
    requires_approval = Column(Boolean, nullable=False, default=True)
    manifest = Column(JSON, nullable=False)
    is_builtin = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class WorkflowModel(Base):
    """Workflow database model."""

    __tablename__ = "workflows"

    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    definition = Column(JSON, nullable=False)  # Full workflow definition
    status = Column(String(50), nullable=False, default="pending")
    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    completed_at = Column(DateTime, nullable=True)
