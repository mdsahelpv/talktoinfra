"""
Extended database models for Discovered Infrastructure Management.

This module adds models for unified discovered infrastructure tracking with
state machine support for onboarding workflows.
"""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    Text,
    JSON,
    ForeignKey,
    CheckConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, INET, MACADDR
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class InfrastructureType(str, Enum):
    """Types of discovered infrastructure."""

    KUBERNETES_CLUSTER = "kubernetes_cluster"
    CLOUD_RESOURCE = "cloud_resource"
    DATABASE = "database"
    LOAD_BALANCER = "service"
    NETWORK_DEVICE = "network_device"
    HOST = "host"
    UNKNOWN = "unknown"


class DiscoveredState(str, Enum):
    """State machine states for discovered infrastructure items."""

    DISCOVERED = "discovered"
    ANALYZED = "analyzed"
    SUGGESTED = "suggested"
    PENDING_ONBOARDING = "pending_onboarding"
    ONBOARDING = "onboarding"
    ONBOARDED = "onboarded"
    FAILED = "failed"
    IGNORED = "ignored"


# Valid state transitions
VALID_STATE_TRANSITIONS = {
    DiscoveredState.DISCOVERED: [
        DiscoveredState.ANALYZED,
        DiscoveredState.IGNORED,
    ],
    DiscoveredState.ANALYZED: [
        DiscoveredState.SUGGESTED,
        DiscoveredState.IGNORED,
    ],
    DiscoveredState.SUGGESTED: [
        DiscoveredState.PENDING_ONBOARDING,
        DiscoveredState.ONBOARDED,
        DiscoveredState.IGNORED,
    ],
    DiscoveredState.PENDING_ONBOARDING: [
        DiscoveredState.ONBOARDING,
        DiscoveredState.IGNORED,
    ],
    DiscoveredState.ONBOARDING: [
        DiscoveredState.ONBOARDED,
        DiscoveredState.FAILED,
        DiscoveredState.PENDING_ONBOARDING,
    ],
    DiscoveredState.ONBOARDED: [
        DiscoveredState.FAILED,
    ],
    DiscoveredState.FAILED: [
        DiscoveredState.PENDING_ONBOARDING,
        DiscoveredState.IGNORED,
    ],
    DiscoveredState.IGNORED: [],  # Terminal state
}


class DiscoveredInfrastructure(Base):
    """Unified model for all discovered infrastructure items.

    This consolidates hosts, services, and other discovered resources
    into a single searchable/filterable model with state tracking.
    """

    __tablename__ = "discovered_infrastructure"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Core identification
    ip_address = Column(INET, nullable=True, index=True)
    hostname = Column(String(255), index=True)
    fqdn = Column(String(255))
    mac_address = Column(MACADDR)

    # Infrastructure classification
    infra_type = Column(
        String(50),
        nullable=False,
        default=InfrastructureType.UNKNOWN.value,
        index=True,
    )
    # e.g., "postgresql", "nginx"
    service_type = Column(String(100), index=True)
    service_version = Column(String(255))
    # 0-100 confidence in detection
    confidence_score = Column(Integer, default=0)

    # State machine
    state = Column(
        String(30),
        nullable=False,
        default=DiscoveredState.DISCOVERED.value,
        index=True,
    )
    previous_state = Column(String(30))

    # Discovery metadata
    scan_job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scan_jobs.id", ondelete="SET NULL"),
        index=True,
    )
    discovered_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    last_seen_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Network details
    port = Column(Integer, index=True)  # Primary port for this entry
    protocol = Column(String(10), default="tcp")
    open_ports = Column(JSON, default=list)  # Array of port objects

    # Service information
    service_banner = Column(Text)
    ssl_info = Column(JSON)  # TLS certificate details
    headers = Column(JSON)  # HTTP headers if available

    # Cloud/Container metadata
    cloud_provider = Column(String(50))
    cloud_metadata = Column(JSON)  # AWS/Azure/GCP specific data
    k8s_info = Column(JSON)  # Kubernetes node/pod info
    container_info = Column(JSON)  # Docker/container details

    # Location information
    location = Column(String(255))  # Network location
    vpc_id = Column(String(255))
    subnet_id = Column(String(255))

    # Response metrics
    response_time_ms = Column(Integer)
    availability_score = Column(Integer, default=100)  # 0-100 percentage

    # Onboarding tracking
    # e.g., "connect_k8s", "add_monitoring"
    suggested_action = Column(String(100))
    onboarding_id = Column(UUID(as_uuid=True))  # Link to onboarding process
    managed_host_id = Column(
        UUID(as_uuid=True),
        ForeignKey("managed_hosts.id", ondelete="SET NULL"),
    )

    # User actions
    ignored_at = Column(DateTime(timezone=True))
    ignored_by = Column(String(100))
    ignore_reason = Column(Text)

    # Audit trail
    created_by = Column(String(100), nullable=False, default="system")
    notes = Column(Text)
    tags = Column(JSON, default=list)

    # Relationships
    scan_job = relationship("ScanJob")
    managed_host = relationship("ManagedHost")
    state_history = relationship(
        "DiscoveredStateHistory",
        back_populates="item",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "infra_type IN ('kubernetes_cluster', 'cloud_resource', 'database', "
            "'load_balancer', 'network_device', 'host', 'unknown')",
            name="valid_infra_type",
        ),
        CheckConstraint(
            "state IN ('discovered', 'analyzed', 'suggested', "
            "'pending_onboarding', 'onboarding', 'onboarded', 'failed', 'ignored')",
            name="valid_discovered_state",
        ),
        CheckConstraint("confidence_score >= 0 AND confidence_score <= 100"),
        CheckConstraint(
            "availability_score >= 0 AND availability_score <= 100"),
        Index("idx_discovered_infra_type_state", "infra_type", "state"),
        Index("idx_discovered_infra_scan_time",
              "scan_job_id", "discovered_at"),
    )


