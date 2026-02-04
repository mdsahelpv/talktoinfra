"""Initial schema for Onboarding Service.

Revision ID: 001
Revises: 
Create Date: 2026-02-04

"""

from datetime import datetime
from typing import Any, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid


# revision identifiers, used by Alembic
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Any, None] = None
depends_on: Union[str, Any, None] = None


def upgrade() -> None:
    """Create initial database schema."""

    # Create clusters table
    op.create_table(
        'clusters',
        sa.Column('id', UUID(as_uuid=True),
                  primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('provider', sa.String(50),
                  nullable=False, default='kubernetes'),
        sa.Column('api_endpoint', sa.String(500), nullable=True),
        sa.Column('certificate_authority', sa.Text, nullable=True),
        sa.Column('skip_tls_verify', sa.Boolean, default=False),
        sa.Column('status', sa.String(50), nullable=False, default='pending'),
        sa.Column('connection_status', sa.String(50), nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('include_namespaces', sa.JSON, nullable=True),
        sa.Column('exclude_namespaces', sa.JSON, nullable=True),
        sa.Column('labels', sa.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime,
                  default=datetime.utcnow, nullable=False),
        sa.Column('updated_at', sa.DateTime,
                  default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.Column('last_sync_at', sa.DateTime, nullable=True),
        sa.Column('deleted_at', sa.DateTime, nullable=True),
    )

    # Create cloud_accounts table
    op.create_table(
        'cloud_accounts',
        sa.Column('id', UUID(as_uuid=True),
                  primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('aws_account_id', sa.String(50), nullable=True),
        sa.Column('azure_subscription_id', sa.String(100), nullable=True),
        sa.Column('azure_tenant_id', sa.String(100), nullable=True),
        sa.Column('gcp_project_id', sa.String(100), nullable=True),
        sa.Column('regions', sa.JSON, nullable=True),
        sa.Column('resource_types', sa.JSON, nullable=True),
        sa.Column('resource_groups', sa.JSON, nullable=True),
        sa.Column('status', sa.String(50), nullable=False, default='pending'),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('labels', sa.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime,
                  default=datetime.utcnow, nullable=False),
        sa.Column('updated_at', sa.DateTime,
                  default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.Column('last_sync_at', sa.DateTime, nullable=True),
        sa.Column('deleted_at', sa.DateTime, nullable=True),
    )

    # Create credentials table
    op.create_table(
        'credentials',
        sa.Column('id', UUID(as_uuid=True),
                  primary_key=True, default=uuid.uuid4),
        sa.Column('cluster_id', UUID(as_uuid=True), sa.ForeignKey(
            'clusters.id'), nullable=True, index=True),
        sa.Column('cloud_account_id', UUID(as_uuid=True), sa.ForeignKey(
            'cloud_accounts.id'), nullable=True, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('credential_type', sa.String(100), nullable=False),
        sa.Column('encrypted_data', sa.Text, nullable=False),
        sa.Column('encryption_key_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime,
                  default=datetime.utcnow, nullable=False),
        sa.Column('updated_at', sa.DateTime,
                  default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.Column('last_used_at', sa.DateTime, nullable=True),
        sa.Column('expires_at', sa.DateTime, nullable=True),
        sa.Column('rotation_required', sa.Boolean, default=False),
        sa.Column('rotation_period_days', sa.Integer, nullable=True),
        sa.Column('last_rotated_at', sa.DateTime, nullable=True),
        sa.Column('rotated_from', UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime, nullable=True),
        sa.Column('deprecated', sa.Boolean, default=False),
        sa.Column('deprecated_at', sa.DateTime, nullable=True),
        sa.Column('replaced_by', UUID(as_uuid=True), nullable=True),
    )

    # Create sync_jobs table
    op.create_table(
        'sync_jobs',
        sa.Column('id', UUID(as_uuid=True),
                  primary_key=True, default=uuid.uuid4),
        sa.Column('cluster_id', UUID(as_uuid=True), sa.ForeignKey(
            'clusters.id'), nullable=False, index=True),
        sa.Column('job_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('resources_found', sa.Integer, default=0),
        sa.Column('resources_synced', sa.Integer, default=0),
        sa.Column('errors_count', sa.Integer, default=0),
        sa.Column('error_details', sa.JSON, nullable=True),
        sa.Column('started_at', sa.DateTime, nullable=True),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime,
                  default=datetime.utcnow, nullable=False),
    )

    # Create credential_audit_logs table
    op.create_table(
        'credential_audit_logs',
        sa.Column('id', UUID(as_uuid=True),
                  primary_key=True, default=uuid.uuid4),
        sa.Column('credential_id', UUID(as_uuid=True), sa.ForeignKey(
            'credentials.id'), nullable=False, index=True),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('accessed_by', sa.String(255), nullable=True),
        sa.Column('access_reason', sa.Text, nullable=True),
        sa.Column('success', sa.Boolean, nullable=False),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime,
                  default=datetime.utcnow, nullable=False),
        sa.Column('request_ip', sa.String(50), nullable=True),
        sa.Column('request_user_agent', sa.String(500), nullable=True),
    )

    # Create indexes
    op.create_index('idx_clusters_name', 'clusters', ['name'])
    op.create_index('idx_clusters_provider', 'clusters', ['provider'])
    op.create_index('idx_cloud_accounts_name', 'cloud_accounts', ['name'])
    op.create_index('idx_cloud_accounts_provider',
                    'cloud_accounts', ['provider'])
    op.create_index('idx_credentials_cluster_id',
                    'credentials', ['cluster_id'])
    op.create_index('idx_credentials_cloud_account_id',
                    'credentials', ['cloud_account_id'])


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table('credential_audit_logs')
    op.drop_table('sync_jobs')
    op.drop_table('credentials')
    op.drop_table('cloud_accounts')
    op.drop_table('clusters')
