"""SQLAlchemy models for Onboarding Service."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database_base import Base


class Cluster(Base):
    """Kubernetes cluster model."""

    __tablename__ = "clusters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False, index=True)
    provider = Column(String(50), nullable=False, default="kubernetes")

    # Connection details
    api_endpoint = Column(String(500), nullable=True)
    certificate_authority = Column(Text, nullable=True)
    skip_tls_verify = Column(Boolean, default=False)

    # Status
    status = Column(String(50), nullable=False, default="pending")
    connection_status = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)

    # Namespace configuration
    # List of namespace patterns
    include_namespaces = Column(JSON, nullable=True)
    # List of namespace patterns
    exclude_namespaces = Column(JSON, nullable=True)

    # Labels/tags
    labels = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)
    last_sync_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    credentials = relationship(
        "Credential", back_populates="cluster", lazy="dynamic")
    sync_jobs = relationship(
        "SyncJob", back_populates="cluster", lazy="dynamic")


class CloudAccount(Base):
    """Cloud provider account model."""

    __tablename__ = "cloud_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False, index=True)
    provider = Column(String(50), nullable=False)  # aws, azure, gcp

    # Provider-specific identifiers
    aws_account_id = Column(String(50), nullable=True)
    azure_subscription_id = Column(String(100), nullable=True)
    azure_tenant_id = Column(String(100), nullable=True)
    gcp_project_id = Column(String(100), nullable=True)

    # Configuration
    regions = Column(JSON, nullable=True)  # List of regions
    resource_types = Column(JSON, nullable=True)  # List of resource types
    resource_groups = Column(JSON, nullable=True)  # For Azure

    # Status
    status = Column(String(50), nullable=False, default="pending")
    error_message = Column(Text, nullable=True)

    # Labels/tags
    labels = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)
    last_sync_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    credentials = relationship(
        "Credential", back_populates="cloud_account", lazy="dynamic")


class Credential(Base):
    """Credential storage model (encrypted)."""

    __tablename__ = "credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # References
    cluster_id = Column(UUID(as_uuid=True), ForeignKey(
        "clusters.id"), nullable=True, index=True)
    cloud_account_id = Column(UUID(as_uuid=True), ForeignKey(
        "cloud_accounts.id"), nullable=True, index=True)

    # Credential metadata
    name = Column(String(255), nullable=False)
    # kubeconfig, service_account, token, api_key
    credential_type = Column(String(100), nullable=False)

    # Encrypted credential data (AES-256 encrypted JSON)
    encrypted_data = Column(Text, nullable=False)
    encryption_key_id = Column(String(255), nullable=True)

    # Credential lifecycle
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)

    # Rotation tracking
    rotation_required = Column(Boolean, default=False)
    rotation_period_days = Column(Integer, nullable=True)
    last_rotated_at = Column(DateTime, nullable=True)
    rotated_from = Column(UUID(as_uuid=True), nullable=True)

    # Soft delete
    deleted_at = Column(DateTime, nullable=True)
    deprecated = Column(Boolean, default=False)
    deprecated_at = Column(DateTime, nullable=True)
    replaced_by = Column(UUID(as_uuid=True), nullable=True)

    # Relationships
    cluster = relationship("Cluster", back_populates="credentials")
    cloud_account = relationship("CloudAccount", back_populates="credentials")


class SyncJob(Base):
    """Cluster sync job tracking."""

    __tablename__ = "sync_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    cluster_id = Column(UUID(as_uuid=True), ForeignKey(
        "clusters.id"), nullable=False, index=True)

    # Job details
    # full, incremental, namespace
    job_type = Column(String(50), nullable=False)
    # pending, running, completed, failed
    status = Column(String(50), nullable=False)

    # Progress tracking
    resources_found = Column(Integer, default=0)
    resources_synced = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)
    error_details = Column(JSON, nullable=True)

    # Timestamps
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    cluster = relationship("Cluster", back_populates="sync_jobs")


class CredentialAuditLog(Base):
    """Audit log for credential access."""

    __tablename__ = "credential_audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    credential_id = Column(UUID(as_uuid=True), ForeignKey(
        "credentials.id"), nullable=False, index=True)

    # Access details
    # created, used, rotated, deleted
    action = Column(String(50), nullable=False)
    accessed_by = Column(String(255), nullable=True)  # service or user
    access_reason = Column(Text, nullable=True)

    # Result
    success = Column(Boolean, nullable=False)
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Request metadata
    request_ip = Column(String(50), nullable=True)
    request_user_agent = Column(String(500), nullable=True)
