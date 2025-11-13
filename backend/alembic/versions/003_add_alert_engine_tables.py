"""Add alert engine tables

Revision ID: 003_alert_engine
Revises: 002_add_aggregation_tables
Create Date: 2025-01-12 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_alert_engine'
down_revision = '002_add_aggregation_tables'
branch_labels = None
depends_on = None


def upgrade():
    """Create alert engine tables."""

    # Ensure analytics schema exists
    op.execute('CREATE SCHEMA IF NOT EXISTS analytics')

    # Create alert_rules table
    op.create_table(
        'alert_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('rule_name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('metric_type', sa.String(100), nullable=False),
        sa.Column('condition_type', sa.String(50), nullable=False),  # 'threshold', 'change', 'anomaly', 'pattern'
        sa.Column('condition_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),  # 'info', 'warning', 'critical', 'emergency'
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('check_interval_minutes', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('cooldown_minutes', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('notification_channels', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('escalation_policy_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('last_evaluated_at', sa.DateTime(), nullable=True),
        sa.Column('last_triggered_at', sa.DateTime(), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        schema='analytics'
    )

    # Create indices for alert_rules
    op.create_index('idx_alert_rules_workspace', 'alert_rules', ['workspace_id', 'is_active'], unique=False, schema='analytics')
    op.create_index('idx_alert_rules_workspace_name', 'alert_rules', ['workspace_id', 'rule_name'], unique=True, schema='analytics')
    op.create_index('idx_alert_rules_active_next_check', 'alert_rules', ['is_active', 'last_evaluated_at'], unique=False, schema='analytics')
    op.create_index('idx_alert_rules_severity', 'alert_rules', ['severity'], unique=False, schema='analytics')

    # Create alerts table
    op.create_table(
        'alerts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('rule_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('alert_title', sa.String(500), nullable=False),
        sa.Column('alert_message', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('metric_value', sa.Numeric(), nullable=True),
        sa.Column('threshold_value', sa.Numeric(), nullable=True),
        sa.Column('triggered_at', sa.DateTime(), nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
        sa.Column('acknowledged_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('resolved_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('alert_context', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notification_sent', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('notification_channels', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('escalated', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('escalation_level', sa.Integer(), nullable=False, server_default='0'),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['rule_id'], ['analytics.alert_rules.id'], ondelete='CASCADE'),
        schema='analytics'
    )

    # Create indices for alerts
    op.create_index('idx_alerts_workspace', 'alerts', ['workspace_id', 'triggered_at'], unique=False, postgresql_using='btree', postgresql_ops={'triggered_at': 'DESC'}, schema='analytics')
    op.create_index('idx_alerts_unresolved', 'alerts', ['workspace_id', 'resolved_at'], unique=False, schema='analytics')
    op.create_index('idx_alerts_severity', 'alerts', ['severity', 'acknowledged_at'], unique=False, schema='analytics')
    op.create_index('idx_alerts_rule', 'alerts', ['rule_id', 'triggered_at'], unique=False, schema='analytics')
    op.create_index('idx_alerts_escalation', 'alerts', ['escalated', 'escalation_level'], unique=False, schema='analytics')

    # Create notification_history table
    op.create_table(
        'notification_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('alert_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('channel', sa.String(50), nullable=False),
        sa.Column('recipient', sa.Text(), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('delivery_status', sa.String(20), nullable=False),  # 'pending', 'sent', 'failed', 'bounced'
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('response_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['alert_id'], ['analytics.alerts.id'], ondelete='CASCADE'),
        schema='analytics'
    )

    # Create indices for notification_history
    op.create_index('idx_notifications_alert', 'notification_history', ['alert_id'], unique=False, schema='analytics')
    op.create_index('idx_notifications_status', 'notification_history', ['delivery_status', 'sent_at'], unique=False, postgresql_using='btree', postgresql_ops={'sent_at': 'DESC'}, schema='analytics')
    op.create_index('idx_notifications_channel', 'notification_history', ['channel', 'sent_at'], unique=False, schema='analytics')

    # Create escalation_policies table
    op.create_table(
        'escalation_policies',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('policy_name', sa.String(255), nullable=False),
        sa.Column('escalation_levels', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),

        sa.PrimaryKeyConstraint('id'),
        schema='analytics'
    )

    # Create indices for escalation_policies
    op.create_index('idx_escalation_policies_workspace', 'escalation_policies', ['workspace_id'], unique=False, schema='analytics')
    op.create_index('idx_escalation_policies_workspace_name', 'escalation_policies', ['workspace_id', 'policy_name'], unique=True, schema='analytics')

    # Create alert_suppressions table
    op.create_table(
        'alert_suppressions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('suppression_type', sa.String(50), nullable=False),  # 'rule', 'pattern', 'maintenance'
        sa.Column('pattern', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),

        sa.PrimaryKeyConstraint('id'),
        schema='analytics'
    )

    # Create indices for alert_suppressions
    op.create_index('idx_suppression_active', 'alert_suppressions', ['workspace_id', 'start_time', 'end_time'], unique=False, schema='analytics')
    op.create_index('idx_suppression_time_range', 'alert_suppressions', ['start_time', 'end_time'], unique=False, schema='analytics')

    # Add foreign key for escalation_policy_id in alert_rules
    op.create_foreign_key('fk_alert_rules_escalation_policy', 'alert_rules', 'escalation_policies', ['escalation_policy_id'], ['id'], source_schema='analytics', referent_schema='analytics', ondelete='SET NULL')


def downgrade():
    """Drop alert engine tables."""

    # Drop foreign key first
    op.drop_constraint('fk_alert_rules_escalation_policy', 'alert_rules', type_='foreignkey', schema='analytics')

    # Drop indices and tables in reverse order

    # alert_suppressions
    op.drop_index('idx_suppression_time_range', table_name='alert_suppressions', schema='analytics')
    op.drop_index('idx_suppression_active', table_name='alert_suppressions', schema='analytics')
    op.drop_table('alert_suppressions', schema='analytics')

    # escalation_policies
    op.drop_index('idx_escalation_policies_workspace_name', table_name='escalation_policies', schema='analytics')
    op.drop_index('idx_escalation_policies_workspace', table_name='escalation_policies', schema='analytics')
    op.drop_table('escalation_policies', schema='analytics')

    # notification_history
    op.drop_index('idx_notifications_channel', table_name='notification_history', schema='analytics')
    op.drop_index('idx_notifications_status', table_name='notification_history', schema='analytics')
    op.drop_index('idx_notifications_alert', table_name='notification_history', schema='analytics')
    op.drop_table('notification_history', schema='analytics')

    # alerts
    op.drop_index('idx_alerts_escalation', table_name='alerts', schema='analytics')
    op.drop_index('idx_alerts_rule', table_name='alerts', schema='analytics')
    op.drop_index('idx_alerts_severity', table_name='alerts', schema='analytics')
    op.drop_index('idx_alerts_unresolved', table_name='alerts', schema='analytics')
    op.drop_index('idx_alerts_workspace', table_name='alerts', schema='analytics')
    op.drop_table('alerts', schema='analytics')

    # alert_rules
    op.drop_index('idx_alert_rules_severity', table_name='alert_rules', schema='analytics')
    op.drop_index('idx_alert_rules_active_next_check', table_name='alert_rules', schema='analytics')
    op.drop_index('idx_alert_rules_workspace_name', table_name='alert_rules', schema='analytics')
    op.drop_index('idx_alert_rules_workspace', table_name='alert_rules', schema='analytics')
    op.drop_table('alert_rules', schema='analytics')
