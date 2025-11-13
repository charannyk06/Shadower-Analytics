-- Rollback Authentication and Authorization Tables Migration
-- This script safely removes auth-related tables and their dependencies

-- Drop triggers first
DROP TRIGGER IF EXISTS api_keys_updated_at_trigger ON api_keys;
DROP TRIGGER IF EXISTS user_sessions_last_active_trigger ON user_sessions;

-- Drop functions
DROP FUNCTION IF EXISTS update_api_keys_updated_at();
DROP FUNCTION IF EXISTS update_session_last_active();

-- Drop tables (in reverse order of creation)
DROP TABLE IF EXISTS refresh_tokens;
DROP TABLE IF EXISTS user_sessions;
DROP TABLE IF EXISTS api_keys;

-- Note: This rollback script should only be used if you need to completely
-- remove the authentication tables. Make sure to backup any important data first.
