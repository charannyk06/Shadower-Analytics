"""Add collaboration analytics tables

Revision ID: 005_collaboration_analytics
Revises: 004_export_tables
Create Date: 2025-01-13 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005_collaboration_analytics'
down_revision = '004_export_tables'
branch_labels = None
depends_on = None


def upgrade():
    """Create collaboration analytics tables."""

    # Create multi_agent_workflows table
    op.create_table(
        'multi_agent_workflows',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('workflow_id', sa.String(), nullable=False),
        sa.Column('workspace_id', sa.String(), nullable=False),
        sa.Column('workflow_name', sa.String(255), nullable=False),
        sa.Column('workflow_type', sa.String(50), nullable=True),
        sa.Column('workflow_version', sa.String(50), nullable=True),
        sa.Column('workflow_definition', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('total_duration_ms', sa.Integer(), nullable=True),
        sa.Column('agents_involved', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('handoffs_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('parallel_executions', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('coordination_efficiency', sa.Float(), nullable=True),
        sa.Column('communication_overhead', sa.Float(), nullable=True),
        sa.Column('bottleneck_score', sa.Float(), nullable=True),
        sa.Column('synergy_index', sa.Float(), nullable=True),
        sa.Column('success_rate', sa.Float(), nullable=True),
        sa.Column('resource_cost', sa.Float(), nullable=True),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        schema='analytics'
    )

    # Create indices for multi_agent_workflows
    op.create_index('idx_workflows_workspace_status', 'multi_agent_workflows', ['workspace_id', 'status'], unique=False, schema='analytics')
    op.create_index('idx_workflows_started', 'multi_agent_workflows', ['started_at'], unique=False, schema='analytics')
    op.create_index('idx_workflows_workflow_type', 'multi_agent_workflows', ['workflow_type', 'started_at'], unique=False, schema='analytics')
    op.create_index('ix_multi_agent_workflows_workflow_id', 'multi_agent_workflows', ['workflow_id'], unique=True, schema='analytics')

    # Create agent_interactions table
    op.create_table(
        'agent_interactions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('workflow_id', sa.String(), nullable=False),
        sa.Column('workspace_id', sa.String(), nullable=False),
        sa.Column('source_agent_id', sa.String(), nullable=False),
        sa.Column('target_agent_id', sa.String(), nullable=False),
        sa.Column('interaction_type', sa.String(50), nullable=True),
        sa.Column('payload_size_bytes', sa.Integer(), nullable=True),
        sa.Column('data_transferred', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('transformation_applied', sa.String(), nullable=True),
        sa.Column('interaction_duration_ms', sa.Integer(), nullable=True),
        sa.Column('queue_time_ms', sa.Integer(), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('data_quality_score', sa.Float(), nullable=True),
        sa.Column('compatibility_score', sa.Float(), nullable=True),
        sa.Column('error_occurred', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('retry_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('error_type', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        schema='analytics'
    )

    # Create indices for agent_interactions
    op.create_index('idx_interactions_workflow', 'agent_interactions', ['workflow_id', 'created_at'], unique=False, schema='analytics')
    op.create_index('idx_interactions_agents', 'agent_interactions', ['source_agent_id', 'target_agent_id'], unique=False, schema='analytics')
    op.create_index('idx_interactions_type', 'agent_interactions', ['interaction_type', 'created_at'], unique=False, schema='analytics')
    op.create_index('idx_interactions_workspace', 'agent_interactions', ['workspace_id', 'created_at'], unique=False, schema='analytics')

    # Create agent_handoffs table
    op.create_table(
        'agent_handoffs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('handoff_id', sa.String(), nullable=False),
        sa.Column('workflow_id', sa.String(), nullable=False),
        sa.Column('workspace_id', sa.String(), nullable=False),
        sa.Column('source_agent_id', sa.String(), nullable=False),
        sa.Column('target_agent_id', sa.String(), nullable=False),
        sa.Column('preparation_time_ms', sa.Integer(), nullable=True),
        sa.Column('transfer_time_ms', sa.Integer(), nullable=True),
        sa.Column('acknowledgment_time_ms', sa.Integer(), nullable=True),
        sa.Column('total_handoff_time_ms', sa.Integer(), nullable=True),
        sa.Column('data_size_bytes', sa.Integer(), nullable=True),
        sa.Column('data_completeness', sa.Float(), nullable=True),
        sa.Column('schema_compatible', sa.Boolean(), nullable=True),
        sa.Column('transformation_required', sa.Boolean(), nullable=True),
        sa.Column('handoff_success', sa.Boolean(), nullable=False),
        sa.Column('data_integrity_maintained', sa.Boolean(), nullable=True),
        sa.Column('context_preserved', sa.Float(), nullable=True),
        sa.Column('information_loss', sa.Float(), nullable=True),
        sa.Column('retry_attempts', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('recovery_strategy', sa.String(100), nullable=True),
        sa.Column('recovery_time_ms', sa.Integer(), nullable=True),
        sa.Column('failure_reason', sa.String(), nullable=True),
        sa.Column('handoff_time', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        schema='analytics'
    )

    # Create indices for agent_handoffs
    op.create_index('idx_handoffs_workflow', 'agent_handoffs', ['workflow_id', 'handoff_time'], unique=False, schema='analytics')
    op.create_index('idx_handoffs_agents', 'agent_handoffs', ['source_agent_id', 'target_agent_id'], unique=False, schema='analytics')
    op.create_index('idx_handoffs_success', 'agent_handoffs', ['handoff_success', 'handoff_time'], unique=False, schema='analytics')
    op.create_index('idx_handoffs_workspace', 'agent_handoffs', ['workspace_id', 'handoff_time'], unique=False, schema='analytics')
    op.create_index('ix_agent_handoffs_handoff_id', 'agent_handoffs', ['handoff_id'], unique=True, schema='analytics')

    # Create agent_dependencies table
    op.create_table(
        'agent_dependencies',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('workspace_id', sa.String(), nullable=False),
        sa.Column('agent_id', sa.String(), nullable=False),
        sa.Column('depends_on_agent_id', sa.String(), nullable=False),
        sa.Column('dependency_type', sa.String(50), nullable=True),
        sa.Column('dependency_strength', sa.Float(), nullable=True),
        sa.Column('is_circular', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('is_critical_path', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('dependency_definition', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_verified', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        schema='analytics'
    )

    # Create indices for agent_dependencies
    op.create_index('idx_dependencies_workspace', 'agent_dependencies', ['workspace_id', 'is_active'], unique=False, schema='analytics')
    op.create_index('idx_dependencies_agents', 'agent_dependencies', ['agent_id', 'depends_on_agent_id'], unique=False, schema='analytics')
    op.create_index('idx_dependencies_type', 'agent_dependencies', ['dependency_type', 'is_active'], unique=False, schema='analytics')
    op.create_index('ix_agent_dependencies_is_critical_path', 'agent_dependencies', ['is_critical_path'], unique=False, schema='analytics')

    # Create collaboration_metrics table
    op.create_table(
        'collaboration_metrics',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('workspace_id', sa.String(), nullable=False),
        sa.Column('agent_id', sa.String(), nullable=True),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('period_type', sa.String(20), nullable=False),
        sa.Column('collaboration_efficiency_score', sa.Float(), nullable=True),
        sa.Column('avg_interaction_time_ms', sa.Float(), nullable=True),
        sa.Column('error_rate', sa.Float(), nullable=True),
        sa.Column('avg_quality_score', sa.Float(), nullable=True),
        sa.Column('avg_compatibility', sa.Float(), nullable=True),
        sa.Column('workflows_participated', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('successful_workflows', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('failed_workflows', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('avg_workflow_duration_ms', sa.Float(), nullable=True),
        sa.Column('total_interactions', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('outgoing_interactions', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('incoming_interactions', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('handoffs_given', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('handoffs_received', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('avg_queue_length', sa.Float(), nullable=True),
        sa.Column('peak_load', sa.Integer(), nullable=True),
        sa.Column('idle_time_percentage', sa.Float(), nullable=True),
        sa.Column('load_variance', sa.Float(), nullable=True),
        sa.Column('diversity_index', sa.Float(), nullable=True),
        sa.Column('collective_accuracy', sa.Float(), nullable=True),
        sa.Column('emergence_score', sa.Float(), nullable=True),
        sa.Column('adaptation_rate', sa.Float(), nullable=True),
        sa.Column('calculated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        schema='analytics'
    )

    # Create indices for collaboration_metrics
    op.create_index('idx_collab_metrics_workspace_period', 'collaboration_metrics', ['workspace_id', 'period_start', 'period_end'], unique=False, schema='analytics')
    op.create_index('idx_collab_metrics_agent_period', 'collaboration_metrics', ['agent_id', 'period_start'], unique=False, schema='analytics')
    op.create_index('idx_collab_metrics_calculated', 'collaboration_metrics', ['calculated_at'], unique=False, schema='analytics')

    # Create workflow_execution_steps table
    op.create_table(
        'workflow_execution_steps',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('workflow_id', sa.String(), nullable=False),
        sa.Column('workspace_id', sa.String(), nullable=False),
        sa.Column('agent_id', sa.String(), nullable=False),
        sa.Column('step_id', sa.String(100), nullable=False),
        sa.Column('step_name', sa.String(255), nullable=False),
        sa.Column('step_order', sa.Integer(), nullable=False),
        sa.Column('step_type', sa.String(50), nullable=True),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('queue_time_ms', sa.Integer(), nullable=True),
        sa.Column('depends_on_steps', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('blocking_steps', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('cpu_usage', sa.Float(), nullable=True),
        sa.Column('memory_usage', sa.Float(), nullable=True),
        sa.Column('credits_used', sa.Integer(), nullable=True),
        sa.Column('output_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        schema='analytics'
    )

    # Create indices for workflow_execution_steps
    op.create_index('idx_workflow_steps_workflow', 'workflow_execution_steps', ['workflow_id', 'step_order'], unique=False, schema='analytics')
    op.create_index('idx_workflow_steps_agent', 'workflow_execution_steps', ['agent_id', 'started_at'], unique=False, schema='analytics')
    op.create_index('idx_workflow_steps_status', 'workflow_execution_steps', ['status', 'started_at'], unique=False, schema='analytics')

    # Create collaboration_patterns table
    op.create_table(
        'collaboration_patterns',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('workspace_id', sa.String(), nullable=False),
        sa.Column('pattern_id', sa.String(100), nullable=False),
        sa.Column('pattern_type', sa.String(50), nullable=False),
        sa.Column('pattern_name', sa.String(255), nullable=False),
        sa.Column('pattern_description', sa.String(), nullable=True),
        sa.Column('agents_involved', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('pattern_definition', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('occurrence_frequency', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('success_rate', sa.Float(), nullable=True),
        sa.Column('avg_performance', sa.Float(), nullable=True),
        sa.Column('efficiency_score', sa.Float(), nullable=True),
        sa.Column('optimization_opportunities', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('redundancy_detected', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('is_optimal', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('detected_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('last_seen', sa.DateTime(), nullable=True),
        sa.Column('detection_confidence', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        schema='analytics'
    )

    # Create indices for collaboration_patterns
    op.create_index('idx_collab_patterns_workspace_type', 'collaboration_patterns', ['workspace_id', 'pattern_type'], unique=False, schema='analytics')
    op.create_index('idx_collab_patterns_detected', 'collaboration_patterns', ['detected_at'], unique=False, schema='analytics')
    op.create_index('idx_collab_patterns_frequency', 'collaboration_patterns', ['occurrence_frequency'], unique=False, schema='analytics')
    op.create_index('ix_collaboration_patterns_pattern_id', 'collaboration_patterns', ['pattern_id'], unique=True, schema='analytics')

    # Create load_balancing_metrics table
    op.create_table(
        'load_balancing_metrics',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('workspace_id', sa.String(), nullable=False),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('period_type', sa.String(20), nullable=False),
        sa.Column('load_distribution', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('gini_coefficient', sa.Float(), nullable=True),
        sa.Column('load_skewness', sa.Float(), nullable=True),
        sa.Column('load_variance', sa.Float(), nullable=True),
        sa.Column('overloaded_agents', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('underutilized_agents', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('rebalancing_strategy', sa.String(100), nullable=True),
        sa.Column('agent_scaling_recommendations', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('workflow_reassignment_suggestions', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('calculated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        schema='analytics'
    )

    # Create indices for load_balancing_metrics
    op.create_index('idx_load_metrics_workspace_period', 'load_balancing_metrics', ['workspace_id', 'period_start'], unique=False, schema='analytics')
    op.create_index('idx_load_metrics_imbalance', 'load_balancing_metrics', ['gini_coefficient'], unique=False, schema='analytics')


def downgrade():
    """Drop collaboration analytics tables."""

    op.drop_table('load_balancing_metrics', schema='analytics')
    op.drop_table('collaboration_patterns', schema='analytics')
    op.drop_table('workflow_execution_steps', schema='analytics')
    op.drop_table('collaboration_metrics', schema='analytics')
    op.drop_table('agent_dependencies', schema='analytics')
    op.drop_table('agent_handoffs', schema='analytics')
    op.drop_table('agent_interactions', schema='analytics')
    op.drop_table('multi_agent_workflows', schema='analytics')
