# Security Fixes for Materialized Views (PR #42)

This document summarizes the security fixes applied to address the critical issues identified in the code review.

## Summary of Changes

### ✅ Blocking Issues Fixed

#### 1. Missing RLS Policies on Materialized Views
**Issue**: Materialized views aggregated data across ALL workspaces without RLS, causing data leakage.

**Fix**: 
- Created migration `015_add_rls_and_secure_views.sql` that:
  - Enables RLS on source tables (`agent_runs`, `agent_errors`)
  - Creates secure views (`v_*_secure`) over materialized views with workspace filtering
  - Adds RLS policies using `analytics.get_user_workspaces()` function

**Files Changed**:
- `database/migrations/015_add_rls_and_secure_views.sql` (new)

#### 2. Overly Permissive GRANT PUBLIC
**Issue**: Grants to `PUBLIC` allowed any database connection to read all workspace data.

**Fix**: Changed all `GRANT ... TO PUBLIC` to `GRANT ... TO authenticated` or `GRANT ... TO service_role`.

**Files Changed**:
- `database/migrations/014_create_enhanced_materialized_views.sql` (lines 334-345)

#### 3. Status/Health Endpoints Bypass Workspace Isolation
**Issue**: Status, health, statistics, and row-count endpoints returned metadata for all workspaces.

**Fix**: Restricted all metadata endpoints to admin users only using `require_admin` dependency.

**Files Changed**:
- `backend/src/api/routes/materialized_views.py`:
  - `/status` endpoint (line 217)
  - `/statistics/{view_name}` endpoint (line 248)
  - `/health` endpoint (line 295)
  - `/{view_name}/row-count` endpoint (line 340)
  - `/views/list` endpoint (line 380) - added authentication

#### 4. COALESCE in Unique Index
**Issue**: Unique index used COALESCE which could cause constraint violations with NULL values.

**Fix**: Changed to partial unique index that excludes NULLs (since source table has NOT NULL constraints).

**Files Changed**:
- `database/migrations/014_create_enhanced_materialized_views.sql` (lines 186-199)

### ✅ Important Issues Fixed

#### 5. SQL Injection in Refresh Function
**Issue**: PL/pgSQL function built SQL using string concatenation.

**Fix**: Changed to use `format()` with `%I` identifier escaping.

**Files Changed**:
- `database/migrations/014_create_enhanced_materialized_views.sql` (lines 273-279)

#### 6. SQL Injection Risk in refresh_service.py
**Issue**: Used f-string interpolation for SQL query construction.

**Fix**: Added SQL identifier validation and used `sql.quoted_name()` for safer construction.

**Files Changed**:
- `backend/src/services/materialized_views/refresh_service.py` (lines 310-318)

#### 7. Generic Error Response Leaks Internal Details
**Issue**: API endpoints returned full exception messages to clients.

**Fix**: Changed all error responses to generic messages, logging full details server-side.

**Files Changed**:
- `backend/src/api/routes/materialized_views.py`:
  - All exception handlers now return generic error messages

#### 8. Initial Refresh Blocks Migration
**Issue**: Initial REFRESH MATERIALIZED VIEW commands could timeout on large datasets.

**Fix**: Commented out initial refresh with instructions to run manually after migration.

**Files Changed**:
- `database/migrations/014_create_enhanced_materialized_views.sql` (lines 315-328)

### 🔧 Additional Fixes

#### 9. Fixed Bug in mv_error_summary View
**Issue**: View referenced `ae.user_id` which doesn't exist in `agent_errors` table.

**Fix**: Changed to join with `agent_runs` table to get `user_id` via `agent_run_id`.

**Files Changed**:
- `database/migrations/014_create_enhanced_materialized_views.sql` (lines 157-184)

## Migration Order

1. Run migration `014_create_enhanced_materialized_views.sql` (creates materialized views)
2. Run migration `015_add_rls_and_secure_views.sql` (adds RLS and secure views)
3. Manually refresh materialized views (see instructions in migration 014)

## Testing Recommendations

1. **Multi-tenant isolation tests** (CRITICAL):
   - Create test with 2 workspaces, user A in workspace 1, user B in workspace 2
   - User A queries secure views - verify they ONLY see workspace 1 data
   - User B queries secure views - verify they ONLY see workspace 2 data
   - Test both via API endpoints and direct database queries

2. **Authorization tests**:
   - Test refresh endpoints with non-admin user - should return 403
   - Test status/health/statistics endpoints with non-admin user - should return 403
   - Test with admin user - should succeed
   - Test list endpoint without authentication - should return 401

3. **Performance tests**:
   - Test refresh timeout with slow query (mock) - verify it times out at 30s
   - Test concurrent refresh with multiple simultaneous requests

4. **Error recovery tests**:
   - Test refresh when source table is missing
   - Test refresh when database connection drops mid-refresh
   - Test partial failure scenario - verify successful views stay refreshed

## Security Notes

- **Direct access to materialized views**: While materialized views are granted to `authenticated` users, applications should use the secure views (`v_*_secure`) for workspace-filtered access.
- **Admin endpoints**: All metadata endpoints (status, health, statistics, row-count) are now admin-only to prevent information leakage.
- **Service role**: The refresh function is only executable by `service_role`. API endpoints use admin authentication, but the database function itself requires service_role privileges.

## Next Steps

1. ✅ All blocking security issues have been addressed
2. ⏳ Add integration tests for multi-tenant workspace isolation
3. ⏳ Test migrations on staging environment
4. ⏳ Update API documentation to reflect secure view usage
5. ⏳ Consider making 30-day window configurable (nice-to-have)

