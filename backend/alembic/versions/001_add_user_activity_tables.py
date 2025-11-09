"""Add user activity and segments tables

Revision ID: 001_user_activity
Revises:
Create Date: 2025-01-09 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_user_activity'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create user activity tracking tables."""

    # Create analytics schema if it doesn't exist
    op.execute('CREATE SCHEMA IF NOT EXISTS analytics')

    # Create user_activity table
    op.create_table(
        'user_activity',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('workspace_id', sa.String(), nullable=True),
        sa.Column('session_id', sa.String(), nullable=True),

        # Event details
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('event_name', sa.String(100), nullable=True),
        sa.Column('page_path', sa.String(255), nullable=True),

        # Context
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.String(), nullable=True),
        sa.Column('referrer', sa.String(), nullable=True),
        sa.Column('device_type', sa.String(20), nullable=True),
        sa.Column('browser', sa.String(50), nullable=True),
        sa.Column('os', sa.String(50), nullable=True),
        sa.Column('country_code', sa.String(2), nullable=True),

        # Event data
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),

        sa.PrimaryKeyConstraint('id'),
        schema='analytics'
    )

    # Create indices for performance
    op.create_index('ix_user_activity_id', 'user_activity', ['id'], unique=False, schema='analytics')
    op.create_index('ix_user_activity_user_id', 'user_activity', ['user_id'], unique=False, schema='analytics')
    op.create_index('ix_user_activity_workspace_id', 'user_activity', ['workspace_id'], unique=False, schema='analytics')
    op.create_index('ix_user_activity_session_id', 'user_activity', ['session_id'], unique=False, schema='analytics')
    op.create_index('ix_user_activity_event_type', 'user_activity', ['event_type'], unique=False, schema='analytics')
    op.create_index('ix_user_activity_created_at', 'user_activity', ['created_at'], unique=False, schema='analytics')

    # Create compound indices for common query patterns
    op.create_index('idx_user_activity_workspace_created', 'user_activity', ['workspace_id', 'created_at'], unique=False, schema='analytics')
    op.create_index('idx_user_activity_user_workspace', 'user_activity', ['user_id', 'workspace_id'], unique=False, schema='analytics')
    op.create_index('idx_user_activity_session_created', 'user_activity', ['session_id', 'created_at'], unique=False, schema='analytics')
    op.create_index('idx_user_activity_workspace_event_type', 'user_activity', ['workspace_id', 'event_type'], unique=False, schema='analytics')

    # Create user_segments table
    op.create_table(
        'user_segments',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('workspace_id', sa.String(), nullable=True),
        sa.Column('segment_name', sa.String(100), nullable=False),
        sa.Column('segment_type', sa.String(50), nullable=True),

        # Segment definition
        sa.Column('criteria', postgresql.JSON(astext_type=sa.Text()), nullable=False),

        # Cached metrics
        sa.Column('user_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('avg_engagement', sa.Float(), nullable=True),

        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),

        sa.PrimaryKeyConstraint('id'),
        schema='analytics'
    )

    # Create indices for user_segments
    op.create_index('ix_user_segments_id', 'user_segments', ['id'], unique=False, schema='analytics')
    op.create_index('ix_user_segments_workspace_id', 'user_segments', ['workspace_id'], unique=False, schema='analytics')


def downgrade():
    """Drop user activity tracking tables."""

    # Drop indices first
    op.drop_index('idx_user_activity_workspace_event_type', table_name='user_activity', schema='analytics')
    op.drop_index('idx_user_activity_session_created', table_name='user_activity', schema='analytics')
    op.drop_index('idx_user_activity_user_workspace', table_name='user_activity', schema='analytics')
    op.drop_index('idx_user_activity_workspace_created', table_name='user_activity', schema='analytics')
    op.drop_index('ix_user_activity_created_at', table_name='user_activity', schema='analytics')
    op.drop_index('ix_user_activity_event_type', table_name='user_activity', schema='analytics')
    op.drop_index('ix_user_activity_session_id', table_name='user_activity', schema='analytics')
    op.drop_index('ix_user_activity_workspace_id', table_name='user_activity', schema='analytics')
    op.drop_index('ix_user_activity_user_id', table_name='user_activity', schema='analytics')
    op.drop_index('ix_user_activity_id', table_name='user_activity', schema='analytics')

    # Drop tables
    op.drop_table('user_activity', schema='analytics')

    # Drop user_segments indices
    op.drop_index('ix_user_segments_workspace_id', table_name='user_segments', schema='analytics')
    op.drop_index('ix_user_segments_id', table_name='user_segments', schema='analytics')

    # Drop user_segments table
    op.drop_table('user_segments', schema='analytics')

    # Note: Not dropping analytics schema as it might be used by other migrations
