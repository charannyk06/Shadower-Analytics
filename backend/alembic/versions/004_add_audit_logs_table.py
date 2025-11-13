"""Add audit logs table for security tracking.

Revision ID: 004_add_audit_logs
Revises: 003_add_alert_engine_tables
Create Date: 2025-01-13 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004_add_audit_logs'
down_revision = '003_add_alert_engine_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create audit_logs table for security and compliance tracking."""

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('workspace_id', sa.String(), nullable=True),
        sa.Column('resource_type', sa.String(length=100), nullable=True),
        sa.Column('resource_id', sa.String(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('details', postgresql.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('request_id', sa.String(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True, server_default='success'),
        sa.Column('error_message', sa.String(length=500), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('severity', sa.String(length=20), nullable=True, server_default='info'),
        sa.PrimaryKeyConstraint('id'),
        schema='analytics'
    )

    # Create indices for efficient querying
    op.create_index(
        'idx_audit_logs_event_type',
        'audit_logs',
        ['event_type'],
        schema='analytics'
    )

    op.create_index(
        'idx_audit_logs_user_id',
        'audit_logs',
        ['user_id'],
        schema='analytics'
    )

    op.create_index(
        'idx_audit_logs_workspace_id',
        'audit_logs',
        ['workspace_id'],
        schema='analytics'
    )

    op.create_index(
        'idx_audit_logs_timestamp',
        'audit_logs',
        ['timestamp'],
        schema='analytics'
    )

    op.create_index(
        'idx_audit_logs_resource',
        'audit_logs',
        ['resource_type', 'resource_id'],
        schema='analytics'
    )


def downgrade() -> None:
    """Drop audit_logs table and indices."""

    # Drop indices first
    op.drop_index('idx_audit_logs_resource', table_name='audit_logs', schema='analytics')
    op.drop_index('idx_audit_logs_timestamp', table_name='audit_logs', schema='analytics')
    op.drop_index('idx_audit_logs_workspace_id', table_name='audit_logs', schema='analytics')
    op.drop_index('idx_audit_logs_user_id', table_name='audit_logs', schema='analytics')
    op.drop_index('idx_audit_logs_event_type', table_name='audit_logs', schema='analytics')

    # Drop table
    op.drop_table('audit_logs', schema='analytics')
