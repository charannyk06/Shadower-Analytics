# Test Migrations

This directory contains database migrations that are **ONLY for test/dev environments** and should **NEVER** be run in production.

## ⚠️ WARNING

**DO NOT** include these migrations in production deployment scripts or CI/CD pipelines that target production databases.

## Files

- `015_create_test_auth_functions.sql` - Creates test helper functions `auth.uid()` and `auth.role()` for testing RLS policies. These functions are provided by Supabase in production and should not be overridden.

## Usage

These migrations should be run manually in test/dev environments only:

```bash
# Test environment only
psql $TEST_DATABASE_URL -f database/test_migrations/015_create_test_auth_functions.sql
```

## Setup for Tests

For pytest fixtures, load these migrations in your test setup:

```python
# backend/tests/conftest.py
@pytest.fixture(scope="session")
async def setup_test_db():
    # Load test migrations
    async with aiopg.connect(TEST_DATABASE_URL) as conn:
        with open("database/test_migrations/015_create_test_auth_functions.sql") as f:
            await conn.execute(f.read())
```

