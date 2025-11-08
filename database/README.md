# Shadow Analytics - Database Schema

This directory contains the complete PostgreSQL database schema for the Shadow Analytics system, including migrations, procedures, and maintenance scripts.

## Overview

The analytics database uses a separate `analytics` schema within a Supabase PostgreSQL instance, providing:
- Time-series optimized tables for user activity tracking
- Pre-aggregated metrics (hourly and daily rollups)
- Materialized views for high-performance queries
- Row-Level Security (RLS) for multi-tenant data isolation
- Automated triggers and maintenance procedures

## Directory Structure

```
database/
├── migrations/          # Database migrations (run in order)
│   ├── 001_create_analytics_schema.sql
│   ├── 002_create_core_tables.sql
│   ├── 003_create_specialized_tables.sql
│   ├── 004_create_materialized_views.sql
│   ├── 005_create_functions.sql
│   ├── 006_create_triggers.sql
│   ├── 007_create_rls_policies.sql
│   └── 008_create_performance_indexes.sql
├── procedures/          # Maintenance procedures
│   ├── refresh_materialized_views.sql
│   ├── aggregate_metrics.sql
│   └── cleanup_old_data.sql
├── run_migrations.sh    # Migration runner script
└── README.md           # This file
```

## Quick Start

### Running All Migrations

```bash
# Using the migration script (recommended)
./database/run_migrations.sh "postgresql://user:pass@localhost/db_name"

# Or with environment variable
export DATABASE_URL="postgresql://user:pass@localhost/db_name"
./database/run_migrations.sh
```

### Running Individual Migrations

```bash
# Run migrations in order
psql $DATABASE_URL -f database/migrations/001_create_analytics_schema.sql
psql $DATABASE_URL -f database/migrations/002_create_core_tables.sql
# ... and so on
```

## Schema Components

### Core Tables

#### 1. **user_activity**
Tracks all user events and interactions
- Page views, agent runs, errors, feature usage
- Session tracking with metadata
- Retention: 90 days

#### 2. **daily_metrics**
Daily aggregated metrics per workspace
- User metrics (total, active, new, returning)
- Execution metrics (runs, success rate, runtime)
- Credit consumption and costs
- Error rates and types

#### 3. **hourly_metrics**
Hourly metrics for real-time monitoring
- Active users and run counts
- Response time metrics
- Retention: 30 days

#### 4. **agent_performance**
Detailed performance metrics per agent
- Execution statistics with percentiles (p50, p75, p95, p99)
- Credit and token usage
- User ratings and feedback
- Error analysis

#### 5. **user_cohorts**
Cohort analysis for retention tracking
- Daily, weekly, monthly cohorts
- Retention curves
- LTV estimates and churn rates

#### 6. **alert_rules** & **alert_history**
Configurable alerting system
- Metric-based alert rules
- Multi-channel notifications (email, Slack, webhook)
- Alert history and acknowledgments

### Materialized Views

Pre-computed views for high-performance queries:

- **mv_active_users**: DAU/WAU/MAU calculations
- **mv_top_agents**: Agent leaderboards by runs and success rate
- **mv_workspace_summary**: Workspace-level metrics rollup
- **mv_error_trends**: Error pattern analysis
- **mv_agent_usage_trends**: Week-over-week growth tracking

**Refresh Schedule**: Daily (or call `analytics.refresh_all_materialized_views()`)

### Functions & Procedures

#### Analytics Functions

```sql
-- Refresh all materialized views
SELECT analytics.refresh_all_materialized_views();

-- Get workspace metrics for date range
SELECT * FROM analytics.get_workspace_metrics(
    'workspace-uuid'::UUID,
    '2025-10-01'::DATE,
    '2025-11-01'::DATE
);

-- Get agent insights
SELECT * FROM analytics.get_agent_insights('agent-uuid'::UUID, 30);

-- Calculate percentiles
SELECT analytics.calculate_percentiles(
    ARRAY[1.2, 2.3, 3.4, 4.5],
    ARRAY[0.5, 0.95, 0.99]
);
```

#### Aggregation Functions

```sql
-- Aggregate daily metrics
SELECT analytics.aggregate_daily_metrics('2025-11-08'::DATE);

-- Aggregate hourly metrics
SELECT analytics.aggregate_hourly_metrics(NOW() - INTERVAL '1 hour');
```

#### Maintenance Functions

```sql
-- Clean up old data per retention policy
SELECT * FROM analytics.cleanup_old_data();

-- Evaluate alert rules
SELECT * FROM analytics.evaluate_alert_rules();
```

## Maintenance Procedures

### Daily Tasks

```bash
# Aggregate yesterday's metrics
psql $DATABASE_URL -f database/procedures/aggregate_metrics.sql

# Refresh materialized views
psql $DATABASE_URL -f database/procedures/refresh_materialized_views.sql
```

### Weekly Tasks

```bash
# Clean up old data
psql $DATABASE_URL -f database/procedures/cleanup_old_data.sql
```

### Scheduled Jobs (Recommended)

Set up cron jobs or use pg_cron extension:

```sql
-- Daily at 1 AM: Aggregate metrics
SELECT cron.schedule('aggregate-daily-metrics', '0 1 * * *',
    'SELECT analytics.aggregate_daily_metrics(CURRENT_DATE - 1)');

-- Daily at 2 AM: Refresh materialized views
SELECT cron.schedule('refresh-mv', '0 2 * * *',
    'SELECT analytics.refresh_all_materialized_views()');

-- Weekly on Sunday at 3 AM: Cleanup old data
SELECT cron.schedule('cleanup-old-data', '0 3 * * 0',
    'SELECT analytics.cleanup_old_data()');

-- Hourly: Aggregate hourly metrics
SELECT cron.schedule('aggregate-hourly-metrics', '5 * * * *',
    'SELECT analytics.aggregate_hourly_metrics(DATE_TRUNC(''hour'', NOW() - INTERVAL ''1 hour''))');
```

## Row-Level Security (RLS)

All tables have RLS enabled for multi-tenant isolation:

- Users can only access data for workspaces they belong to
- `service_role` has full access for background jobs
- Users can insert their own activity data
- Alert acknowledgments are workspace-scoped

### Testing RLS

```sql
-- Set user context
SET LOCAL role authenticated;
SET LOCAL request.jwt.claim.sub = 'user-uuid';

-- Query will only return user's workspaces
SELECT * FROM analytics.daily_metrics;
```

## Performance Optimization

### Indexing Strategy

- **BRIN indexes** on time-series columns (created_at, metric_date)
- **GIN indexes** on JSONB columns (metadata, error_types)
- **Composite indexes** on common query patterns
- **Partial indexes** for frequently filtered conditions
- **Covering indexes** to avoid table lookups

### Query Performance

Target performance metrics:
- Indexed queries: < 100ms
- Materialized view queries: < 50ms
- Aggregation functions: < 5 seconds
- Materialized view refresh: < 30 seconds

### Monitoring

```sql
-- Check table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
    pg_size_pretty(pg_indexes_size(schemaname||'.'||tablename)) as index_size
FROM pg_tables
WHERE schemaname = 'analytics'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Check slow queries
SELECT
    query,
    calls,
    mean_exec_time,
    max_exec_time
FROM pg_stat_statements
WHERE query LIKE '%analytics.%'
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Check index usage
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'analytics'
ORDER BY idx_scan DESC;
```

## Data Retention Policy

| Table | Retention Period | Cleanup Method |
|-------|-----------------|----------------|
| user_activity | 90 days | Automatic via `cleanup_old_data()` |
| hourly_metrics | 30 days | Automatic via `cleanup_old_data()` |
| daily_metrics | Indefinite | Manual archive if needed |
| agent_performance | Indefinite | Manual archive if needed |
| alert_history | 180 days | Automatic via `cleanup_old_data()` |

## Backup & Recovery

### Backup Analytics Schema

```bash
# Backup schema structure
pg_dump $DATABASE_URL --schema=analytics --schema-only > analytics_schema.sql

# Backup schema data
pg_dump $DATABASE_URL --schema=analytics --data-only > analytics_data.sql

# Full backup
pg_dump $DATABASE_URL --schema=analytics > analytics_full.sql
```

### Restore

```bash
# Restore schema
psql $DATABASE_URL < analytics_schema.sql

# Restore data
psql $DATABASE_URL < analytics_data.sql
```

## Troubleshooting

### Materialized Views Not Refreshing

```sql
-- Check for locks
SELECT * FROM pg_locks WHERE relation = 'analytics.mv_active_users'::regclass;

-- Force refresh (non-concurrent)
REFRESH MATERIALIZED VIEW analytics.mv_active_users;
```

### Slow Queries

```sql
-- Analyze tables
ANALYZE analytics.user_activity;
ANALYZE analytics.daily_metrics;

-- Reindex if needed
REINDEX TABLE analytics.user_activity;
```

### RLS Issues

```sql
-- Check current user
SELECT current_user, auth.uid();

-- Check workspace access
SELECT * FROM analytics.get_user_workspaces();

-- Disable RLS temporarily for debugging (be careful!)
ALTER TABLE analytics.daily_metrics DISABLE ROW LEVEL SECURITY;
```

## Development

### Adding New Tables

1. Create migration file: `00X_add_new_table.sql`
2. Include table definition, indexes, comments
3. Add RLS policies if needed
4. Update this README

### Adding New Metrics

1. Update relevant table (e.g., `daily_metrics`)
2. Update aggregation functions
3. Update materialized views if needed
4. Add indexes for new columns
5. Update documentation

## Security Considerations

- ✅ Row-Level Security enabled on all tables
- ✅ Read-only access to public schema
- ✅ Service role for background jobs only
- ✅ Encrypted connections required (Supabase default)
- ✅ No sensitive PII stored (IP addresses hashed recommended)
- ✅ Audit logging via triggers

## Support

For issues or questions:
- Check migration logs
- Review PostgreSQL logs
- Consult Supabase dashboard
- Contact platform team

## License

Proprietary - Shadow Analytics Platform