class DiscoveredStateHistory(Base):
    """Audit trail for state changes on discovered infrastructure."""

    __tablename__ = "discovered_state_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("discovered_infrastructure.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    from_state = Column(String(30))
    to_state = Column(String(30), nullable=False)

    triggered_by = Column(String(100))  # User or system
    trigger_reason = Column(Text)

    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    item = relationship("DiscoveredInfrastructure",
                        back_populates="state_history")

    __table_args__ = (
        CheckConstraint(
            "to_state IN ('discovered', 'analyzed', 'suggested', "
            "'pending_onboarding', 'onboarding', 'onboarded', 'failed', 'ignored')",
            name="valid_history_state",
        ),
    )


class ServiceCatalogEntry(Base):
    """Discovered services catalog for tracking API endpoints and services."""

    __tablename__ = "service_catalog"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Service identification
    host_id = Column(
        UUID(as_uuid=True),
        ForeignKey("discovered_infrastructure.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    endpoint = Column(String(500), nullable=False)  # Full URL/path
    path = Column(String(500))
    method = Column(String(10), default="GET")  # HTTP method

    # Service classification
    service_name = Column(String(100))
    # e.g., "rest_api", "graphql", "websocket"
    service_type = Column(String(50))
    api_version = Column(String(20))

    # Discovery info
    discovered_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    last_checked_at = Column(DateTime(timezone=True))
    response_time_ms = Column(Integer)

    # Service details
    documentation_url = Column(String(500))
    description = Column(Text)
    capabilities = Column(JSON, default=list)  # API capabilities
    auth_required = Column(Integer, default=0)
    auth_type = Column(String(50))  # e.g., "oauth2", "api_key", "basic"

    # Relationships
    host = relationship("DiscoveredInfrastructure")

    __table_args__ = (
        CheckConstraint(
            "method IN ('GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS')"),
        Index("idx_service_catalog_host", "host_id"),
        Index("idx_service_catalog_endpoint", "endpoint"),
    )


class DiscoveredBulkOperation(Base):
    """Track bulk operations on discovered infrastructure."""

    __tablename__ = "discovered_bulk_operations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # onboard, ignore, export
    operation_type = Column(String(50), nullable=False)
    target_count = Column(Integer, nullable=False)
    success_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)

    # pending, running, completed, failed
    status = Column(String(20), default="pending")
    error_message = Column(Text)

    created_by = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True))

    target_ids = Column(JSON, default=list)  # List of affected item IDs
    result_summary = Column(JSON, default=dict)

    __table_args__ = (
        CheckConstraint(
            "operation_type IN ('onboard', 'ignore', 'export', 'rescan')",
            name="valid_bulk_operation",
        ),
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="valid_bulk_status",
        ),
    )
