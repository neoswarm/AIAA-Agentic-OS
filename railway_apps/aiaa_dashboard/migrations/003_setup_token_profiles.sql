-- ==============================================================================
-- Setup Token Profiles
-- Structured storage for setup-token profiles with encrypted token blobs.
-- ==============================================================================
CREATE TABLE IF NOT EXISTS setup_token_profiles (
    profile_id TEXT PRIMARY KEY,
    encrypted_token TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'inactive', 'revoked')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_setup_token_profiles_status
ON setup_token_profiles(status, updated_at DESC);

INSERT INTO migration_history (migration_name) VALUES ('003_setup_token_profiles.sql');
