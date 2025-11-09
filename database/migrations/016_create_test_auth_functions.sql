-- =====================================================================
-- Migration: 016_create_test_auth_functions.sql
-- Description: Create test helper functions for auth.uid() and auth.role()
-- Created: 2025-11-09
-- 
-- WARNING: TEST ENVIRONMENT ONLY
-- This migration should ONLY run in test/dev environments
-- DO NOT run in production - Supabase provides these functions
-- 
-- For testing RLS policies, we need these functions to simulate user context.
-- =====================================================================

SET search_path TO analytics, public;

-- =====================================================================
-- Environment Guard: Prevent execution in Supabase/production
-- =====================================================================

DO $$
BEGIN
    -- Check if we're in Supabase/production environment
    -- Supabase has a special role 'supabase_admin' that indicates production
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'supabase_admin') THEN
        RAISE EXCEPTION 
            'This migration should not run in Supabase/production environments. '
            'Supabase provides auth.uid() and auth.role() functions automatically. '
            'This migration is for test/dev environments only.';
    END IF;
END $$;

-- =====================================================================
-- Create auth schema if it doesn't exist (for testing)
-- =====================================================================

CREATE SCHEMA IF NOT EXISTS auth;

-- =====================================================================
-- Function: auth.uid()
-- Description: Returns the current user's UUID from JWT claim
-- For testing: Reads from GUC variable "request.jwt.claim.sub"
-- =====================================================================

CREATE OR REPLACE FUNCTION auth.uid()
RETURNS UUID
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    user_id_text TEXT;
BEGIN
    -- Try to get user ID from JWT claim (Supabase pattern)
    user_id_text := current_setting('request.jwt.claim.sub', true);
    
    -- If not set, return NULL (no user context)
    IF user_id_text IS NULL OR user_id_text = '' THEN
        RETURN NULL;
    END IF;
    
    -- Convert to UUID
    RETURN user_id_text::UUID;
EXCEPTION
    WHEN OTHERS THEN
        -- If conversion fails, return NULL
        RETURN NULL;
END;
$$;

COMMENT ON FUNCTION auth.uid() IS 
    'Returns the current user UUID from JWT claim. '
    'For testing: Set via SET LOCAL "request.jwt.claim.sub" = ''user-uuid''';

-- =====================================================================
-- Function: auth.role()
-- Description: Returns the current user's role
-- For testing: Reads from GUC variable "request.jwt.claim.role"
-- =====================================================================

CREATE OR REPLACE FUNCTION auth.role()
RETURNS TEXT
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    role_text TEXT;
BEGIN
    -- Try to get role from JWT claim (Supabase pattern)
    role_text := current_setting('request.jwt.claim.role', true);
    
    -- If not set, default to 'authenticated'
    IF role_text IS NULL OR role_text = '' THEN
        -- Check if we're in a service role context
        IF current_setting('request.jwt.claim.role', true) IS NULL THEN
            -- Check PostgreSQL role
            IF current_user = 'service_role' OR current_user = 'postgres' THEN
                RETURN 'service_role';
            END IF;
        END IF;
        RETURN 'authenticated';
    END IF;
    
    RETURN role_text;
EXCEPTION
    WHEN OTHERS THEN
        -- Default to authenticated
        RETURN 'authenticated';
END;
$$;

COMMENT ON FUNCTION auth.role() IS 
    'Returns the current user role from JWT claim. '
    'For testing: Set via SET LOCAL "request.jwt.claim.role" = ''role-name''';

-- =====================================================================
-- Grants
-- =====================================================================

-- Grant execute to authenticated and service_role
GRANT EXECUTE ON FUNCTION auth.uid() TO authenticated;
GRANT EXECUTE ON FUNCTION auth.uid() TO service_role;
GRANT EXECUTE ON FUNCTION auth.role() TO authenticated;
GRANT EXECUTE ON FUNCTION auth.role() TO service_role;

-- =====================================================================
-- Migration Complete
-- =====================================================================

