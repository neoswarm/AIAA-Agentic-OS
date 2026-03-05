-- ==============================================================================
-- User Settings Table
-- Persistent key/value settings used by Settings UI and API v2 endpoints
-- ==============================================================================
CREATE TABLE IF NOT EXISTS user_settings (
    setting_key TEXT PRIMARY KEY,
    setting_value TEXT NOT NULL,
    last_validated_at TEXT,
    validation_status TEXT,
    last_error TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_settings_key ON user_settings(setting_key);

INSERT INTO migration_history (migration_name) VALUES ('002_user_settings.sql');
