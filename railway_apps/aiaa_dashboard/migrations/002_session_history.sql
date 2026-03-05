-- Session History Tables
-- Store chat/session metadata and message history for paginated retrieval

CREATE TABLE IF NOT EXISTS session_history_sessions (
    id TEXT PRIMARY KEY,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS session_history_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES session_history_sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_session_history_messages_session
ON session_history_messages(session_id, id);

INSERT INTO migration_history (migration_name) VALUES ('002_session_history.sql');
