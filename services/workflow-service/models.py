"""
Workflow Service Database Models
"""

import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Text,
    DateTime,
    JSON,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from database import Base


class WorkflowDefinition(Base):
    """Workflow template definition in database."""

    __tablename__ = "workflow_definitions"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text, default="")
    version = Column(Integer, default=1)

    # Workflow steps
    steps = Column(JSON, default=[])

    # Entry point (first step ID or name)
    entry_point = Column(String, default="")

    # Metadata
    created_by = Column(String, default="")
    tags = Column(JSON, default=[])
    is_template = Column(Boolean, default=False)

    # Parameters
    parameters = Column(JSON, default={})
    parameter_schema = Column(JSON, default={})

    # Timestamps
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )

    # Relationships
    executions = relationship("WorkflowExecution", back_populates="workflow")


class WorkflowExecution(Base):
    """Workflow execution instance in database."""

    __tablename__ = "workflow_executions"

    id = Column(String, primary_key=True, index=True)
    workflow_id = Column(String, ForeignKey("workflow_definitions.id"))
    workflow_version = Column(Integer)

    # Execution state
    status = Column(String, default="running")
    current_step_id = Column(String, nullable=True)

    # Execution context
    parameters = Column(JSON, default={})
    context = Column(JSON, default={})

    # Results
    results = Column(JSON, default={})
    errors = Column(JSON, default=[])

    # Timestamps
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Audit
    created_by = Column(String, default="")
    approved_by = Column(String, nullable=True)

    # Relationships
    workflow = relationship("WorkflowDefinition", back_populates="executions")
    step_executions = relationship("StepExecution", back_populates="execution")


class StepExecution(Base):
    """Execution details for individual workflow steps."""

    __tablename__ = "step_executions"

    id = Column(String, primary_key=True, index=True)
    execution_id = Column(String, ForeignKey("workflow_executions.id"))
    step_id = Column(String, index=True)

    name = Column(String)
    step_type = Column(String)
    order = Column(Integer)

    # Step configuration
    config = Column(JSON, default={})

    # Execution state
    status = Column(String, default="pending")
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)

    # Error handling
    retry_count = Column(Integer, default=0)

    # Relationships
    execution = relationship("WorkflowExecution", back_populates="step_executions")
