-- User settings for API keys, profile, and preferences
CREATE TABLE IF NOT EXISTS user_settings (
    setting_key TEXT PRIMARY KEY,
    setting_value TEXT,
    last_validated_at TIMESTAMP,
    validation_status TEXT,
    last_error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_settings_key ON user_settings(setting_key);
CREATE INDEX IF NOT EXISTS idx_user_settings_validation_status ON user_settings(validation_status);

INSERT INTO migration_history (migration_name) VALUES ('002_user_settings.sql');
