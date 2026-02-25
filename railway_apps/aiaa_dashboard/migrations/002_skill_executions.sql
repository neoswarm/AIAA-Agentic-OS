-- AIAA Dashboard SQLite Schema v1.1
-- Skill execution persistence with latency metrics

CREATE TABLE IF NOT EXISTS skill_executions (
    id TEXT PRIMARY KEY,
    skill_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued' CHECK(status IN ('queued', 'running', 'success', 'error', 'cancelled', 'timeout')),
    params JSON,
    output_preview TEXT,
    output_path TEXT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    first_token_at TIMESTAMP,
    completed_at TIMESTAMP,
    queue_wait_ms INTEGER,
    first_token_ms INTEGER,
    total_runtime_ms INTEGER,
    duration_ms INTEGER
);

CREATE INDEX IF NOT EXISTS idx_skill_exec_created ON skill_executions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_skill_exec_status ON skill_executions(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_skill_exec_skill ON skill_executions(skill_name, created_at DESC);

INSERT INTO migration_history (migration_name) VALUES ('002_skill_executions.sql');
