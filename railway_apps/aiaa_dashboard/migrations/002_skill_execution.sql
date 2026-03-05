-- AIAA Dashboard Schema v2.0
-- Skill execution, client profiles, and user settings tables

-- ==============================================================================
-- Skill Executions Table
-- Track every skill run with params, output, and status
-- ==============================================================================
CREATE TABLE IF NOT EXISTS skill_executions (
    id TEXT PRIMARY KEY,
    skill_name TEXT NOT NULL,
    params TEXT,
    status TEXT DEFAULT 'queued' CHECK(status IN ('queued', 'running', 'success', 'error', 'cancelled', 'timeout')),
    started_at TEXT,
    first_token_at TEXT,
    completed_at TEXT,
    queue_wait_ms INTEGER,
    first_token_ms INTEGER,
    total_runtime_ms INTEGER,
    duration_ms INTEGER,
    output_path TEXT,
    output_preview TEXT,
    error_message TEXT,
    cost_estimate REAL,
    telemetry TEXT,
    profile_used TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_skill_exec_name ON skill_executions(skill_name, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_skill_exec_status ON skill_executions(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_skill_exec_created ON skill_executions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_skill_exec_profile ON skill_executions(profile_used, created_at DESC);

-- ==============================================================================
-- Client Profiles Table
-- Store client business info for skill parameterization
-- ==============================================================================
CREATE TABLE IF NOT EXISTS client_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    industry TEXT,
    website TEXT,
    description TEXT,
    target_audience TEXT,
    goals TEXT,
    competitors TEXT,
    brand_voice TEXT,
    rules TEXT,
    preferences TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_client_slug ON client_profiles(slug);

-- ==============================================================================
-- User Settings Table
-- Key-value store for dashboard preferences and API keys
-- ==============================================================================
CREATE TABLE IF NOT EXISTS user_settings (
    setting_key TEXT PRIMARY KEY,
    setting_value TEXT NOT NULL,
    last_validated_at TEXT,
    validation_status TEXT,
    last_error TEXT,
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_user_settings_key ON user_settings(setting_key);

-- Record this migration
INSERT INTO migration_history (migration_name) VALUES ('002_skill_execution.sql');
