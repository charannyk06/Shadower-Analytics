"""Add export tables

Revision ID: 004_export_tables
Revises: 003_anomaly_detection
Create Date: 2025-01-13 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004_export_tables'
down_revision = '003_anomaly_detection'
branch_labels = None
depends_on = None


def upgrade():
    """Create export tables."""

    # Create export_jobs table
    op.create_table(
        'export_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('config', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('data_sources', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('format', sa.String(50), nullable=False),
        sa.Column('compression', sa.String(50), nullable=True),
        sa.Column('delivery_method', sa.String(50), nullable=True),
        sa.Column('delivery_config', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('encryption_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('encryption_config', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default="'queued'"),
        sa.Column('progress_percent', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('rows_processed', sa.BigInteger(), nullable=True, server_default='0'),
        sa.Column('total_rows', sa.BigInteger(), nullable=True, server_default='0'),
        sa.Column('current_table', sa.String(255), nullable=True),
        sa.Column('files_created', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('estimated_size_mb', sa.Float(), nullable=True),
        sa.Column('estimated_time_seconds', sa.Integer(), nullable=True),
        sa.Column('estimated_rows', sa.BigInteger(), nullable=True),
        sa.Column('files', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('total_size_mb', sa.Float(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('celery_task_id', sa.String(255), nullable=True),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        schema='analytics'
    )

    # Create indices for export_jobs
    op.create_index('ix_export_jobs_workspace_id', 'export_jobs', ['workspace_id'], unique=False, schema='analytics')
    op.create_index('ix_export_jobs_user_id', 'export_jobs', ['user_id'], unique=False, schema='analytics')
    op.create_index('ix_export_jobs_status', 'export_jobs', ['status'], unique=False, schema='analytics')
    op.create_index('ix_export_jobs_celery_task_id', 'export_jobs', ['celery_task_id'], unique=False, schema='analytics')
    op.create_index('idx_export_jobs_workspace_created', 'export_jobs', ['workspace_id', 'created_at'], unique=False, schema='analytics')

    # Create export_templates table
    op.create_table(
        'export_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('configuration', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('use_count', sa.Integer(), nullable=True, server_default='0'),

        sa.PrimaryKeyConstraint('id'),
        schema='analytics'
    )

    # Create indices for export_templates
    op.create_index('ix_export_templates_workspace_id', 'export_templates', ['workspace_id'], unique=False, schema='analytics')
    op.create_index('ix_export_templates_user_id', 'export_templates', ['user_id'], unique=False, schema='analytics')
    op.create_index('ix_export_templates_is_public', 'export_templates', ['is_public'], unique=False, schema='analytics')

    # Create export_schedules table
    op.create_table(
        'export_schedules',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('frequency', sa.String(50), nullable=False),
        sa.Column('schedule_config', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('retention_config', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('last_run_at', sa.DateTime(), nullable=True),
        sa.Column('last_job_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('next_run_at', sa.DateTime(), nullable=True),
        sa.Column('run_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('failure_count', sa.Integer(), nullable=True, server_default='0'),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['template_id'], ['analytics.export_templates.id'], ondelete='CASCADE'),
        schema='analytics'
    )

    # Create indices for export_schedules
    op.create_index('ix_export_schedules_workspace_id', 'export_schedules', ['workspace_id'], unique=False, schema='analytics')
    op.create_index('ix_export_schedules_is_active', 'export_schedules', ['is_active'], unique=False, schema='analytics')
    op.create_index('ix_export_schedules_next_run_at', 'export_schedules', ['next_run_at'], unique=False, schema='analytics')
    op.create_index('idx_export_schedules_active_next_run', 'export_schedules', ['is_active', 'next_run_at'], unique=False, schema='analytics')

    # Create export_files table
    op.create_table(
        'export_files',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('filename', sa.String(512), nullable=False),
        sa.Column('file_path', sa.String(1024), nullable=False),
        sa.Column('file_index', sa.Integer(), nullable=False),
        sa.Column('size_mb', sa.Float(), nullable=False),
        sa.Column('row_count', sa.BigInteger(), nullable=True),
        sa.Column('checksum', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('downloaded_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('last_downloaded_at', sa.DateTime(), nullable=True),
        sa.Column('storage_type', sa.String(50), nullable=True, server_default="'local'"),
        sa.Column('storage_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['job_id'], ['analytics.export_jobs.id'], ondelete='CASCADE'),
        schema='analytics'
    )

    # Create indices for export_files
    op.create_index('ix_export_files_job_id', 'export_files', ['job_id'], unique=False, schema='analytics')
    op.create_index('idx_export_files_job_index', 'export_files', ['job_id', 'file_index'], unique=False, schema='analytics')

    # Create export_metadata table
    op.create_table(
        'export_metadata',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('schema_info', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('statistics', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('source_database', sa.String(255), nullable=True),
        sa.Column('export_timestamp', sa.DateTime(), nullable=False),
        sa.Column('filters_applied', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('transformations_applied', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('validation_status', sa.String(50), nullable=True),
        sa.Column('validation_results', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['job_id'], ['analytics.export_jobs.id'], ondelete='CASCADE'),
        schema='analytics'
    )

    # Create indices for export_metadata
    op.create_index('ix_export_metadata_job_id', 'export_metadata', ['job_id'], unique=False, schema='analytics')

    # Add foreign key to export_jobs
    op.create_foreign_key(
        'fk_export_jobs_template_id',
        'export_jobs', 'export_templates',
        ['template_id'], ['id'],
        source_schema='analytics',
        referent_schema='analytics',
        ondelete='SET NULL'
    )


def downgrade():
    """Drop export tables."""

    # Drop foreign keys
    op.drop_constraint('fk_export_jobs_template_id', 'export_jobs', schema='analytics', type_='foreignkey')

    # Drop tables in reverse order
    op.drop_table('export_metadata', schema='analytics')
    op.drop_table('export_files', schema='analytics')
    op.drop_table('export_schedules', schema='analytics')
    op.drop_table('export_templates', schema='analytics')
    op.drop_table('export_jobs', schema='analytics')
