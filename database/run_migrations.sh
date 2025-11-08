#!/bin/bash

# =====================================================================
# Script: run_migrations.sh
# Description: Run all analytics database migrations in order
# Usage: ./database/run_migrations.sh [database_url]
# =====================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Database connection (use environment variable or argument)
DB_URL="${1:-${DATABASE_URL:-postgres://localhost/shadower_analytics}}"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Shadow Analytics - Database Migration${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Function to run a migration file
run_migration() {
    local file=$1
    local filename=$(basename "$file")

    echo -e "${YELLOW}Running migration: $filename${NC}"

    if psql "$DB_URL" -f "$file" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ $filename completed successfully${NC}"
        return 0
    else
        echo -e "${RED}✗ $filename failed${NC}"
        return 1
    fi
}

# Run migrations in order
MIGRATION_DIR="$(dirname "$0")/migrations"

echo "Migration directory: $MIGRATION_DIR"
echo ""

# Check if migration directory exists
if [ ! -d "$MIGRATION_DIR" ]; then
    echo -e "${RED}Error: Migration directory not found: $MIGRATION_DIR${NC}"
    exit 1
fi

# Run each migration in order
MIGRATIONS=(
    "001_create_analytics_schema.sql"
    "002_create_core_tables.sql"
    "003_create_specialized_tables.sql"
    "004_create_materialized_views.sql"
    "005_create_functions.sql"
    "006_create_triggers.sql"
    "007_create_rls_policies.sql"
    "008_create_performance_indexes.sql"
)

FAILED=0

for migration in "${MIGRATIONS[@]}"; do
    migration_file="$MIGRATION_DIR/$migration"

    if [ ! -f "$migration_file" ]; then
        echo -e "${RED}Error: Migration file not found: $migration${NC}"
        FAILED=1
        break
    fi

    if ! run_migration "$migration_file"; then
        FAILED=1
        break
    fi

    echo ""
done

echo -e "${GREEN}========================================${NC}"

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All migrations completed successfully!${NC}"
    echo ""

    # Show schema information
    echo -e "${YELLOW}Analytics Schema Summary:${NC}"
    psql "$DB_URL" -c "
        SELECT
            schemaname,
            tablename,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
        FROM pg_tables
        WHERE schemaname = 'analytics'
        ORDER BY tablename;
    "

    echo ""
    echo -e "${YELLOW}Materialized Views:${NC}"
    psql "$DB_URL" -c "
        SELECT
            schemaname,
            matviewname,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||matviewname)) as size
        FROM pg_matviews
        WHERE schemaname = 'analytics'
        ORDER BY matviewname;
    "

    exit 0
else
    echo -e "${RED}Migration failed. Please check the errors above.${NC}"
    exit 1
fi
