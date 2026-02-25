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
    status TEXT DEFAULT 'queued' CHECK(status IN ('queued', 'running', 'success', 'error', 'cancelled')),
    started_at TEXT,
    completed_at TEXT,
    duration_ms INTEGER,
    output_path TEXT,
    output_preview TEXT,
    error_message TEXT,
    cost_estimate REAL,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_skill_exec_name ON skill_executions(skill_name, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_skill_exec_status ON skill_executions(status, created_at DESC);

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
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Record this migration
INSERT INTO migration_history (migration_name) VALUES ('002_skill_execution.sql');
