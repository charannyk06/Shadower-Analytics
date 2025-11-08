-- =====================================================================
-- Migration: 001_create_analytics_schema.sql
-- Description: Create analytics schema and set up permissions
-- Created: 2025-11-08
-- =====================================================================

-- Create analytics schema
CREATE SCHEMA IF NOT EXISTS analytics;

-- Set search path to include both analytics and public schemas
SET search_path TO analytics, public;

-- Enable necessary extensions (if not already enabled)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Grant schema usage permissions
GRANT USAGE ON SCHEMA analytics TO authenticated;
GRANT CREATE ON SCHEMA analytics TO service_role;

-- Grant read-only access to public schema for analytics queries
GRANT SELECT ON ALL TABLES IN SCHEMA public TO service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO service_role;

-- Create comment for documentation
COMMENT ON SCHEMA analytics IS 'Analytics schema for Shadow Analytics system - contains metrics, aggregations, and analytical data separate from the main application schema';
