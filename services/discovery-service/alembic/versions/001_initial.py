"""Initial migration creating all discovery service tables.

Revision ID: 001
Revises:
Create Date: 2026-02-02 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all discovery service tables with indexes and constraints."""

    # Create scan_jobs table
    op.create_table(
        "scan_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("scan_type", sa.String(20), nullable=False, server_default="python"),
        sa.Column("progress", sa.Integer, server_default="0"),
        sa.Column("ip_range", postgresql.CIDR(), nullable=False),
        sa.Column("ports", postgresql.ARRAY(sa.Integer()), nullable=False),
        sa.Column("total_hosts", sa.Integer(), nullable=True),
        sa.Column("scanned_hosts", sa.Integer(), server_default="0"),
        sa.Column("found_hosts", sa.Integer(), server_default="0"),
        sa.Column("created_by", sa.String(100), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("config", postgresql.JSON(), server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed', 'cancelled')",
            name="valid_scan_status",
        ),
        sa.CheckConstraint(
            "scan_type IN ('fast', 'detailed', 'hybrid', 'python')",
            name="valid_scan_type",
        ),
        sa.CheckConstraint("progress >= 0 AND progress <= 100", name="valid_progress"),
    )

    # Create indexes for scan_jobs
    op.create_index("ix_scan_jobs_status", "scan_jobs", ["status"])
    op.create_index("ix_scan_jobs_created_by", "scan_jobs", ["created_by"])
    op.create_index("ix_scan_jobs_created_at", "scan_jobs", ["created_at"])
    op.create_index("ix_scan_jobs_scan_type", "scan_jobs", ["scan_type"])

    # Create discovered_hosts table
    op.create_table(
        "discovered_hosts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("scan_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ip_address", postgresql.INET(), nullable=False),
        sa.Column("hostname", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column(
            "discovered_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "status IN ('alive', 'unreachable', 'filtered')", name="valid_host_status"
        ),
        sa.UniqueConstraint("job_id", "ip_address", name="unique_host_per_job"),
    )

    # Create indexes for discovered_hosts
    op.create_index("ix_discovered_hosts_job_id", "discovered_hosts", ["job_id"])
    op.create_index(
        "ix_discovered_hosts_ip_address", "discovered_hosts", ["ip_address"]
    )
    op.create_index("ix_discovered_hosts_status", "discovered_hosts", ["status"])
    op.create_index(
        "ix_discovered_hosts_discovered_at", "discovered_hosts", ["discovered_at"]
    )

    # Create discovered_ports table
    op.create_table(
        "discovered_ports",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "host_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("discovered_hosts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("service", sa.String(100), nullable=True),
        sa.Column("service_version", sa.String(255), nullable=True),
        sa.Column("banner", sa.Text(), nullable=True),
        sa.Column("protocol", sa.String(10), server_default="tcp"),
        sa.Column(
            "discovered_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint("port > 0 AND port <= 65535", name="valid_port_range"),
        sa.CheckConstraint(
            "status IN ('open', 'closed', 'filtered')", name="valid_port_status"
        ),
        sa.CheckConstraint("protocol IN ('tcp', 'udp')", name="valid_protocol"),
        sa.UniqueConstraint("host_id", "port", "protocol", name="unique_port_per_host"),
    )

    # Create indexes for discovered_ports
    op.create_index("ix_discovered_ports_host_id", "discovered_ports", ["host_id"])
    op.create_index("ix_discovered_ports_port", "discovered_ports", ["port"])
    op.create_index("ix_discovered_ports_status", "discovered_ports", ["status"])
    op.create_index("ix_discovered_ports_protocol", "discovered_ports", ["protocol"])
    op.create_index("ix_discovered_ports_service", "discovered_ports", ["service"])

    # Create managed_hosts table
    op.create_table(
        "managed_hosts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("ip_address", postgresql.INET(), nullable=False, unique=True),
        sa.Column("ports", postgresql.ARRAY(sa.Integer()), server_default="{}"),
        sa.Column("services", postgresql.ARRAY(sa.String()), server_default="{}"),
        sa.Column("status", sa.String(20), server_default="unknown"),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "first_discovered_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "discovered_by_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("scan_jobs.id"),
            nullable=True,
        ),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("added_by", sa.String(100), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSON(), server_default="{}"),
        sa.CheckConstraint(
            "status IN ('online', 'offline', 'unknown', 'degraded')",
            name="valid_managed_status",
        ),
    )

    # Create indexes for managed_hosts
    op.create_index("ix_managed_hosts_ip_address", "managed_hosts", ["ip_address"])
    op.create_index("ix_managed_hosts_status", "managed_hosts", ["status"])
    op.create_index("ix_managed_hosts_added_by", "managed_hosts", ["added_by"])
    op.create_index(
        "ix_managed_hosts_discovered_by_job_id",
        "managed_hosts",
        ["discovered_by_job_id"],
    )
    op.create_index("ix_managed_hosts_added_at", "managed_hosts", ["added_at"])
    op.create_index(
        "ix_managed_hosts_last_checked_at", "managed_hosts", ["last_checked_at"]
    )

    # Create host_health_checks table
    op.create_table(
        "host_health_checks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "host_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("managed_hosts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "checked_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "status IN ('online', 'offline', 'unknown', 'degraded')",
            name="valid_health_status",
        ),
    )

    # Create indexes for host_health_checks
    op.create_index("ix_host_health_checks_host_id", "host_health_checks", ["host_id"])
    op.create_index("ix_host_health_checks_status", "host_health_checks", ["status"])
    op.create_index(
        "ix_host_health_checks_checked_at", "host_health_checks", ["checked_at"]
    )

    # Create scan_exclusions table
    op.create_table(
        "scan_exclusions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("network", postgresql.CIDR(), nullable=False, unique=True),
        sa.Column("reason", sa.String(255), nullable=False),
        sa.Column("created_by", sa.String(100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("is_active", sa.Integer(), server_default="1"),
    )

    # Create indexes for scan_exclusions
    op.create_index("ix_scan_exclusions_network", "scan_exclusions", ["network"])
    op.create_index("ix_scan_exclusions_is_active", "scan_exclusions", ["is_active"])
    op.create_index("ix_scan_exclusions_created_by", "scan_exclusions", ["created_by"])


def downgrade() -> None:
    """Drop all discovery service tables."""

    # Drop in reverse order to handle foreign key dependencies
    op.drop_table("scan_exclusions")
    op.drop_table("host_health_checks")
    op.drop_table("managed_hosts")
    op.drop_table("discovered_ports")
    op.drop_table("discovered_hosts")
    op.drop_table("scan_jobs")
