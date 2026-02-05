"""
Database models for RAG Service.

This module defines SQLAlchemy models for:
- Layer 1: Structured Storage (PostgreSQL)
  - Enhanced discovery tables with RAG metadata
  - K8s resource tables
- Index tracking for incremental updates
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    ARRAY,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class RAGDocument(Base):
    """Tracks indexed documents for RAG system.

    This table tracks all documents that have been indexed into
    the vector store, enabling incremental updates.
    """

    __tablename__ = "rag_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Document identification
    document_id = Column(String(255), nullable=False, unique=True)
    document_type = Column(
        String(50),
        nullable=False,
        default="infrastructure",
        comment="Type: infrastructure, log, doc, k8s_resource",
    )
    source_id = Column(String(255), nullable=True, comment="Source system ID")
    source_type = Column(String(50), nullable=True,
                         comment="Source: discovery, k8s, manual")

    # Document content
    title = Column(String(500), nullable=True)
    content_hash = Column(String(64), nullable=False,
                          comment="SHA-256 hash of content")

    # RAG metadata
    resource_type = Column(String(100), nullable=True)
    resource_name = Column(String(255), nullable=True)
    namespace = Column(String(255), nullable=True)
    cluster_id = Column(String(255), nullable=True)

    # Metadata from source
    metadata = Column(JSON, default=dict)

    # Indexing status
    is_indexed = Column(Boolean, default=False,
                        comment="Currently in vector store")
    indexing_error = Column(Text, nullable=True)

    # Timestamps
    content_updated_at = Column(DateTime(timezone=True), nullable=True)
    indexed_at = Column(DateTime(timezone=True), nullable=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True),
                        default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_rag_documents_source", "source_type", "source_id"),
        Index("idx_rag_documents_type", "document_type"),
        Index("idx_rag_documents_indexed", "is_indexed"),
    )


class K8sPod(Base):
    """Kubernetes Pod resource tracking."""

    __tablename__ = "k8s_pods"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cluster_id = Column(String(255), nullable=False,
                        comment="Cluster identifier")

    # Pod identification
    name = Column(String(253), nullable=False)
    namespace = Column(String(253), nullable=False)
    uid = Column(String(255), nullable=True)

    # Status
    status = Column(String(50), nullable=False)
    phase = Column(String(50), nullable=True)
    reason = Column(String(255), nullable=True)

    # Pod specification
    node_name = Column(String(253), nullable=True)
    images = Column(ARRAY(String), default=list, comment="Container images")
    containers = Column(JSON, default=list)

    # Labels and annotations
    labels = Column(JSON, default=dict)
    annotations = Column(JSON, default=dict)

    # Timestamps
    start_time = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True),
                        default=datetime.utcnow, onupdate=datetime.utcnow)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("cluster_id", "namespace", "name",
                         name="unique_pod_per_cluster"),
        Index("idx_k8s_pods_cluster", "cluster_id"),
        Index("idx_k8s_pods_namespace", "namespace"),
        Index("idx_k8s_pods_status", "status"),
    )


class K8sDeployment(Base):
    """Kubernetes Deployment resource tracking."""

    __tablename__ = "k8s_deployments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cluster_id = Column(String(255), nullable=False,
                        comment="Cluster identifier")

    # Deployment identification
    name = Column(String(253), nullable=False)
    namespace = Column(String(253), nullable=False)
    uid = Column(String(255), nullable=True)

    # Specification
    replicas = Column(Integer, default=1)
    ready_replicas = Column(Integer, default=0)
    strategy_type = Column(String(50), nullable=True,
                           comment="RollingUpdate, Recreate")
    strategy_rolling_update = Column(JSON, nullable=True)

    # Selector
    selector_match_labels = Column(JSON, default=dict)
    selector_match_expressions = Column(JSON, default=list)

    # Template
    pod_template_labels = Column(JSON, default=dict)
    pod_template_spec = Column(JSON, default=dict)

    # Status conditions
    conditions = Column(JSON, default=list)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True),
                        default=datetime.utcnow, onupdate=datetime.utcnow)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("cluster_id", "namespace", "name",
                         name="unique_deployment_per_cluster"),
        Index("idx_k8s_deployments_cluster", "cluster_id"),
        Index("idx_k8s_deployments_namespace", "namespace"),
    )


class K8sService(Base):
    """Kubernetes Service resource tracking."""

    __tablename__ = "k8s_services"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cluster_id = Column(String(255), nullable=False,
                        comment="Cluster identifier")

    # Service identification
    name = Column(String(253), nullable=False)
    namespace = Column(String(253), nullable=False)
    uid = Column(String(255), nullable=True)

    # Specification
    type = Column(String(50), nullable=False,
                  comment="ClusterIP, NodePort, LoadBalancer, ExternalName")
    cluster_ip = Column(String(255), nullable=True)
    external_ip = Column(ARRAY(String), default=list)
    ports = Column(JSON, default=list, comment="Service ports configuration")

    # Selector
    selector = Column(JSON, default=dict)

    # External traffic policy
    external_traffic_policy = Column(String(50), nullable=True)
    health_check_node_port = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True),
                        default=datetime.utcnow, onupdate=datetime.utcnow)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("cluster_id", "namespace", "name",
                         name="unique_service_per_cluster"),
        Index("idx_k8s_services_cluster", "cluster_id"),
        Index("idx_k8s_services_namespace", "namespace"),
        Index("idx_k8s_services_type", "type"),
    )


class K8sNode(Base):
    """Kubernetes Node resource tracking."""

    __tablename__ = "k8s_nodes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cluster_id = Column(String(255), nullable=False,
                        comment="Cluster identifier")

    # Node identification
    name = Column(String(253), nullable=False)
    uid = Column(String(255), nullable=True)

    # Status
    status = Column(String(50), nullable=False,
                    comment="Ready, NotReady, Unknown")
    conditions = Column(JSON, default=list, comment="Node conditions")

    # Capacity
    capacity = Column(JSON, default=dict, comment="CPU, memory, pods capacity")
    allocatable = Column(JSON, default=dict, comment="Allocatable resources")
    node_info = Column(JSON, default=dict,
                       comment="Kubelet version, OS, kernel")

    # Labels and taints
    labels = Column(JSON, default=dict)
    taints = Column(JSON, default=list)

    # Addresses
    addresses = Column(JSON, default=list)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True),
                        default=datetime.utcnow, onupdate=datetime.utcnow)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("cluster_id", "name", name="unique_node_per_cluster"),
        Index("idx_k8s_nodes_cluster", "cluster_id"),
        Index("idx_k8s_nodes_status", "status"),
    )


class DiscoveredHostEnhanced(Base):
    """Enhanced discovered host with RAG metadata.

    This extends the existing discovered_hosts table with fields
    for Layer 1 structured storage enhancement.
    """

    __tablename__ = "discovered_hosts_enhanced"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    host_id = Column(
        UUID(as_uuid=True),
        ForeignKey("discovered_hosts.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Enhanced scan metadata (Layer 1)
    scan_metadata = Column(
        JSON, default=dict, comment="Full nmap/masscan output")
    service_banners = Column(
        Text, nullable=True, comment="Service banner text")

    # SSL certificate information
    ssl_certificate = Column(JSON, nullable=True, comment="SSL cert details")

    # Tracking
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    rag_document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("rag_documents.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True),
                        default=datetime.utcnow, onupdate=datetime.utcnow)


class DiscoveredPortEnhanced(Base):
    """Enhanced discovered port with RAG metadata.

    This extends the existing discovered_ports table with fields
    for Layer 1 structured storage enhancement.
    """

    __tablename__ = "discovered_ports_enhanced"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    port_id = Column(
        UUID(as_uuid=True),
        ForeignKey("discovered_ports.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Enhanced scan metadata (Layer 1)
    scan_metadata = Column(
        JSON, default=dict, comment="Detailed port scan output")
    service_banners = Column(
        Text, nullable=True, comment="Grabbed service banner")

    # SSL certificate information
    ssl_certificate = Column(
        JSON, nullable=True, comment="SSL cert info if applicable")
    tls_version = Column(String(50), nullable=True)
    certificate_subject = Column(String(500), nullable=True)

    # Tracking
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    rag_document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("rag_documents.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True),
                        default=datetime.utcnow, onupdate=datetime.utcnow)


class RAGIndexingJob(Base):
    """Tracks RAG indexing jobs for monitoring and recovery."""

    __tablename__ = "rag_indexing_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Job identification
    job_type = Column(String(50), nullable=False,
                      comment="full, incremental, source")
    source_type = Column(String(50), nullable=True,
                         comment="discovery, k8s, manual")
    source_id = Column(String(255), nullable=True)

    # Status
    status = Column(
        String(20),
        nullable=False,
        default="pending",
        comment="pending, running, completed, failed",
    )
    progress = Column(Integer, default=0, comment="Progress percentage")
    error_message = Column(Text, nullable=True)

    # Statistics
    documents_processed = Column(Integer, default=0)
    documents_indexed = Column(Integer, default=0)
    documents_failed = Column(Integer, default=0)
    embedding_tokens = Column(Integer, default=0)

    # Timing
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Request metadata
    triggered_by = Column(String(255), nullable=True)
    request_metadata = Column(JSON, default=dict)

    __table_args__ = (
        Index("idx_rag_jobs_status", "status"),
        Index("idx_rag_jobs_type", "job_type"),
    )


class SourceCitation(Base):
    """Stores source citations for RAG results.

    This enables traceability and citation of information
    returned by RAG queries.
    """

    __tablename__ = "source_citations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Citation identification
    citation_key = Column(String(255), nullable=False, unique=True)
    query_hash = Column(String(64), nullable=False)

    # Source information
    source_type = Column(String(50), nullable=False)
    source_id = Column(String(255), nullable=False)
    source_name = Column(String(500), nullable=True)
    source_location = Column(String(500), nullable=True,
                             comment="File path, URL, etc.")

    # Citation details
    content_snippet = Column(Text, nullable=True)
    relevance_score = Column(Integer, nullable=True)
    line_number = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_citations_query", "query_hash"),
        Index("idx_citations_source", "source_type", "source_id"),
    )
