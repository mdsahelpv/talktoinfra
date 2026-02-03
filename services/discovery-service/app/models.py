"""
Database models for Discovery Service.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    Text,
    JSON,
    ARRAY,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, CIDR, INET
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class ScanJob(Base):
    """Scan job tracking and persistence."""

    __tablename__ = "scan_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(
        String(20), nullable=False, default="pending", server_default="pending"
    )
    scan_type = Column(String(20), nullable=False, default="python")
    progress = Column(Integer, default=0)

    # Scan parameters
    ip_range = Column(CIDR, nullable=False)
    ports = Column(ARRAY(Integer), nullable=False)

    # Statistics
    total_hosts = Column(Integer)
    scanned_hosts = Column(Integer, default=0)
    found_hosts = Column(Integer, default=0)

    # Metadata
    created_by = Column(String(100), nullable=False)
    started_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)

    # Configuration
    config = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    discovered_hosts = relationship(
        "DiscoveredHost", back_populates="job", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed', 'cancelled')",
            name="valid_scan_status",
        ),
        CheckConstraint(
            "scan_type IN ('fast', 'detailed', 'hybrid', 'python')",
            name="valid_scan_type",
        ),
        CheckConstraint("progress >= 0 AND progress <= 100", name="valid_progress"),
    )


class DiscoveredHost(Base):
    """Hosts discovered during network scans."""

    __tablename__ = "discovered_hosts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scan_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )

    ip_address = Column(INET, nullable=False)
    hostname = Column(String(255))
    status = Column(String(20), nullable=False)
    response_time_ms = Column(Integer)
    discovered_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    job = relationship("ScanJob", back_populates="discovered_hosts")
    ports = relationship(
        "DiscoveredPort", back_populates="host", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('alive', 'unreachable', 'filtered')", name="valid_host_status"
        ),
        UniqueConstraint("job_id", "ip_address", name="unique_host_per_job"),
    )


class DiscoveredPort(Base):
    """Ports discovered on hosts during scans."""

    __tablename__ = "discovered_ports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    host_id = Column(
        UUID(as_uuid=True),
        ForeignKey("discovered_hosts.id", ondelete="CASCADE"),
        nullable=False,
    )

    port = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False)
    service = Column(String(100))
    service_version = Column(String(255))
    banner = Column(Text)
    protocol = Column(String(10), default="tcp")
    discovered_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    host = relationship("DiscoveredHost", back_populates="ports")

    __table_args__ = (
        CheckConstraint("port > 0 AND port <= 65535", name="valid_port_range"),
        CheckConstraint(
            "status IN ('open', 'closed', 'filtered')", name="valid_port_status"
        ),
        CheckConstraint("protocol IN ('tcp', 'udp')", name="valid_protocol"),
        UniqueConstraint("host_id", "port", "protocol", name="unique_port_per_host"),
    )


class ManagedHost(Base):
    """Persistent managed hosts (added from discovered hosts)."""

    __tablename__ = "managed_hosts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name = Column(String(255), nullable=False)
    ip_address = Column(INET, nullable=False, unique=True)

    # Discovered services
    ports = Column(ARRAY(Integer), default=list)
    services = Column(ARRAY(String), default=list)

    # Status tracking
    status = Column(String(20), default="unknown")
    last_checked_at = Column(DateTime(timezone=True))

    # Discovery metadata
    first_discovered_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    discovered_by_job_id = Column(UUID(as_uuid=True), ForeignKey("scan_jobs.id"))

    # Management metadata
    added_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    added_by = Column(String(100), nullable=False)
    notes = Column(Text)
    host_metadata = Column(JSON, default=dict)

    # Relationships
    health_checks = relationship(
        "HostHealthCheck", back_populates="host", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('online', 'offline', 'unknown', 'degraded')",
            name="valid_managed_status",
        ),
    )


class HostHealthCheck(Base):
    """Health check history for managed hosts."""

    __tablename__ = "host_health_checks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    host_id = Column(
        UUID(as_uuid=True),
        ForeignKey("managed_hosts.id", ondelete="CASCADE"),
        nullable=False,
    )

    status = Column(String(20), nullable=False)
    response_time_ms = Column(Integer)
    error_message = Column(Text)
    checked_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    host = relationship("ManagedHost", back_populates="health_checks")

    __table_args__ = (
        CheckConstraint(
            "status IN ('online', 'offline', 'unknown', 'degraded')",
            name="valid_health_status",
        ),
    )


class ScanExclusion(Base):
    """Networks excluded from scanning for security."""

    __tablename__ = "scan_exclusions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    network = Column(CIDR, nullable=False, unique=True)
    reason = Column(String(255), nullable=False)
    created_by = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    is_active = Column(Integer, default=1)  # 1 = true, 0 = false
