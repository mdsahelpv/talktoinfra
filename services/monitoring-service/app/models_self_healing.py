"""
SQLAlchemy Models for Self-Healing and Automated Response.

Database models for auto-restart, auto-scale, auto-retry, and runbook automation.
"""

from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, Text, JSON, Index, ForeignKey
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class SelfHealingRule(Base):
    """Rules for automated self-healing actions."""

    __tablename__ = "self_healing_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Rule type: auto_restart_pod, auto_scale_hpa, auto_retry_job, runbook
    rule_type = Column(String(50), nullable=False, index=True)

    # Enable/disable
    enabled = Column(Boolean, default=True, nullable=False)

    # Conditions
    # label, status, metric
    condition_type = Column(String(50), nullable=False)
    condition_value = Column(JSON, nullable=False)  # The condition to match

    # Action configuration
    # restart, scale, retry, webhook
    action_type = Column(String(50), nullable=False)
    action_config = Column(JSON, default={})  # Parameters for the action

    # Thresholds and limits
    max_retries = Column(Integer, default=3)
    retry_interval_seconds = Column(Integer, default=60)
    cooldown_seconds = Column(Integer, default=300)

    # Targeting
    cluster_id = Column(String(100), nullable=True, index=True)
    namespace = Column(String(100), nullable=True)
    label_selector = Column(JSON, default={})  # Kubernetes label selector

    # Notifications
    notify_on_action = Column(Boolean, default=True)
    notify_channels = Column(JSON, default=[])

    # Timing
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)
    last_triggered = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_rule_type_enabled", "rule_type", "enabled"),
        Index("idx_rule_cluster_ns", "cluster_id", "namespace"),
    )


class SelfHealingAction(Base):
    """Log of self-healing actions executed."""

    __tablename__ = "self_healing_actions"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Reference to rule
    rule_id = Column(Integer, ForeignKey(
        "self_healing_rules.id"), nullable=False)

    # Action details
    action_type = Column(String(50), nullable=False)
    # pod name, hpa name, job name
    target_resource = Column(String(255), nullable=False)
    # Pod, Deployment, Job, etc.
    target_kind = Column(String(50), nullable=False)
    cluster_id = Column(String(100), nullable=True)
    namespace = Column(String(100), nullable=True)

    # Trigger
    # What triggered this action
    trigger_condition = Column(JSON, nullable=False)

    # Execution status
    # pending, running, success, failed, skipped
    status = Column(String(20), nullable=False)
    result = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    # Retry tracking
    attempt_number = Column(Integer, default=1)
    max_attempts = Column(Integer, default=3)

    # Timing
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Metadata
    metadata = Column(JSON, default={})

    __table_args__ = (
        Index("idx_action_rule_status", "rule_id", "status"),
        Index("idx_action_cluster_time", "cluster_id", "created_at"),
    )


class Runbook(Base):
    """Automated remediation runbooks."""

    __tablename__ = "runbooks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)

    # Trigger conditions
    trigger_type = Column(String(50), nullable=False)  # alert, metric, manual
    trigger_condition = Column(JSON, nullable=False)

    # Steps - ordered list of actions
    steps = Column(JSON, nullable=False)  # List of step definitions

    # Configuration
    enabled = Column(Boolean, default=True, nullable=False)
    require_approval = Column(Boolean, default=False)
    timeout_seconds = Column(Integer, default=600)

    # Rollback configuration
    rollback_on_failure = Column(Boolean, default=True)
    rollback_steps = Column(JSON, default=[])

    # Usage tracking
    times_executed = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    last_executed = Column(DateTime, nullable=True)

    # Timing
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_runbook_trigger", "trigger_type", "enabled"),
    )


class RunbookExecution(Base):
    """Execution log for runbooks."""

    __tablename__ = "runbook_executions"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Reference to runbook
    runbook_id = Column(Integer, ForeignKey("runbooks.id"), nullable=False)

    # Execution context
    trigger_data = Column(JSON, default={})  # What triggered the runbook
    context = Column(JSON, default={})  # Execution context

    # Status
    # pending, running, success, failed, rolled_back
    status = Column(String(20), nullable=False)
    current_step = Column(Integer, default=0)

    # Results
    step_results = Column(JSON, default=[])  # Results of each step
    final_result = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    # Timing
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Execution metadata
    executed_by = Column(String(100), nullable=True)  # User or system
    execution_type = Column(
        String(50), default="automatic")  # automatic, manual

    __table_args__ = (
        Index("idx_execution_runbook_status", "runbook_id", "status"),
        Index("idx_execution_time", "created_at"),
    )


class ProactiveInsight(Base):
    """AI-generated proactive insights and predictions."""

    __tablename__ = "proactive_insights"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Insight type
    # trend, prediction, recommendation
    insight_type = Column(String(50), nullable=False, index=True)

    # Content
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    recommendation = Column(Text, nullable=True)

    # Target
    cluster_id = Column(String(100), nullable=True, index=True)
    namespace = Column(String(100), nullable=True)
    resource_kind = Column(String(50), nullable=True)
    resource_name = Column(String(255), nullable=True)

    # Analysis data
    analysis_data = Column(JSON, default={})  # Supporting data
    confidence_score = Column(Float, default=0.0)  # 0-1 confidence

    # Priority
    severity = Column(String(20), default="info")  # info, warning, critical
    priority_score = Column(Float, default=0.0)  # 0-100

    # Status
    # active, acknowledged, resolved, dismissed
    status = Column(String(20), default="active")

    # Actions taken
    actions_taken = Column(JSON, default=[])
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(100), nullable=True)

    # Timing
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_insight_cluster_status", "cluster_id", "status"),
        Index("idx_insight_severity", "severity", "status"),
    )


class ClusterHealthScore(Base):
    """Historical health scoring for clusters."""

    __tablename__ = "cluster_health_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)

    cluster_id = Column(String(100), nullable=False, index=True)
    cluster_name = Column(String(255), nullable=True)

    # Health scores (0-100)
    overall_score = Column(Float, nullable=False)
    availability_score = Column(Float, default=100.0)
    performance_score = Column(Float, default=100.0)
    capacity_score = Column(Float, default=100.0)
    reliability_score = Column(Float, default=100.0)

    # Contributing factors
    issues_count = Column(Integer, default=0)
    warning_count = Column(Integer, default=0)
    critical_count = Column(Integer, default=0)

    # Resource metrics at time of scoring
    # increasing, stable, decreasing
    cpu_trend = Column(String(20), nullable=True)
    memory_trend = Column(String(20), nullable=True)
    pod_trend = Column(String(20), nullable=True)

    # Predictions
    predicted_issues = Column(JSON, default=[])

    timestamp = Column(DateTime, default=datetime.utcnow,
                       nullable=False, index=True)

    __table_args__ = (
        Index("idx_health_score_cluster_time", "cluster_id", "timestamp"),
    )
