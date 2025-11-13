"""Add execution analytics tables

Revision ID: 005_execution_analytics
Revises: 004_export_tables
Create Date: 2025-01-13 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005_execution_analytics'
down_revision = '004_export_tables'
branch_labels = None
depends_on = None


def upgrade():
    """Create execution analytics tables."""

    # Create agent_executions table for detailed execution tracking
    op.create_table(
        'agent_executions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('execution_id', sa.String(255), nullable=False, unique=True),
        sa.Column('agent_id', sa.String(255), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Execution details
        sa.Column('trigger_type', sa.String(50), nullable=True),  # 'manual', 'scheduled', 'webhook', 'api'
        sa.Column('trigger_source', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('input_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('output_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        # Performance metrics
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(20), nullable=True),  # 'pending', 'running', 'success', 'failed', 'timeout'
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_type', sa.String(100), nullable=True),

        # Resource usage
        sa.Column('credits_consumed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('tokens_used', postgresql.JSONB(astext_type=sa.Text()), nullable=True),  # {prompt: 1000, completion: 500}
        sa.Column('api_calls_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('memory_usage_mb', sa.Numeric(precision=10, scale=2), nullable=True),

        # Execution path
        sa.Column('steps_total', sa.Integer(), nullable=True),
        sa.Column('steps_completed', sa.Integer(), nullable=True),
        sa.Column('execution_graph', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('checkpoints', postgresql.ARRAY(postgresql.JSONB(astext_type=sa.Text())), nullable=True),

        # Context
        sa.Column('environment', sa.String(20), nullable=True),  # 'production', 'development', 'staging'
        sa.Column('runtime_mode', sa.String(20), nullable=True),  # 'default', 'fast'
        sa.Column('version', sa.String(50), nullable=True),

        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),

        sa.PrimaryKeyConstraint('id'),
        schema='analytics'
    )

    # Create indices for agent_executions
    op.create_index('ix_agent_executions_execution_id', 'agent_executions', ['execution_id'], unique=True, schema='analytics')
    op.create_index('ix_agent_executions_agent_id', 'agent_executions', ['agent_id'], unique=False, schema='analytics')
    op.create_index('ix_agent_executions_workspace_id', 'agent_executions', ['workspace_id'], unique=False, schema='analytics')
    op.create_index('ix_agent_executions_user_id', 'agent_executions', ['user_id'], unique=False, schema='analytics')
    op.create_index('ix_agent_executions_status', 'agent_executions', ['status'], unique=False, schema='analytics')

    # Composite indices for performance
    op.create_index('idx_agent_executions_agent_start', 'agent_executions', ['agent_id', 'start_time'], unique=False, schema='analytics')
    op.create_index('idx_agent_executions_workspace_start', 'agent_executions', ['workspace_id', 'start_time'], unique=False, schema='analytics')
    op.create_index('idx_agent_executions_status_workspace', 'agent_executions', ['status', 'workspace_id'], unique=False, schema='analytics')
    op.create_index('idx_agent_executions_duration', 'agent_executions', ['duration_ms'], unique=False, schema='analytics')

    # Create execution_steps table for detailed step tracking
    op.create_table(
        'execution_steps',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('execution_id', sa.String(255), nullable=False),
        sa.Column('step_index', sa.Integer(), nullable=False),
        sa.Column('step_name', sa.String(255), nullable=True),
        sa.Column('step_type', sa.String(50), nullable=True),  # 'action', 'decision', 'loop', 'api_call'

        # Step metrics
        sa.Column('start_time', sa.DateTime(), nullable=True),
        sa.Column('end_time', sa.DateTime(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(20), nullable=True),

        # Step data
        sa.Column('input', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('output', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error', postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        # Resource usage
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('api_calls', postgresql.ARRAY(postgresql.JSONB(astext_type=sa.Text())), nullable=True),

        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),

        sa.PrimaryKeyConstraint('id'),
        schema='analytics'
    )

    # Create indices for execution_steps
    op.create_index('ix_execution_steps_execution_id', 'execution_steps', ['execution_id'], unique=False, schema='analytics')
    op.create_index('idx_execution_steps_execution_step', 'execution_steps', ['execution_id', 'step_index'], unique=False, schema='analytics')
    op.create_index('idx_execution_steps_duration', 'execution_steps', ['duration_ms'], unique=False, schema='analytics')

    # Create execution_patterns table for pattern analysis results
    op.create_table(
        'execution_patterns',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('agent_id', sa.String(255), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('pattern_type', sa.String(50), nullable=False),  # 'hourly', 'input', 'path', 'bottleneck'

        # Pattern data
        sa.Column('pattern_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('frequency', sa.Integer(), nullable=True),
        sa.Column('avg_duration_ms', sa.Integer(), nullable=True),
        sa.Column('avg_credits', sa.Float(), nullable=True),
        sa.Column('success_rate', sa.Float(), nullable=True),

        # Analysis metadata
        sa.Column('analyzed_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('sample_size', sa.Integer(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),

        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),

        sa.PrimaryKeyConstraint('id'),
        schema='analytics'
    )

    # Create indices for execution_patterns
    op.create_index('ix_execution_patterns_agent_id', 'execution_patterns', ['agent_id'], unique=False, schema='analytics')
    op.create_index('ix_execution_patterns_workspace_id', 'execution_patterns', ['workspace_id'], unique=False, schema='analytics')
    op.create_index('idx_execution_patterns_type_analyzed', 'execution_patterns', ['pattern_type', 'analyzed_at'], unique=False, schema='analytics')

    # Create execution_bottlenecks table for performance bottleneck tracking
    op.create_table(
        'execution_bottlenecks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('agent_id', sa.String(255), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('step_name', sa.String(255), nullable=False),

        # Bottleneck metrics
        sa.Column('avg_duration_ms', sa.Integer(), nullable=False),
        sa.Column('duration_variance', sa.Float(), nullable=True),
        sa.Column('execution_count', sa.Integer(), nullable=False),
        sa.Column('p95_duration_ms', sa.Integer(), nullable=True),
        sa.Column('p99_duration_ms', sa.Integer(), nullable=True),

        # Impact analysis
        sa.Column('impact_score', sa.Float(), nullable=True),  # 0-100 score
        sa.Column('optimization_priority', sa.String(20), nullable=True),  # 'critical', 'high', 'medium', 'low'
        sa.Column('suggestions', postgresql.ARRAY(sa.Text()), nullable=True),

        sa.Column('detected_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),

        sa.PrimaryKeyConstraint('id'),
        schema='analytics'
    )

    # Create indices for execution_bottlenecks
    op.create_index('ix_execution_bottlenecks_agent_id', 'execution_bottlenecks', ['agent_id'], unique=False, schema='analytics')
    op.create_index('ix_execution_bottlenecks_workspace_id', 'execution_bottlenecks', ['workspace_id'], unique=False, schema='analytics')
    op.create_index('idx_execution_bottlenecks_priority', 'execution_bottlenecks', ['optimization_priority', 'impact_score'], unique=False, schema='analytics')


def downgrade():
    """Drop execution analytics tables."""

    # Drop tables in reverse order
    op.drop_table('execution_bottlenecks', schema='analytics')
    op.drop_table('execution_patterns', schema='analytics')
    op.drop_table('execution_steps', schema='analytics')
    op.drop_table('agent_executions', schema='analytics')
