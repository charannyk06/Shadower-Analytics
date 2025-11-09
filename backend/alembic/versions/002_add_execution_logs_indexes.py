"""Add compound indexes for execution_logs table

Revision ID: 002_execution_logs_indexes
Revises: 001_user_activity
Create Date: 2025-01-09 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002_execution_logs_indexes'
down_revision = '001_user_activity'
branch_labels = None
depends_on = None


def upgrade():
    """Create compound indexes for execution_logs table to optimize comparison queries."""

    # Create compound indices for comparison queries performance
    # These indexes align with the query patterns in comparison_service.py

    # Index for agent-based queries with date filtering
    op.create_index(
        'idx_execution_logs_agent_date',
        'execution_logs',
        ['agent_id', 'started_at'],
        unique=False
    )

    # Index for workspace-based queries with date filtering
    op.create_index(
        'idx_execution_logs_workspace_date',
        'execution_logs',
        ['workspace_id', 'started_at'],
        unique=False
    )

    # Index for status-based queries with date filtering
    op.create_index(
        'idx_execution_logs_status_date',
        'execution_logs',
        ['status', 'started_at'],
        unique=False
    )

    # Index for combined agent and workspace queries with date filtering
    op.create_index(
        'idx_execution_logs_agent_workspace',
        'execution_logs',
        ['agent_id', 'workspace_id', 'started_at'],
        unique=False
    )


def downgrade():
    """Drop compound indexes for execution_logs table."""

    # Drop indices in reverse order
    op.drop_index('idx_execution_logs_agent_workspace', table_name='execution_logs')
    op.drop_index('idx_execution_logs_status_date', table_name='execution_logs')
    op.drop_index('idx_execution_logs_workspace_date', table_name='execution_logs')
    op.drop_index('idx_execution_logs_agent_date', table_name='execution_logs')
