-- Initialize PostgreSQL for Shadow Analytics

-- Create database if not exists (run as postgres user)
SELECT 'CREATE DATABASE shadower_analytics'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'shadower_analytics')\gexec

-- Connect to the database
\c shadower_analytics

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create analytics schema
CREATE SCHEMA IF NOT EXISTS analytics;

-- Grant privileges
GRANT ALL PRIVILEGES ON SCHEMA analytics TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA analytics TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA analytics TO postgres;
