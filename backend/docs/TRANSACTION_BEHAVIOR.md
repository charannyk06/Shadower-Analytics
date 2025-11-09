# Transaction Behavior in Aggregation Jobs

## Overview

Aggregation jobs use a specific transaction pattern that developers should understand for error handling and debugging.

## Individual Function Commits

Each aggregation function commits independently:

- `aggregate_execution_metrics()` - commits after aggregating execution data
- `aggregate_user_activity()` - commits after aggregating user activity
- `aggregate_credit_consumption()` - commits after aggregating credit data
- `aggregate_daily_metrics()` - commits after aggregating daily rollups

## Partial Rollup Behavior

When a rollup function (e.g., `hourly_rollup()`) executes, it calls multiple aggregation functions. If one fails:

1. **Previously completed aggregations are committed** - their data is saved
2. **Failed aggregation rolls back** - its changes are discarded
3. **Remaining aggregations may not execute** - depends on error handling

### Example Scenario

```python
async def hourly_rollup(db, target_hour):
    # These each commit independently:
    exec_count = await aggregate_execution_metrics(db, start, end)  # ✓ Commits
    user_count = await aggregate_user_activity(db, start, end)       # ✗ Fails & rolls back
    credit_count = await aggregate_credit_consumption(db, start, end) # May not execute
```

Result: Execution metrics are saved, user activity is not, credits may or may not be.

## Why This Design?

1. **Partial Progress**: Saves work done before failures
2. **Idempotency**: ON CONFLICT DO UPDATE allows safe retries
3. **Isolation**: One aggregation failure doesn't lose all work
4. **Debugging**: Can identify which specific aggregation failed

## Idempotent Operations

All aggregation inserts use `ON CONFLICT DO UPDATE`:

```sql
INSERT INTO analytics.execution_metrics_hourly (...)
VALUES (...)
ON CONFLICT (workspace_id, hour)
DO UPDATE SET
    total_executions = EXCLUDED.total_executions,
    ...
```

This means:
- **First run**: Inserts new data
- **Retry**: Updates existing data with new values
- **Safe to retry**: Won't create duplicates or fail

## Error Recovery

### Celery Automatic Retry

Tasks are configured with automatic retry:

```python
@celery_app.task(
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
)
```

### Manual Recovery

If automatic retries fail:

1. **Check logs** to identify failed aggregation
2. **Verify partial data** was committed
3. **Manually trigger** the failed task with same parameters
4. **Idempotency** ensures safe re-execution

### Monitoring

Use Flower UI to:
- View task status
- Inspect error messages
- Retry failed tasks
- Monitor execution history

## Best Practices

### For Developers

1. **Always check logs** after task failures
2. **Understand idempotency** - retries update, don't duplicate
3. **Test failure scenarios** in development
4. **Monitor partial completions** in production

### For Operators

1. **Set up alerts** for task failures
2. **Regular log review** for partial failures
3. **Retry failed tasks** via Flower or CLI
4. **Verify data consistency** after recoveries

## Transaction Rollback Limitations

The `rollback()` in `hourly_rollup()` exception handler has limited effect:

```python
except Exception as e:
    logger.error(f"Hourly rollup failed: {str(e)}")
    await db.rollback()  # Only affects uncommitted work
    raise
```

This rollback only affects:
- Changes not yet committed
- The current function's transaction

It does NOT rollback:
- Previously committed aggregation functions
- Other database sessions
- Changes in separate transactions

## Alternative Approaches

If full transaction atomicity is required, consider:

1. **Single transaction per rollup**:
   - Combine all aggregations in one commit
   - All-or-nothing behavior
   - Risk: One failure loses all work

2. **Two-phase commit**:
   - Prepare all aggregations
   - Commit all or rollback all
   - Complex to implement

3. **Compensation transactions**:
   - Save rollback data
   - Undo committed changes on failure
   - Requires additional infrastructure

Current design prioritizes simplicity and partial progress over strict atomicity.

## Summary

- **Partial commits are expected behavior**
- **Idempotency enables safe retries**
- **Monitor logs for failures**
- **Use Flower for manual recovery**
- **Current design favors progress over atomicity**

For questions or issues, consult the main [AGGREGATION_JOBS.md](AGGREGATION_JOBS.md) documentation.
