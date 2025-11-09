# Database Index Requirements

This document outlines the required database indexes for optimal performance of the Shadower Analytics platform.

## Cohort Analysis Service

The cohort analysis feature relies heavily on the following indexes for optimal performance (<3 second target):

### Required Indexes

#### 1. UserActivity Table (analytics schema)

```sql
-- Composite index for workspace + created_at queries
CREATE INDEX IF NOT EXISTS idx_user_activity_workspace_created
ON analytics.user_activity (workspace_id, created_at);

-- Composite index for user + workspace queries
CREATE INDEX IF NOT EXISTS idx_user_activity_user_workspace
ON analytics.user_activity (user_id, workspace_id);

-- Composite index for workspace + user + created_at (cohort retention queries)
CREATE INDEX IF NOT EXISTS idx_user_activity_workspace_user_created
ON analytics.user_activity (workspace_id, user_id, created_at);

-- Index for session-based queries
CREATE INDEX IF NOT EXISTS idx_user_activity_session_created
ON analytics.user_activity (session_id, created_at);

-- Index for event type filtering
CREATE INDEX IF NOT EXISTS idx_user_activity_workspace_event_type
ON analytics.user_activity (workspace_id, event_type);

-- Index for device type segmentation
CREATE INDEX IF NOT EXISTS idx_user_activity_workspace_device
ON analytics.user_activity (workspace_id, device_type)
WHERE device_type IS NOT NULL;
```

#### 2. ExecutionLog Table

```sql
-- Composite index for workspace + user (LTV calculations)
CREATE INDEX IF NOT EXISTS idx_execution_log_workspace_user
ON public.execution_logs (workspace_id, user_id);

-- Index for credits_used aggregations
CREATE INDEX IF NOT EXISTS idx_execution_log_workspace_credits
ON public.execution_logs (workspace_id, credits_used);

-- Composite index for user revenue queries
CREATE INDEX IF NOT EXISTS idx_execution_log_user_credits
ON public.execution_logs (user_id, credits_used);
```

## Index Verification

To verify indexes are in place, run:

```sql
-- Check UserActivity indexes
SELECT
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'analytics'
  AND tablename = 'user_activity'
ORDER BY indexname;

-- Check ExecutionLog indexes
SELECT
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename = 'execution_logs'
ORDER BY indexname;
```

## Performance Targets

With these indexes in place, the following performance targets should be met:

| Operation | Target | Notes |
|-----------|--------|-------|
| Cohort calculation | <3 seconds | For 90-day date range |
| Retention matrix | <2 seconds | Single cohort, all periods |
| LTV calculation | <1 second | Per cohort |
| Segment retention | <1 second | Per cohort |

## Index Maintenance

### Monitoring Index Usage

```sql
-- Check index usage statistics
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname IN ('analytics', 'public')
  AND tablename IN ('user_activity', 'execution_logs')
ORDER BY idx_scan DESC;
```

### Identifying Missing Indexes

```sql
-- Find tables that might benefit from indexes (table scans)
SELECT
    schemaname,
    tablename,
    seq_scan,
    seq_tup_read,
    idx_scan,
    seq_tup_read / seq_scan AS avg_seq_read
FROM pg_stat_user_tables
WHERE schemaname IN ('analytics', 'public')
  AND seq_scan > 0
ORDER BY seq_tup_read DESC;
```

## Notes

1. **Partial Indexes**: The `device_type` index uses a partial filter (`WHERE device_type IS NOT NULL`) to reduce index size and improve performance.

2. **Covering Indexes**: Consider adding covering indexes for frequently queried columns to enable index-only scans.

3. **Index Bloat**: Monitor index bloat and rebuild indexes periodically:
   ```sql
   REINDEX INDEX CONCURRENTLY idx_user_activity_workspace_created;
   ```

4. **Analyze Statistics**: Keep statistics up-to-date:
   ```sql
   ANALYZE analytics.user_activity;
   ANALYZE public.execution_logs;
   ```

## Migration

These indexes should be created as part of database migrations. See migration files:
- `database/migrations/XXX_add_cohort_analysis_indexes.sql`

## Performance Testing

After creating indexes, verify performance with:

```sql
-- Test cohort query performance
EXPLAIN ANALYZE
SELECT
    DATE_TRUNC('month', created_at) as cohort_date,
    COUNT(DISTINCT user_id) as cohort_size
FROM analytics.user_activity
WHERE workspace_id = 'test-workspace'
  AND created_at >= CURRENT_DATE - INTERVAL '180 days'
GROUP BY DATE_TRUNC('month', created_at);
```

Expected: Index Scan instead of Seq Scan, execution time <100ms.
