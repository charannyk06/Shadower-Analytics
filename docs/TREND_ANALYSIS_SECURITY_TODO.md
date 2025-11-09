# Trend Analysis Service - Security Hardening Action Plan

## Status: IN PROGRESS

This document outlines the remaining security fixes needed for the trend analysis service after addressing PR review feedback.

## ✅ Completed Fixes

### 1. API Layer Security (COMPLETE)
**File**: `backend/src/api/routes/metrics.py`

✅ **Rate Limiting**: Added dedicated rate limiter (2 req/min, 50 req/hour)
✅ **Request Timeout**: 30-second timeout protection with asyncio.timeout()
✅ **User ID Passing**: user_id now passed to service for cache scoping
✅ **Error Sanitization**: Error messages no longer expose workspace IDs or internal details
✅ **Structured Logging**: Added structured logging with user_id, ip, and error context
✅ **HTTP Status Codes**: Proper 400, 403, 429, 504 responses

### 2. Supporting Infrastructure (COMPLETE)
✅ **Constants**: `trend_analysis_constants.py` with all magic numbers extracted
✅ **Pydantic Models**: `models/trend_analysis.py` with 30+ type-safe models
✅ **Security Tests**: `test_trend_analysis_security.py` with 15+ test cases
✅ **Documentation**: `docs/SECURITY_FIXES.md` comprehensive security guide
✅ **React Query v5**: Frontend hooks updated to use `gcTime`
✅ **Rollback Script**: Database migration rollback provided

## 🔴 Critical Remaining Fixes

### 3. Service Layer Security (IN PROGRESS)
**File**: `backend/src/services/analytics/trend_analysis_service.py`

The original service file (1120 lines) still contains SQL injection vulnerabilities and needs comprehensive security hardening.

#### Required Changes:

**A. SQL Injection Prevention** (HIGH PRIORITY)
- [ ] Replace `_build_time_series_query()` with parameterized version
- [ ] Update all metric queries to use `:parameter` syntax
- [ ] Change `_get_time_series()` to use bind parameters
- [ ] Test with SQL injection payloads

**Current vulnerable code** (lines 158-212):
```python
f"WHERE workspace_id = '{workspace_id}'"  # ❌ SQL Injection
```

**Required fix**:
```python
WHERE workspace_id = :workspace_id"  # ✅ Parameterized
params = {"workspace_id": workspace_id, "start_date": start_date}
result = await self.db.execute(text(query), params)
```

**B. Input Validation** (HIGH PRIORITY)
- [ ] Add `_validate_inputs()` method
- [ ] Validate workspace_id format (UUID check)
- [ ] Whitelist metrics against `ALLOWED_METRICS`
- [ ] Whitelist timeframes against `ALLOWED_TIMEFRAMES`
- [ ] Raise ValueError with safe messages

**C. Workspace Access Validation** (HIGH PRIORITY)
- [ ] Add `_validate_workspace_access()` method
- [ ] Query `workspace_members` table with parameterized query
- [ ] Raise PermissionError if unauthorized
- [ ] Log unauthorized attempts

**D. Magic Numbers Replacement** (MEDIUM PRIORITY)
- [ ] Replace `< 14` with `MIN_DATA_POINTS_FOR_ANALYSIS`
- [ ] Replace `0.3` with `SEASONALITY_ACF_THRESHOLD`
- [ ] Replace `2.0` with `ANOMALY_THRESHOLD_STD_DEVS`
- [ ] Replace `50` with `VOLATILITY_THRESHOLD`
- [ ] Replace `0.1` with `STABLE_TREND_THRESHOLD`
- [ ] Import from `trend_analysis_constants`

**E. Async Optimization** (MEDIUM PRIORITY)
- [ ] Wrap `_calculate_overview()` in `asyncio.to_thread()`
- [ ] Wrap `_perform_decomposition()` in `asyncio.to_thread()`
- [ ] Wrap `_detect_patterns()` in `asyncio.to_thread()`
- [ ] Wrap `_generate_comparisons()` in `asyncio.to_thread()`
- [ ] Wrap `_generate_forecast()` in `asyncio.to_thread()`

**F. Cache Validation** (MEDIUM PRIORITY)
- [ ] Add Pydantic validation in `_get_cached_analysis()`
- [ ] Catch `ValidationError` and re-compute if invalid
- [ ] Update `_cache_analysis()` to accept `user_id`
- [ ] Include `user_id` in cache queries for isolation

**G. User ID Integration** (MEDIUM PRIORITY)
- [ ] Update `analyze_trend()` signature to accept `user_id: Optional[str]`
- [ ] Pass `user_id` to `_validate_workspace_access()`
- [ ] Pass `user_id` to cache methods
- [ ] Update all method signatures

## 📋 Detailed Implementation Plan

### Phase 1: Critical Security Fixes (Est: 2-3 hours)

