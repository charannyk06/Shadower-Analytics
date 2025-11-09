"""Add aggregation tables for rollups

Revision ID: 002_aggregation
Revises: 001_user_activity
Create Date: 2025-01-09 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_aggregation'
down_revision = '001_user_activity'
branch_labels = None
depends_on = None


def upgrade():
    """Create aggregation tables for rollups."""

    # Create execution_metrics_hourly table
    op.create_table(
        'execution_metrics_hourly',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workspace_id', sa.String(), nullable=False),
        sa.Column('hour', sa.DateTime(), nullable=False),

        # Execution counts
        sa.Column('total_executions', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('successful_executions', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('failed_executions', sa.Integer(), nullable=True, server_default='0'),

        # Performance metrics
        sa.Column('avg_runtime', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('p50_runtime', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('p95_runtime', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('p99_runtime', sa.Float(), nullable=True, server_default='0.0'),

        # Resource consumption
        sa.Column('total_credits', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('avg_credits_per_run', sa.Float(), nullable=True, server_default='0.0'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),

        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'hour', name='uq_exec_metrics_hourly_workspace_hour'),
        schema='analytics'
    )

    # Create indices for execution_metrics_hourly
    op.create_index('ix_exec_metrics_hourly_id', 'execution_metrics_hourly', ['id'], unique=False, schema='analytics')
    op.create_index('ix_exec_metrics_hourly_workspace_id', 'execution_metrics_hourly', ['workspace_id'], unique=False, schema='analytics')
    op.create_index('ix_exec_metrics_hourly_hour', 'execution_metrics_hourly', ['hour'], unique=False, schema='analytics')
    op.create_index('idx_exec_metrics_hourly_workspace_hour', 'execution_metrics_hourly', ['workspace_id', 'hour'], unique=False, schema='analytics')

    # Create execution_metrics_daily table
    op.create_table(
        'execution_metrics_daily',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workspace_id', sa.String(), nullable=False),
        sa.Column('date', sa.DateTime(), nullable=False),

        # Execution counts
        sa.Column('total_executions', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('successful_executions', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('failed_executions', sa.Integer(), nullable=True, server_default='0'),

        # Performance metrics
        sa.Column('avg_runtime', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('p50_runtime', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('p95_runtime', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('p99_runtime', sa.Float(), nullable=True, server_default='0.0'),

        # Resource consumption
        sa.Column('total_credits', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('avg_credits_per_run', sa.Float(), nullable=True, server_default='0.0'),

        # Activity metrics
        sa.Column('unique_users', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('unique_agents', sa.Integer(), nullable=True, server_default='0'),

        # Health score
        sa.Column('health_score', sa.Float(), nullable=True, server_default='0.0'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),

        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'date', name='uq_exec_metrics_daily_workspace_date'),
        schema='analytics'
    )

    # Create indices for execution_metrics_daily
    op.create_index('ix_exec_metrics_daily_id', 'execution_metrics_daily', ['id'], unique=False, schema='analytics')
    op.create_index('ix_exec_metrics_daily_workspace_id', 'execution_metrics_daily', ['workspace_id'], unique=False, schema='analytics')
    op.create_index('ix_exec_metrics_daily_date', 'execution_metrics_daily', ['date'], unique=False, schema='analytics')
    op.create_index('idx_exec_metrics_daily_workspace_date', 'execution_metrics_daily', ['workspace_id', 'date'], unique=False, schema='analytics')

    # Create user_activity_hourly table
    op.create_table(
        'user_activity_hourly',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workspace_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('hour', sa.DateTime(), nullable=False),

        # Activity counts
        sa.Column('total_events', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('page_views', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('unique_sessions', sa.Integer(), nullable=True, server_default='0'),

        # Engagement metrics
        sa.Column('active_duration_seconds', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('avg_session_duration', sa.Float(), nullable=True, server_default='0.0'),

        # Event type breakdown
        sa.Column('event_type_counts', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='{}'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),

        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'user_id', 'hour', name='uq_user_activity_hourly_workspace_user_hour'),
        schema='analytics'
    )

    # Create indices for user_activity_hourly
    op.create_index('ix_user_activity_hourly_id', 'user_activity_hourly', ['id'], unique=False, schema='analytics')
    op.create_index('ix_user_activity_hourly_workspace_id', 'user_activity_hourly', ['workspace_id'], unique=False, schema='analytics')
    op.create_index('ix_user_activity_hourly_user_id', 'user_activity_hourly', ['user_id'], unique=False, schema='analytics')
    op.create_index('ix_user_activity_hourly_hour', 'user_activity_hourly', ['hour'], unique=False, schema='analytics')
    op.create_index('idx_user_activity_hourly_workspace_hour', 'user_activity_hourly', ['workspace_id', 'hour'], unique=False, schema='analytics')
    op.create_index('idx_user_activity_hourly_user_hour', 'user_activity_hourly', ['user_id', 'hour'], unique=False, schema='analytics')

    # Create credit_consumption_hourly table
    # Note: user_id and agent_id use empty string as default instead of NULL
    # to avoid NULL handling issues with unique constraints
    op.create_table(
        'credit_consumption_hourly',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workspace_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False, server_default=''),
        sa.Column('agent_id', sa.String(), nullable=False, server_default=''),
        sa.Column('hour', sa.DateTime(), nullable=False),

        # Credit metrics
        sa.Column('total_credits', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('avg_credits_per_execution', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('peak_credits_per_execution', sa.Integer(), nullable=True, server_default='0'),

        # Efficiency metrics
        sa.Column('executions_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('successful_executions', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('credits_per_success', sa.Float(), nullable=True, server_default='0.0'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),

        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'user_id', 'agent_id', 'hour', name='uq_credit_hourly_workspace_user_agent_hour'),
        schema='analytics'
    )

    # Create indices for credit_consumption_hourly
    op.create_index('ix_credit_hourly_id', 'credit_consumption_hourly', ['id'], unique=False, schema='analytics')
    op.create_index('ix_credit_hourly_workspace_id', 'credit_consumption_hourly', ['workspace_id'], unique=False, schema='analytics')
    op.create_index('ix_credit_hourly_user_id', 'credit_consumption_hourly', ['user_id'], unique=False, schema='analytics')
    op.create_index('ix_credit_hourly_agent_id', 'credit_consumption_hourly', ['agent_id'], unique=False, schema='analytics')
    op.create_index('ix_credit_hourly_hour', 'credit_consumption_hourly', ['hour'], unique=False, schema='analytics')
    op.create_index('idx_credit_hourly_workspace_hour', 'credit_consumption_hourly', ['workspace_id', 'hour'], unique=False, schema='analytics')
    op.create_index('idx_credit_hourly_user_hour', 'credit_consumption_hourly', ['user_id', 'hour'], unique=False, schema='analytics')


def downgrade():
    """Drop aggregation tables."""

    # Drop credit_consumption_hourly
    op.drop_index('idx_credit_hourly_user_hour', table_name='credit_consumption_hourly', schema='analytics')
    op.drop_index('idx_credit_hourly_workspace_hour', table_name='credit_consumption_hourly', schema='analytics')
    op.drop_index('ix_credit_hourly_hour', table_name='credit_consumption_hourly', schema='analytics')
    op.drop_index('ix_credit_hourly_agent_id', table_name='credit_consumption_hourly', schema='analytics')
    op.drop_index('ix_credit_hourly_user_id', table_name='credit_consumption_hourly', schema='analytics')
    op.drop_index('ix_credit_hourly_workspace_id', table_name='credit_consumption_hourly', schema='analytics')
    op.drop_index('ix_credit_hourly_id', table_name='credit_consumption_hourly', schema='analytics')
    op.drop_table('credit_consumption_hourly', schema='analytics')

    # Drop user_activity_hourly
    op.drop_index('idx_user_activity_hourly_user_hour', table_name='user_activity_hourly', schema='analytics')
    op.drop_index('idx_user_activity_hourly_workspace_hour', table_name='user_activity_hourly', schema='analytics')
    op.drop_index('ix_user_activity_hourly_hour', table_name='user_activity_hourly', schema='analytics')
    op.drop_index('ix_user_activity_hourly_user_id', table_name='user_activity_hourly', schema='analytics')
    op.drop_index('ix_user_activity_hourly_workspace_id', table_name='user_activity_hourly', schema='analytics')
    op.drop_index('ix_user_activity_hourly_id', table_name='user_activity_hourly', schema='analytics')
    op.drop_table('user_activity_hourly', schema='analytics')

    # Drop execution_metrics_daily
    op.drop_index('idx_exec_metrics_daily_workspace_date', table_name='execution_metrics_daily', schema='analytics')
    op.drop_index('ix_exec_metrics_daily_date', table_name='execution_metrics_daily', schema='analytics')
    op.drop_index('ix_exec_metrics_daily_workspace_id', table_name='execution_metrics_daily', schema='analytics')
    op.drop_index('ix_exec_metrics_daily_id', table_name='execution_metrics_daily', schema='analytics')
    op.drop_table('execution_metrics_daily', schema='analytics')

    # Drop execution_metrics_hourly
    op.drop_index('idx_exec_metrics_hourly_workspace_hour', table_name='execution_metrics_hourly', schema='analytics')
    op.drop_index('ix_exec_metrics_hourly_hour', table_name='execution_metrics_hourly', schema='analytics')
    op.drop_index('ix_exec_metrics_hourly_workspace_id', table_name='execution_metrics_hourly', schema='analytics')
    op.drop_index('ix_exec_metrics_hourly_id', table_name='execution_metrics_hourly', schema='analytics')
    op.drop_table('execution_metrics_hourly', schema='analytics')
