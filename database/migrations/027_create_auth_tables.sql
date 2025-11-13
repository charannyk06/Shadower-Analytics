-- Authentication and Authorization Tables Migration
-- This migration creates tables for API keys, user sessions, and refresh tokens

-- API Keys table for programmatic access
CREATE TABLE IF NOT EXISTS api_keys (
    id VARCHAR(255) PRIMARY KEY,
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    workspace_id VARCHAR(255) NOT NULL,

    -- Permissions and access control
    permissions JSONB DEFAULT '[]'::jsonb NOT NULL,
    rate_limit INTEGER DEFAULT 1000,

    -- Status and metadata
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    last_used TIMESTAMP,
    usage_count INTEGER DEFAULT 0,

    -- Expiration
    expires_at TIMESTAMP,

    -- Audit fields
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP,
    revoked_by VARCHAR(255)
);

-- API Keys indexes
CREATE INDEX idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX idx_api_keys_workspace ON api_keys(workspace_id);
CREATE INDEX idx_api_keys_user ON api_keys(user_id);
CREATE INDEX idx_api_keys_active ON api_keys(is_active);
CREATE INDEX idx_api_keys_created_at ON api_keys(created_at);
CREATE INDEX idx_api_keys_last_used ON api_keys(last_used);
CREATE INDEX idx_api_keys_expires_at ON api_keys(expires_at);

-- User Sessions table for tracking active login sessions
CREATE TABLE IF NOT EXISTS user_sessions (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,

    -- Session token (hashed)
    session_token_hash VARCHAR(255) UNIQUE NOT NULL,

    -- Device and location information
    device_info VARCHAR(255),
    ip_address VARCHAR(45), -- IPv6 compatible
    user_agent VARCHAR(500),

    -- Geolocation
    country_code VARCHAR(2),
    city VARCHAR(100),
    location VARCHAR(255), -- Combined location string

    -- Session status
    is_active BOOLEAN DEFAULT TRUE NOT NULL,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    terminated_at TIMESTAMP
);

-- User Sessions indexes
CREATE INDEX idx_user_sessions_session_token_hash ON user_sessions(session_token_hash);
CREATE INDEX idx_user_sessions_user ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_active ON user_sessions(is_active);
CREATE INDEX idx_user_sessions_user_active ON user_sessions(user_id, is_active);
CREATE INDEX idx_user_sessions_created_at ON user_sessions(created_at);
CREATE INDEX idx_user_sessions_last_active ON user_sessions(last_active);
CREATE INDEX idx_user_sessions_expires_at ON user_sessions(expires_at);

-- Refresh Tokens table for token renewal
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,

    -- Token (hashed)
    token_hash VARCHAR(255) UNIQUE NOT NULL,

    -- Associated access token (for revocation)
    access_token_jti VARCHAR(255),

    -- Status
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    is_revoked BOOLEAN DEFAULT FALSE NOT NULL,

    -- Device tracking
    device_info VARCHAR(255),
    ip_address VARCHAR(45),

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    revoked_at TIMESTAMP,
    last_used TIMESTAMP
);

-- Refresh Tokens indexes
CREATE INDEX idx_refresh_tokens_token_hash ON refresh_tokens(token_hash);
CREATE INDEX idx_refresh_tokens_user ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_active ON refresh_tokens(is_active);
CREATE INDEX idx_refresh_tokens_access_token_jti ON refresh_tokens(access_token_jti);
CREATE INDEX idx_refresh_tokens_created_at ON refresh_tokens(created_at);
CREATE INDEX idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);

-- Add comments for documentation
COMMENT ON TABLE api_keys IS 'API keys for programmatic access to the analytics API';
COMMENT ON TABLE user_sessions IS 'Active user sessions for session management';
COMMENT ON TABLE refresh_tokens IS 'Refresh tokens for token renewal without re-authentication';

COMMENT ON COLUMN api_keys.key_hash IS 'SHA-256 hash of the API key';
COMMENT ON COLUMN api_keys.permissions IS 'JSON array of permission strings';
COMMENT ON COLUMN api_keys.rate_limit IS 'Maximum requests per hour';

COMMENT ON COLUMN user_sessions.session_token_hash IS 'SHA-256 hash of the session token';
COMMENT ON COLUMN user_sessions.ip_address IS 'IPv4 or IPv6 address';

COMMENT ON COLUMN refresh_tokens.token_hash IS 'SHA-256 hash of the refresh token';
COMMENT ON COLUMN refresh_tokens.access_token_jti IS 'JWT ID of associated access token for revocation tracking';

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_api_keys_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for api_keys updated_at
CREATE TRIGGER api_keys_updated_at_trigger
    BEFORE UPDATE ON api_keys
    FOR EACH ROW
    EXECUTE FUNCTION update_api_keys_updated_at();

-- Create function to automatically update last_active for sessions
CREATE OR REPLACE FUNCTION update_session_last_active()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_active = TRUE AND OLD.is_active = TRUE THEN
        NEW.last_active = CURRENT_TIMESTAMP;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for user_sessions last_active
CREATE TRIGGER user_sessions_last_active_trigger
    BEFORE UPDATE ON user_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_session_last_active();

-- Grant permissions (adjust schema/roles as needed)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON api_keys TO analytics_service;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON user_sessions TO analytics_service;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON refresh_tokens TO analytics_service;
