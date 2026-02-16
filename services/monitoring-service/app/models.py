"""
SQLAlchemy Models for Monitoring Service.

Database models for metrics, health, and baseline data.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, Text, JSON, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Metric(Base):
    """Time-series metric storage."""

    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    value = Column(Float, nullable=False)
    # gauge, counter, histogram
    metric_type = Column(String(50), nullable=False)
    labels = Column(JSON, default={})
    source_service = Column(String(100), nullable=True)
    cluster_id = Column(String(100), nullable=True, index=True)
    namespace = Column(String(100), nullable=True)
    resource_name = Column(String(255), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow,
                       nullable=False, index=True)

    __table_args__ = (
        Index("idx_metric_name_timestamp", "name", "timestamp"),
        Index("idx_metric_cluster_time", "cluster_id", "timestamp"),
    )


class BaselineMetric(Base):
    """Learned baseline for anomaly detection."""

    __tablename__ = "baseline_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    metric_name = Column(String(255), nullable=False, index=True)
    mean_value = Column(Float, nullable=False)
    std_dev = Column(Float, nullable=False)
    min_value = Column(Float, nullable=True)
    max_value = Column(Float, nullable=True)
    sample_count = Column(Integer, nullable=False)
    hour_of_day = Column(Integer, nullable=True)  # For seasonal patterns
    day_of_week = Column(Integer, nullable=True)
    labels_hash = Column(String(64), nullable=True)
    cluster_id = Column(String(100), nullable=True, index=True)
    computed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_baseline_metric_labels", "metric_name", "labels_hash"),
    )


class CustomMetric(Base):
    """Custom user-defined metrics."""

    __tablename__ = "custom_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    metric_type = Column(String(50), nullable=False)
    unit = Column(String(50), nullable=True)
    labels_schema = Column(JSON, default={})
    aggregation_func = Column(String(50), default="avg")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)


class ServiceHealth(Base):
    """Health status of monitored services."""

    __tablename__ = "service_health"

    id = Column(Integer, primary_key=True, autoincrement=True)
    service_name = Column(String(100), nullable=False, unique=True)
    status = Column(String(20), nullable=False)  # healthy, degraded, down
    response_time_ms = Column(Float, nullable=True)
    last_check = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_success = Column(DateTime, nullable=True)
    consecutive_failures = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    metadata = Column(JSON, default={})

    __table_args__ = (
        Index("idx_service_status", "status"),
    )


class ClusterHealth(Base):
    """Health status of Kubernetes clusters."""

    __tablename__ = "cluster_health"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cluster_id = Column(String(100), nullable=False, unique=True)
    cluster_name = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False)  # healthy, warning, critical
    overall_score = Column(Float, default=100.0)  # 0-100
    node_count = Column(Integer, default=0)
    node_ready_count = Column(Integer, default=0)
    pod_count = Column(Integer, default=0)
    pod_running_count = Column(Integer, default=0)
    pod_failed_count = Column(Integer, default=0)
    cpu_usage_percent = Column(Float, default=0.0)
    memory_usage_percent = Column(Float, default=0.0)
    disk_usage_percent = Column(Float, default=0.0)
    issues = Column(JSON, default=[])  # List of detected issues
    last_check = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_cluster_status", "status"),
    )
