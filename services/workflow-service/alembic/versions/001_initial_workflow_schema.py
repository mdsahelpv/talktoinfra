"""Initial workflow service schema

Revision ID: 001
Revises: 
Create Date: 2026-02-08

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create workflow_definitions table
    op.create_table(
        'workflow_definitions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True, default=''),
        sa.Column('version', sa.Integer(), nullable=True, default=1),
        sa.Column('steps', sa.JSON(), nullable=True, default=[]),
        sa.Column('entry_point', sa.String(), nullable=True, default=''),
        sa.Column('created_by', sa.String(), nullable=True, default=''),
        sa.Column('tags', sa.JSON(), nullable=True, default=[]),
        sa.Column('is_template', sa.Boolean(), nullable=True, default=False),
        sa.Column('parameters', sa.JSON(), nullable=True, default={}),
        sa.Column('parameter_schema', sa.JSON(), nullable=True, default={}),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workflow_definitions_id'),
                    'workflow_definitions', ['id'], unique=False)
    op.create_index(op.f('ix_workflow_definitions_name'),
                    'workflow_definitions', ['name'], unique=False)

    # Create workflow_executions table
    op.create_table(
        'workflow_executions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('workflow_id', sa.String(), nullable=True),
        sa.Column('workflow_version', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(), nullable=True, default='running'),
        sa.Column('current_step_id', sa.String(), nullable=True),
        sa.Column('parameters', sa.JSON(), nullable=True, default={}),
        sa.Column('context', sa.JSON(), nullable=True, default={}),
        sa.Column('results', sa.JSON(), nullable=True, default={}),
        sa.Column('errors', sa.JSON(), nullable=True, default=[]),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(), nullable=True, default=''),
        sa.Column('approved_by', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(
            ['workflow_id'], ['workflow_definitions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workflow_executions_id'),
                    'workflow_executions', ['id'], unique=False)

    # Create step_executions table
    op.create_table(
        'step_executions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('execution_id', sa.String(), nullable=True),
        sa.Column('step_id', sa.String(), nullable=True),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('step_type', sa.String(), nullable=True),
        sa.Column('order', sa.Integer(), nullable=True),
        sa.Column('config', sa.JSON(), nullable=True, default={}),
        sa.Column('status', sa.String(), nullable=True, default='pending'),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True, default=0),
        sa.ForeignKeyConstraint(
            ['execution_id'], ['workflow_executions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_step_executions_id'),
                    'step_executions', ['id'], unique=False)
    op.create_index(op.f('ix_step_executions_step_id'),
                    'step_executions', ['step_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_step_executions_step_id'),
                  table_name='step_executions')
    op.drop_index(op.f('ix_step_executions_id'), table_name='step_executions')
    op.drop_table('step_executions')

    op.drop_index(op.f('ix_workflow_executions_id'),
                  table_name='workflow_executions')
    op.drop_table('workflow_executions')

    op.drop_index(op.f('ix_workflow_definitions_name'),
                  table_name='workflow_definitions')
    op.drop_index(op.f('ix_workflow_definitions_id'),
                  table_name='workflow_definitions')
    op.drop_table('workflow_definitions')