1. **Create secure query builder**:
```python
def _build_time_series_query_secure(
    self,
    metric: str,
    workspace_id: str,
    start_date: datetime
) -> Tuple[str, Dict[str, Any]]:
    """Build parameterized SQL query (SQL injection safe)."""
    params = {
        "workspace_id": workspace_id,
        "start_date": start_date
    }

    metric_queries = {
        "executions": """
            SELECT
                DATE_TRUNC('day', created_at) as timestamp,
                COUNT(*) as value
            FROM analytics.agent_executions
            WHERE workspace_id = :workspace_id
                AND created_at >= :start_date
            GROUP BY DATE_TRUNC('day', created_at)
            ORDER BY timestamp
        """,
        # ... other metrics
    }

    return metric_queries[metric], params
```

2. **Add input validation**:
```python
def _validate_inputs(
    self,
    workspace_id: str,
    metric: str,
    timeframe: str
) -> None:
    """Validate all inputs against whitelists."""
    if not workspace_id or len(workspace_id) < 10:
        raise ValueError("Invalid workspace_id format")

    if metric not in ALLOWED_METRICS:
        raise ValueError(
            f"Invalid metric. Allowed: {', '.join(ALLOWED_METRICS)}"
        )

    if timeframe not in ALLOWED_TIMEFRAMES:
        raise ValueError(
            f"Invalid timeframe. Allowed: {', '.join(ALLOWED_TIMEFRAMES)}"
        )
```

3. **Add workspace access validation**:
```python
async def _validate_workspace_access(
    self,
    workspace_id: str,
    user_id: Optional[str]
) -> None:
    """Validate user has workspace access."""
    if not user_id:
        return  # API layer handles it

    query = text("""
        SELECT EXISTS(
            SELECT 1
            FROM public.workspace_members
            WHERE workspace_id = :workspace_id
            AND user_id = :user_id
        )
    """)

    result = await self.db.execute(
        query,
        {"workspace_id": workspace_id, "user_id": user_id}
    )

    if not result.scalar():
        raise PermissionError("Unauthorized access to workspace")
```

### Phase 2: Performance & Quality (Est: 1-2 hours)

4. **Replace magic numbers**:
   - Find/replace all hardcoded values
   - Import constants at top of file
   - Update all comparisons

5. **Optimize async operations**:
   - Wrap CPU-bound methods in `asyncio.to_thread()`
   - Update `asyncio.gather()` calls

6. **Add cache validation**:
   - Import `ValidationError` from Pydantic
   - Add try/except in cache retrieval
   - Validate with `TrendAnalysisResponse(**cached_result)`

### Phase 3: Integration & Testing (Est: 1-2 hours)

7. **Add integration tests**:
   - Test full API → Service → Database flow
   - Test caching behavior
   - Test validation and access control
   - Test error handling

8. **Performance testing**:
   - Test with production data volumes
   - Measure Prophet performance
   - Verify timeout works correctly

## 🔧 Quick Reference: Line-by-Line Changes

**Line 16**: Add imports
```python
from pydantic import ValidationError
from .trend_analysis_constants import *
```

**Line 32-37**: Update method signature
```python
async def analyze_trend(
    self,
    workspace_id: str,
    metric: str,
    timeframe: str,
    user_id: Optional[str] = None  # ADD THIS
) -> Dict[str, Any]:
```

**Line 48**: Add validation
```python
# ADD THESE LINES
self._validate_inputs(workspace_id, metric, timeframe)
await self._validate_workspace_access(workspace_id, user_id)
```

**Line 57**: Replace magic number
```python
if not time_series_data or len(time_series_data) < MIN_DATA_POINTS_FOR_ANALYSIS:
```

**Lines 67-74**: Use asyncio.to_thread()
```python
results = await asyncio.gather(
    asyncio.to_thread(self._calculate_overview, df, metric),
    asyncio.to_thread(self._perform_decomposition, df),
    # ... etc
)
```

**Lines 150-212**: Replace entire method
```python
def _build_time_series_query_secure(self, metric, workspace_id, start_date):
    # Use parameterized version from secure service template
```

**Line 252**: Replace magic number
```python
if abs(slope) < (std_y * STABLE_TREND_THRESHOLD):
```

**Line 257**: Replace magic number
```python
if volatility > VOLATILITY_THRESHOLD:
```

## 📊 Testing Checklist

After implementing fixes, verify:

- [ ] SQL injection tests pass
- [ ] Input validation rejects invalid inputs
- [ ] Workspace access control works
- [ ] Cache scoping includes user_id
- [ ] Timeout protection triggers at 30s
- [ ] Rate limiting blocks excess requests
- [ ] Error messages don't expose internals
- [ ] Prophet forecasting completes successfully
- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] Performance is acceptable

## 🚀 Deployment Steps

1. Apply all service layer fixes
2. Run full test suite
3. Test in staging environment
4. Monitor for errors and performance
5. Deploy to production
6. Monitor cache hit rates and latencies
7. Set up alerts for rate limiting violations

## 📞 Support

If you encounter issues during implementation:
- Review `docs/SECURITY_FIXES.md` for detailed context
- Check security tests for examples
- Refer to the Pydantic models for type signatures
- See constants file for all threshold values

## ⏱️ Estimated Time

- Critical fixes: 2-3 hours
- Quality improvements: 1-2 hours
- Testing & validation: 1-2 hours
- **Total: 4-7 hours**

## Status: Ready for Implementation

All supporting infrastructure is in place. The service file is ready to be updated with the security fixes outlined above.
