"""Add anomaly detection tables

Revision ID: 003_anomaly_detection
Revises: 002_aggregation
Create Date: 2025-01-12 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_anomaly_detection'
down_revision = '002_aggregation'
branch_labels = None
depends_on = None


def upgrade():
    """Create anomaly detection tables."""

    # Create anomaly_detections table
    op.create_table(
        'anomaly_detections',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('metric_type', sa.String(100), nullable=False),
        sa.Column('detected_at', sa.DateTime(), nullable=False),
        sa.Column('anomaly_value', sa.Numeric(), nullable=True),
        sa.Column('expected_range', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('anomaly_score', sa.Numeric(), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),  # low, medium, high, critical
        sa.Column('detection_method', sa.String(50), nullable=False),  # zscore, isolation_forest, lstm, threshold
        sa.Column('context', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('is_acknowledged', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('acknowledged_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),

        sa.PrimaryKeyConstraint('id'),
        schema='analytics'
    )

    # Create indices for anomaly_detections
    op.create_index('ix_anomaly_detections_id', 'anomaly_detections', ['id'], unique=False, schema='analytics')
    op.create_index('ix_anomaly_detections_workspace_id', 'anomaly_detections', ['workspace_id'], unique=False, schema='analytics')
    op.create_index('ix_anomaly_detections_metric_type', 'anomaly_detections', ['metric_type'], unique=False, schema='analytics')
    op.create_index('ix_anomaly_detections_detected_at', 'anomaly_detections', ['detected_at'], unique=False, schema='analytics')
    op.create_index('ix_anomaly_detections_severity', 'anomaly_detections', ['severity'], unique=False, schema='analytics')
    op.create_index('idx_anomaly_workspace_time', 'anomaly_detections', ['workspace_id', 'detected_at'], unique=False, schema='analytics')
    op.create_index('idx_anomaly_severity_ack', 'anomaly_detections', ['severity', 'is_acknowledged'], unique=False, schema='analytics')
    op.create_index('idx_anomaly_metric_workspace', 'anomaly_detections', ['metric_type', 'workspace_id'], unique=False, schema='analytics')

    # Create anomaly_rules table
    op.create_table(
        'anomaly_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=True),  # NULL = global rule
        sa.Column('metric_type', sa.String(100), nullable=False),
        sa.Column('rule_name', sa.String(255), nullable=False),
        sa.Column('detection_method', sa.String(50), nullable=False),
        sa.Column('parameters', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('auto_alert', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('alert_channels', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),

        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'metric_type', 'rule_name', name='uq_anomaly_rules_workspace_metric_name'),
        schema='analytics'
    )

    # Create indices for anomaly_rules
    op.create_index('ix_anomaly_rules_id', 'anomaly_rules', ['id'], unique=False, schema='analytics')
    op.create_index('ix_anomaly_rules_workspace_id', 'anomaly_rules', ['workspace_id'], unique=False, schema='analytics')
    op.create_index('ix_anomaly_rules_metric_type', 'anomaly_rules', ['metric_type'], unique=False, schema='analytics')
    op.create_index('ix_anomaly_rules_is_active', 'anomaly_rules', ['is_active'], unique=False, schema='analytics')
    op.create_index('idx_anomaly_rules_workspace_metric', 'anomaly_rules', ['workspace_id', 'metric_type'], unique=False, schema='analytics')

    # Create baseline_models table
    op.create_table(
        'baseline_models',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('metric_type', sa.String(100), nullable=False),
        sa.Column('model_type', sa.String(50), nullable=False),  # zscore, isolation_forest, lstm
        sa.Column('model_parameters', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('statistics', postgresql.JSON(astext_type=sa.Text()), nullable=False),  # mean, std, percentiles
        sa.Column('training_data_start', sa.Date(), nullable=False),
        sa.Column('training_data_end', sa.Date(), nullable=False),
        sa.Column('accuracy_metrics', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=False, server_default=sa.text('now()')),

        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'metric_type', 'model_type', name='uq_baseline_models_workspace_metric_type'),
        schema='analytics'
    )

    # Create indices for baseline_models
    op.create_index('ix_baseline_models_id', 'baseline_models', ['id'], unique=False, schema='analytics')
    op.create_index('ix_baseline_models_workspace_id', 'baseline_models', ['workspace_id'], unique=False, schema='analytics')
    op.create_index('ix_baseline_models_metric_type', 'baseline_models', ['metric_type'], unique=False, schema='analytics')
    op.create_index('ix_baseline_models_model_type', 'baseline_models', ['model_type'], unique=False, schema='analytics')
    op.create_index('idx_baseline_models_workspace_metric', 'baseline_models', ['workspace_id', 'metric_type'], unique=False, schema='analytics')


def downgrade():
    """Drop anomaly detection tables."""

    # Drop baseline_models
    op.drop_index('idx_baseline_models_workspace_metric', table_name='baseline_models', schema='analytics')
    op.drop_index('ix_baseline_models_model_type', table_name='baseline_models', schema='analytics')
    op.drop_index('ix_baseline_models_metric_type', table_name='baseline_models', schema='analytics')
    op.drop_index('ix_baseline_models_workspace_id', table_name='baseline_models', schema='analytics')
    op.drop_index('ix_baseline_models_id', table_name='baseline_models', schema='analytics')
    op.drop_table('baseline_models', schema='analytics')

    # Drop anomaly_rules
    op.drop_index('idx_anomaly_rules_workspace_metric', table_name='anomaly_rules', schema='analytics')
    op.drop_index('ix_anomaly_rules_is_active', table_name='anomaly_rules', schema='analytics')
    op.drop_index('ix_anomaly_rules_metric_type', table_name='anomaly_rules', schema='analytics')
    op.drop_index('ix_anomaly_rules_workspace_id', table_name='anomaly_rules', schema='analytics')
    op.drop_index('ix_anomaly_rules_id', table_name='anomaly_rules', schema='analytics')
    op.drop_table('anomaly_rules', schema='analytics')

    # Drop anomaly_detections
    op.drop_index('idx_anomaly_metric_workspace', table_name='anomaly_detections', schema='analytics')
    op.drop_index('idx_anomaly_severity_ack', table_name='anomaly_detections', schema='analytics')
    op.drop_index('idx_anomaly_workspace_time', table_name='anomaly_detections', schema='analytics')
    op.drop_index('ix_anomaly_detections_severity', table_name='anomaly_detections', schema='analytics')
    op.drop_index('ix_anomaly_detections_detected_at', table_name='anomaly_detections', schema='analytics')
    op.drop_index('ix_anomaly_detections_metric_type', table_name='anomaly_detections', schema='analytics')
    op.drop_index('ix_anomaly_detections_workspace_id', table_name='anomaly_detections', schema='analytics')
    op.drop_index('ix_anomaly_detections_id', table_name='anomaly_detections', schema='analytics')
    op.drop_table('anomaly_detections', schema='analytics')
