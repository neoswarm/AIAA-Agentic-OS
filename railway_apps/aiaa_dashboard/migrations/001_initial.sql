-- AIAA Dashboard SQLite Schema v1.0
-- Initial schema with full workflow, execution, webhook, and event tracking

-- ==============================================================================
-- Workflows Table
-- Replaces workflow_config.json with persistent storage
-- ==============================================================================
CREATE TABLE IF NOT EXISTS workflows (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    type TEXT NOT NULL CHECK(type IN ('cron', 'webhook', 'web')),
    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'paused', 'error', 'deleted')),
    cron_schedule TEXT,
    webhook_slug TEXT UNIQUE,
    forward_url TEXT,
    slack_notify INTEGER DEFAULT 0,
    project_id TEXT,
    service_id TEXT,
    config JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_workflows_type ON workflows(type, status);
CREATE INDEX IF NOT EXISTS idx_workflows_service ON workflows(service_id);
CREATE INDEX IF NOT EXISTS idx_workflows_webhook ON workflows(webhook_slug) WHERE webhook_slug IS NOT NULL;

-- ==============================================================================
-- Executions Table
-- Track every workflow run with metrics and outcomes
-- ==============================================================================
CREATE TABLE IF NOT EXISTS executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_id TEXT,
    workflow_name TEXT NOT NULL,
    trigger_type TEXT NOT NULL CHECK(trigger_type IN ('cron', 'manual', 'webhook', 'api')),
    status TEXT DEFAULT 'running' CHECK(status IN ('running', 'success', 'error', 'timeout')),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    duration_ms INTEGER,
    error_message TEXT,
    output_summary TEXT,
    metadata JSON,
    FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_exec_workflow ON executions(workflow_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_exec_status ON executions(status, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_exec_trigger ON executions(trigger_type, started_at DESC);

-- ==============================================================================
-- Webhook Logs Table
-- Detailed logging for every webhook call
-- ==============================================================================
CREATE TABLE IF NOT EXISTS webhook_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    webhook_slug TEXT NOT NULL,
    payload JSON,
    headers JSON,
    status_code INTEGER,
    response_body TEXT,
    error TEXT,
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    duration_ms INTEGER,
    forwarded_to TEXT,
    forward_status INTEGER
);

CREATE INDEX IF NOT EXISTS idx_wh_slug ON webhook_logs(webhook_slug, received_at DESC);
CREATE INDEX IF NOT EXISTS idx_wh_status ON webhook_logs(status_code, received_at DESC);

-- ==============================================================================
-- Events Table  
-- Replaces in-memory deque with persistent event log
-- ==============================================================================
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    source TEXT DEFAULT 'system',
    status TEXT DEFAULT 'info' CHECK(status IN ('success', 'error', 'warning', 'info')),
    data JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_events_type ON events(type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_status ON events(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_source ON events(source, created_at DESC);

-- ==============================================================================
-- API Keys Table
-- For authentication of external integrations
-- ==============================================================================
CREATE TABLE IF NOT EXISTS api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key_hash TEXT NOT NULL UNIQUE,
    key_prefix TEXT NOT NULL,
    name TEXT NOT NULL,
    permissions JSON DEFAULT '["read"]',
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_expires ON api_keys(expires_at) WHERE expires_at IS NOT NULL;

-- ==============================================================================
-- User Favorites Table
-- Track user favorited workflows (Phase 4)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS favorites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==============================================================================
-- Deployment History Table
-- Track workflow deployments and rollbacks (Phase 3)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS deployments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_id TEXT,
    workflow_name TEXT NOT NULL,
    version TEXT,
    status TEXT DEFAULT 'deploying' CHECK(status IN ('deploying', 'success', 'failed', 'rolled_back')),
    config JSON,
    deployed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    deployed_by TEXT,
    FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_deploy_workflow ON deployments(workflow_id, deployed_at DESC);
CREATE INDEX IF NOT EXISTS idx_deploy_status ON deployments(status, deployed_at DESC);

-- ==============================================================================
-- Environment Variables Table
-- Track environment variable changes (audit trail)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS env_var_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    var_name TEXT NOT NULL,
    var_value_hash TEXT NOT NULL,
    action TEXT CHECK(action IN ('set', 'updated', 'deleted')),
    changed_by TEXT DEFAULT 'system',
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_env_history ON env_var_history(var_name, changed_at DESC);

-- ==============================================================================
-- Cron State Table
-- Track active/inactive state of cron jobs
-- ==============================================================================
CREATE TABLE IF NOT EXISTS cron_states (
    service_id TEXT PRIMARY KEY,
    active INTEGER DEFAULT 1,
    original_cron TEXT NOT NULL,
    last_toggled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==============================================================================
-- Migration History Table
-- Track applied migrations
-- ==============================================================================
CREATE TABLE IF NOT EXISTS migration_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    migration_name TEXT NOT NULL UNIQUE,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Record this migration
INSERT INTO migration_history (migration_name) VALUES ('001_initial.sql');
