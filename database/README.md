# Database Schema

This directory contains SQL migrations, seeds, and procedures for the Shadow Analytics database.

## Structure

- `migrations/`: Database migrations in numbered order
- `seeds/`: Sample data for development and testing
- `procedures/`: Stored procedures and functions

## Running Migrations

```bash
# Apply all migrations
psql -h localhost -U postgres -d shadower_analytics -f migrations/001_create_analytics_schema.sql

# Or use the backend's Alembic
cd backend
alembic upgrade head
```

## Seeding Data

```bash
# Development data
psql -h localhost -U postgres -d shadower_analytics -f seeds/development/sample_data.sql

# Test data
psql -h localhost -U postgres -d shadower_analytics_test -f seeds/test/test_data.sql
```
