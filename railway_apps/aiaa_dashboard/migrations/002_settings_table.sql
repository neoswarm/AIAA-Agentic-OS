-- Add settings table for app preferences and secure token storage.
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_settings_key ON settings(key);

INSERT INTO migration_history (migration_name) VALUES ('002_settings_table.sql');
