"""
AIAA Dashboard - Database Models
All database operations for workflows, events, webhooks, and executions.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from cryptography.fernet import Fernet, InvalidToken
from database import query, query_one, execute, insert, row_to_dict, rows_to_dicts


# ==============================================================================
# Workflow Operations
# ==============================================================================

def get_workflows(workflow_type: Optional[str] = None, status: str = "active") -> List[Dict[str, Any]]:
    """Get all workflows, optionally filtered by type and status."""
    if workflow_type:
        rows = query(
            "SELECT * FROM workflows WHERE type = ? AND status = ? ORDER BY name",
            (workflow_type, status)
        )
    else:
        rows = query(
            "SELECT * FROM workflows WHERE status = ? ORDER BY name",
            (status,)
        )
    return rows_to_dicts(rows)


def get_workflow(workflow_id: str) -> Optional[Dict[str, Any]]:
    """Get a single workflow by ID."""
    row = query_one("SELECT * FROM workflows WHERE id = ?", (workflow_id,))
    return row_to_dict(row)


def get_workflow_by_slug(slug: str) -> Optional[Dict[str, Any]]:
    """Get a webhook workflow by slug."""
    row = query_one("SELECT * FROM workflows WHERE webhook_slug = ?", (slug,))
    return row_to_dict(row)


def get_workflow_by_service_id(service_id: str) -> Optional[Dict[str, Any]]:
    """Get a workflow by Railway service ID."""
    row = query_one("SELECT * FROM workflows WHERE service_id = ?", (service_id,))
    return row_to_dict(row)


def upsert_workflow(
    workflow_id: str,
    name: str,
    description: str = "",
    workflow_type: str = "cron",
    status: str = "active",
    cron_schedule: Optional[str] = None,
    webhook_slug: Optional[str] = None,
    forward_url: Optional[str] = None,
    slack_notify: bool = False,
    project_id: Optional[str] = None,
    service_id: Optional[str] = None,
    config: Optional[Dict] = None
) -> int:
    """Insert or update a workflow."""
    config_json = json.dumps(config) if config else None
    
    return execute("""
        INSERT INTO workflows (
            id, name, description, type, status, cron_schedule, webhook_slug,
            forward_url, slack_notify, project_id, service_id, config, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            description = excluded.description,
            status = excluded.status,
            cron_schedule = excluded.cron_schedule,
            webhook_slug = excluded.webhook_slug,
            forward_url = excluded.forward_url,
            slack_notify = excluded.slack_notify,
            project_id = excluded.project_id,
            service_id = excluded.service_id,
            config = excluded.config,
            updated_at = CURRENT_TIMESTAMP
    """, (
        workflow_id, name, description, workflow_type, status, cron_schedule,
        webhook_slug, forward_url, 1 if slack_notify else 0, project_id,
        service_id, config_json
    ))


def delete_workflow(workflow_id: str) -> int:
    """Soft delete a workflow by setting status to 'deleted'."""
    return execute(
        "UPDATE workflows SET status = 'deleted', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (workflow_id,)
    )


def update_workflow_status(workflow_id: str, status: str) -> int:
    """Update workflow status."""
    return execute(
        "UPDATE workflows SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (status, workflow_id)
    )


def update_workflow_cron(workflow_id: str, cron_schedule: str) -> int:
    """Update workflow cron schedule."""
    return execute(
        "UPDATE workflows SET cron_schedule = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (cron_schedule, workflow_id)
    )


# ==============================================================================
# Event Operations
# ==============================================================================

def log_event(
    event_type: str,
    status: str,
    data: Dict[str, Any],
    source: str = "system"
) -> int:
    """Log an event to the database."""
    data_json = json.dumps(data) if data else None
    return insert(
        "INSERT INTO events (type, source, status, data) VALUES (?, ?, ?, ?)",
        (event_type, source, status, data_json)
    )


def get_events(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """Get recent events."""
    rows = query(
        "SELECT * FROM events ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (limit, offset)
    )
    return rows_to_dicts(rows)


def get_recent_events(limit: int = 10) -> List[Dict[str, Any]]:
    """Get most recent events."""
    return get_events(limit=limit)


def get_events_by_type(event_type: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Get events by type."""
    rows = query(
        "SELECT * FROM events WHERE type = ? ORDER BY created_at DESC LIMIT ?",
        (event_type, limit)
    )
    return rows_to_dicts(rows)


def get_events_by_status(status: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Get events by status."""
    rows = query(
        "SELECT * FROM events WHERE status = ? ORDER BY created_at DESC LIMIT ?",
        (status, limit)
    )
    return rows_to_dicts(rows)


def count_events_by_status() -> Dict[str, int]:
    """Count events by status."""
    rows = query("SELECT status, COUNT(*) as count FROM events GROUP BY status")
    return {row["status"]: row["count"] for row in rows}


# ==============================================================================
# Execution Operations
# ==============================================================================

def log_execution(
    workflow_id: Optional[str],
    workflow_name: str,
    trigger_type: str,
    metadata: Optional[Dict] = None
) -> int:
    """Log the start of a workflow execution."""
    metadata_json = json.dumps(metadata) if metadata else None
    return insert(
        """INSERT INTO executions (
            workflow_id, workflow_name, trigger_type, status, metadata, started_at
        ) VALUES (?, ?, ?, 'running', ?, CURRENT_TIMESTAMP)""",
        (workflow_id, workflow_name, trigger_type, metadata_json)
    )


def complete_execution(
    execution_id: int,
    status: str,
    output_summary: Optional[str] = None,
    error_message: Optional[str] = None
) -> int:
    """Mark an execution as complete."""
    return execute(
        """UPDATE executions SET
            status = ?,
            completed_at = CURRENT_TIMESTAMP,
            duration_ms = (julianday(CURRENT_TIMESTAMP) - julianday(started_at)) * 86400000,
            output_summary = ?,
            error_message = ?
        WHERE id = ?""",
        (status, output_summary, error_message, execution_id)
    )


def get_executions(workflow_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """Get executions, optionally filtered by workflow."""
    if workflow_id:
        rows = query(
            "SELECT * FROM executions WHERE workflow_id = ? ORDER BY started_at DESC LIMIT ?",
            (workflow_id, limit)
        )
    else:
        rows = query(
            "SELECT * FROM executions ORDER BY started_at DESC LIMIT ?",
            (limit,)
        )
    return rows_to_dicts(rows)


def get_execution(execution_id: int) -> Optional[Dict[str, Any]]:
    """Get a single execution by ID."""
    row = query_one("SELECT * FROM executions WHERE id = ?", (execution_id,))
    return row_to_dict(row)


def get_execution_stats() -> Dict[str, Any]:
    """Get execution statistics."""
    stats = {}
    
    # Total executions
    row = query_one("SELECT COUNT(*) as total FROM executions")
    stats["total_executions"] = row["total"]
    
    # By status
    rows = query("SELECT status, COUNT(*) as count FROM executions GROUP BY status")
    stats["by_status"] = {row["status"]: row["count"] for row in rows}
    
    # Success rate
    success = stats["by_status"].get("success", 0)
    total = stats["total_executions"]
    stats["success_rate"] = round(success / total * 100, 2) if total > 0 else 0
    
    # Average duration
    row = query_one("SELECT AVG(duration_ms) as avg_duration FROM executions WHERE duration_ms IS NOT NULL")
    stats["avg_duration_ms"] = int(row["avg_duration"]) if row["avg_duration"] else 0
    
    return stats


# ==============================================================================
# Session History Operations
# ==============================================================================

def upsert_session_history(session_id: str, metadata: Optional[Dict] = None) -> int:
    """Create or update a session history record."""
    metadata_json = json.dumps(metadata) if metadata else None
    return execute(
        """INSERT INTO session_history_sessions (id, metadata, created_at, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT(id) DO UPDATE SET
            metadata = COALESCE(excluded.metadata, session_history_sessions.metadata),
            updated_at = CURRENT_TIMESTAMP""",
        (session_id, metadata_json)
    )


def log_session_history_message(
    session_id: str,
    role: str,
    content: str,
    metadata: Optional[Dict] = None
) -> int:
    """Append a message to a session history."""
    upsert_session_history(session_id)
    metadata_json = json.dumps(metadata) if metadata else None
    return insert(
        """INSERT INTO session_history_messages (
            session_id, role, content, metadata, created_at
        ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)""",
        (session_id, role, content, metadata_json)
    )


def get_session_history_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Get one session history metadata record."""
    row = query_one(
        "SELECT * FROM session_history_sessions WHERE id = ?",
        (session_id,)
    )
    return row_to_dict(row)


def get_session_history_messages(
    session_id: str,
    limit: int = 50,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """Get paginated messages for a session history."""
    rows = query(
        """SELECT * FROM session_history_messages
        WHERE session_id = ?
        ORDER BY id ASC
        LIMIT ? OFFSET ?""",
        (session_id, limit, offset)
    )
    return rows_to_dicts(rows)


def count_session_history_messages(session_id: str) -> int:
    """Count total messages in a session history."""
    row = query_one(
        "SELECT COUNT(*) AS total FROM session_history_messages WHERE session_id = ?",
        (session_id,)
    )
    return int(row["total"]) if row else 0


# ==============================================================================
# Webhook Log Operations
# ==============================================================================

def log_webhook_call(
    webhook_slug: str,
    payload: Dict[str, Any],
    headers: Optional[Dict] = None,
    status_code: Optional[int] = None,
    response_body: Optional[str] = None,
    error: Optional[str] = None,
    forwarded_to: Optional[str] = None,
    forward_status: Optional[int] = None
) -> int:
    """Log a webhook call."""
    payload_json = json.dumps(payload) if payload else None
    headers_json = json.dumps(headers) if headers else None
    
    webhook_log_id = insert(
        """INSERT INTO webhook_logs (
            webhook_slug, payload, headers, status_code, response_body, 
            error, forwarded_to, forward_status, received_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
        (webhook_slug, payload_json, headers_json, status_code, response_body, 
         error, forwarded_to, forward_status)
    )
    
    return webhook_log_id


def complete_webhook_log(webhook_log_id: int, status_code: int, response_body: Optional[str] = None) -> int:
    """Mark a webhook log as processed."""
    return execute(
        """UPDATE webhook_logs SET
            processed_at = CURRENT_TIMESTAMP,
            duration_ms = (julianday(CURRENT_TIMESTAMP) - julianday(received_at)) * 86400000,
            status_code = ?,
            response_body = ?
        WHERE id = ?""",
        (status_code, response_body, webhook_log_id)
    )


def get_webhook_logs(webhook_slug: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """Get webhook logs, optionally filtered by slug."""
    if webhook_slug:
        rows = query(
            "SELECT * FROM webhook_logs WHERE webhook_slug = ? ORDER BY received_at DESC LIMIT ?",
            (webhook_slug, limit)
        )
    else:
        rows = query(
            "SELECT * FROM webhook_logs ORDER BY received_at DESC LIMIT ?",
            (limit,)
        )
    return rows_to_dicts(rows)


def get_webhook_stats(webhook_slug: str) -> Dict[str, Any]:
    """Get statistics for a webhook."""
    stats = {}
    
    # Total calls
    row = query_one("SELECT COUNT(*) as total FROM webhook_logs WHERE webhook_slug = ?", (webhook_slug,))
    stats["total_calls"] = row["total"]
    
    # By status code
    rows = query(
        "SELECT status_code, COUNT(*) as count FROM webhook_logs WHERE webhook_slug = ? GROUP BY status_code",
        (webhook_slug,)
    )
    stats["by_status_code"] = {row["status_code"]: row["count"] for row in rows}
    
    # Average duration
    row = query_one(
        "SELECT AVG(duration_ms) as avg_duration FROM webhook_logs WHERE webhook_slug = ? AND duration_ms IS NOT NULL",
        (webhook_slug,)
    )
    stats["avg_duration_ms"] = int(row["avg_duration"]) if row["avg_duration"] else 0
    
    # Error rate
    error_count = stats["by_status_code"].get(500, 0) + stats["by_status_code"].get(502, 0) + stats["by_status_code"].get(503, 0)
    stats["error_rate"] = round(error_count / stats["total_calls"] * 100, 2) if stats["total_calls"] > 0 else 0
    
    return stats


# ==============================================================================
# Settings Operations
# ==============================================================================

def set_setting(key: str, value: str) -> int:
    """Create or update a user setting value."""
    return execute(
        """INSERT INTO user_settings (setting_key, setting_value, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(setting_key) DO UPDATE SET
            setting_value = excluded.setting_value,
            updated_at = CURRENT_TIMESTAMP""",
        (key, value)
    )


def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get a single setting value by key."""
    row = query_one(
        "SELECT setting_value FROM user_settings WHERE setting_key = ?",
        (key,)
    )
    if row is None:
        return default
    return row["setting_value"]


def get_all_settings() -> Dict[str, str]:
    """Get all user settings as a key/value dictionary."""
    rows = query("SELECT setting_key, setting_value FROM user_settings ORDER BY setting_key")
    return {row["setting_key"]: row["setting_value"] for row in rows}


def get_settings_by_prefix(prefix: str) -> Dict[str, str]:
    """Get settings that begin with a key prefix."""
    rows = query(
        "SELECT setting_key, setting_value FROM user_settings WHERE setting_key LIKE ? ORDER BY setting_key",
        (f"{prefix}%",)
    )
    return {row["setting_key"]: row["setting_value"] for row in rows}


def delete_setting(key: str) -> int:
    """Delete a setting by key."""
    return execute("DELETE FROM user_settings WHERE setting_key = ?", (key,))


# ==============================================================================
# API Key Operations
# ==============================================================================

def create_api_key(
    key_hash: str,
    key_prefix: str,
    name: str,
    permissions: List[str] = None
) -> int:
    """Create a new API key."""
    if permissions is None:
        permissions = ["read"]
    permissions_json = json.dumps(permissions)
    
    return insert(
        """INSERT INTO api_keys (key_hash, key_prefix, name, permissions, created_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)""",
        (key_hash, key_prefix, name, permissions_json)
    )


def validate_api_key(key_hash: str) -> Optional[Dict[str, Any]]:
    """Validate an API key and return its details."""
    row = query_one(
        "SELECT * FROM api_keys WHERE key_hash = ? AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)",
        (key_hash,)
    )
    
    if row:
        # Update last used timestamp
        execute("UPDATE api_keys SET last_used_at = CURRENT_TIMESTAMP WHERE id = ?", (row["id"],))
    
    return row_to_dict(row)


def list_api_keys() -> List[Dict[str, Any]]:
    """List all API keys (without sensitive data)."""
    rows = query("SELECT id, key_prefix, name, permissions, created_at, last_used_at, expires_at FROM api_keys ORDER BY created_at DESC")
    return rows_to_dicts(rows)


def delete_api_key(key_id: int) -> int:
    """Delete an API key."""
    return execute("DELETE FROM api_keys WHERE id = ?", (key_id,))


# ==============================================================================
# User Settings Operations
# ==============================================================================

def set_setting(
    setting_key: str,
    setting_value: str,
    last_validated_at: Optional[str] = None,
    validation_status: Optional[str] = None,
    last_error: Optional[str] = None
) -> int:
    """Create or update a user setting, with optional token metadata."""
    if validation_status is not None and last_validated_at is None:
        last_validated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    return execute(
        """INSERT INTO user_settings (
            setting_key, setting_value, last_validated_at, validation_status, last_error, updated_at
        ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(setting_key) DO UPDATE SET
            setting_value = excluded.setting_value,
            last_validated_at = CASE
                WHEN excluded.validation_status IS NOT NULL THEN excluded.last_validated_at
                ELSE user_settings.last_validated_at
            END,
            validation_status = COALESCE(excluded.validation_status, user_settings.validation_status),
            last_error = CASE
                WHEN excluded.validation_status IS NOT NULL THEN excluded.last_error
                ELSE user_settings.last_error
            END,
            updated_at = CURRENT_TIMESTAMP""",
        (setting_key, setting_value, last_validated_at, validation_status, last_error)
    )


def get_setting(setting_key: str) -> Optional[str]:
    """Get a setting value by key."""
    row = query_one("SELECT setting_value FROM user_settings WHERE setting_key = ?", (setting_key,))
    return row["setting_value"] if row else None


def get_setting_metadata(setting_key: str) -> Dict[str, Optional[str]]:
    """Get token validation metadata for a setting key."""
    row = query_one(
        """SELECT last_validated_at, validation_status, last_error
        FROM user_settings
        WHERE setting_key = ?""",
        (setting_key,)
    )
    if not row:
        return {
            "last_validated_at": None,
            "validation_status": None,
            "last_error": None,
        }

    return {
        "last_validated_at": row["last_validated_at"],
        "validation_status": row["validation_status"],
        "last_error": row["last_error"],
    }


def update_setting_metadata(
    setting_key: str,
    validation_status: str,
    last_error: Optional[str] = None,
    last_validated_at: Optional[str] = None
) -> int:
    """Update token metadata for an existing setting key."""
    if last_validated_at is None:
        last_validated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    return execute(
        """UPDATE user_settings
        SET
            last_validated_at = ?,
            validation_status = ?,
            last_error = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE setting_key = ?""",
        (last_validated_at, validation_status, last_error, setting_key)
    )


def get_settings_by_prefix(prefix: str) -> Dict[str, str]:
    """Get all settings that start with the given prefix."""
    rows = query(
        """SELECT setting_key, setting_value
        FROM user_settings
        WHERE setting_key LIKE ?
        ORDER BY setting_key""",
        (f"{prefix}%",)
    )
    return {row["setting_key"]: row["setting_value"] for row in rows}


def get_all_settings() -> Dict[str, str]:
    """Get all settings."""
    rows = query("SELECT setting_key, setting_value FROM user_settings ORDER BY setting_key")
    return {row["setting_key"]: row["setting_value"] for row in rows}


# ==============================================================================
# Cron State Operations
# ==============================================================================

def get_cron_state(service_id: str) -> Optional[Dict[str, Any]]:
    """Get cron state for a service."""
    row = query_one("SELECT * FROM cron_states WHERE service_id = ?", (service_id,))
    return row_to_dict(row)


def upsert_cron_state(service_id: str, active: bool, original_cron: str) -> int:
    """Insert or update cron state."""
    return execute(
        """INSERT INTO cron_states (service_id, active, original_cron, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(service_id) DO UPDATE SET
            active = excluded.active,
            original_cron = excluded.original_cron,
            last_toggled_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP""",
        (service_id, 1 if active else 0, original_cron)
    )


def toggle_cron_state(service_id: str) -> bool:
    """Toggle cron active state and return new state."""
    state = get_cron_state(service_id)
    if state:
        new_active = not bool(state["active"])
        upsert_cron_state(service_id, new_active, state["original_cron"])
        return new_active
    return True


# ==============================================================================
# Favorites Operations
# ==============================================================================

def add_favorite(workflow_name: str) -> int:
    """Add a workflow to favorites."""
    return insert(
        "INSERT OR IGNORE INTO favorites (workflow_name) VALUES (?)",
        (workflow_name,)
    )


def remove_favorite(workflow_name: str) -> int:
    """Remove a workflow from favorites."""
    return execute("DELETE FROM favorites WHERE workflow_name = ?", (workflow_name,))


def get_favorites() -> List[str]:
    """Get all favorite workflow names."""
    rows = query("SELECT workflow_name FROM favorites ORDER BY created_at DESC")
    return [row["workflow_name"] for row in rows]


def is_favorite(workflow_name: str) -> bool:
    """Check if a workflow is favorited."""
    row = query_one("SELECT 1 FROM favorites WHERE workflow_name = ?", (workflow_name,))
    return row is not None


# ==============================================================================
# Skill Execution Operations
# ==============================================================================

def create_skill_execution(
    execution_id: str,
    skill_name: str,
    params: Optional[Dict] = None,
    cost_estimate: Optional[float] = None
) -> str:
    """Create a new skill execution record. Returns the execution ID."""
    params_json = json.dumps(params) if params else None
    execute(
        """INSERT INTO skill_executions (id, skill_name, params, status, cost_estimate, created_at)
        VALUES (?, ?, ?, 'queued', ?, datetime('now'))""",
        (execution_id, skill_name, params_json, cost_estimate)
    )
    return execution_id


def update_skill_execution_status(
    execution_id: str,
    status: str,
    output_preview: Optional[str] = None,
    output_path: Optional[str] = None,
    error_message: Optional[str] = None
) -> int:
    """Update a skill execution status and optional fields."""
    if status == 'running':
        return execute(
            "UPDATE skill_executions SET status = ?, started_at = datetime('now') WHERE id = ?",
            (status, execution_id)
        )
    elif status in ('success', 'error', 'cancelled'):
        return execute(
            """UPDATE skill_executions SET
                status = ?,
                completed_at = datetime('now'),
                duration_ms = CAST((julianday(datetime('now')) - julianday(started_at)) * 86400000 AS INTEGER),
                output_preview = COALESCE(?, output_preview),
                output_path = COALESCE(?, output_path),
                error_message = COALESCE(?, error_message)
            WHERE id = ?""",
            (status, output_preview, output_path, error_message, execution_id)
        )
    else:
        return execute(
            "UPDATE skill_executions SET status = ? WHERE id = ?",
            (status, execution_id)
        )


def get_skill_execution(execution_id: str) -> Optional[Dict[str, Any]]:
    """Get a single skill execution by ID."""
    row = query_one("SELECT * FROM skill_executions WHERE id = ?", (execution_id,))
    return row_to_dict(row)


def get_skill_executions(
    skill_name: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Get skill executions with optional filters."""
    conditions = []
    params = []
    if skill_name:
        conditions.append("skill_name = ?")
        params.append(skill_name)
    if status:
        conditions.append("status = ?")
        params.append(status)

    where = " AND ".join(conditions)
    if where:
        where = "WHERE " + where

    params.append(limit)
    rows = query(
        f"SELECT * FROM skill_executions {where} ORDER BY created_at DESC LIMIT ?",
        tuple(params)
    )
    return rows_to_dicts(rows)


def get_recent_skill_executions(limit: int = 10) -> List[Dict[str, Any]]:
    """Get most recent skill executions."""
    return get_skill_executions(limit=limit)


def cancel_skill_execution(execution_id: str) -> int:
    """Cancel a queued or running skill execution."""
    return execute(
        """UPDATE skill_executions SET
            status = 'cancelled',
            completed_at = datetime('now'),
            duration_ms = CASE
                WHEN started_at IS NOT NULL
                THEN CAST((julianday(datetime('now')) - julianday(started_at)) * 86400000 AS INTEGER)
                ELSE 0
            END
        WHERE id = ? AND status IN ('queued', 'running')""",
        (execution_id,)
    )


def get_skill_execution_stats() -> Dict[str, Any]:
    """Get skill execution statistics."""
    stats = {}

    row = query_one("SELECT COUNT(*) as total FROM skill_executions")
    stats["total"] = row["total"]

    rows = query("SELECT status, COUNT(*) as count FROM skill_executions GROUP BY status")
    stats["by_status"] = {row["status"]: row["count"] for row in rows}

    success = stats["by_status"].get("success", 0)
    total = stats["total"]
    stats["success_rate"] = round(success / total * 100, 2) if total > 0 else 0

    row = query_one(
        "SELECT AVG(duration_ms) as avg_duration FROM skill_executions WHERE duration_ms IS NOT NULL"
    )
    stats["avg_duration_ms"] = int(row["avg_duration"]) if row["avg_duration"] else 0

    rows = query(
        "SELECT skill_name, COUNT(*) as count FROM skill_executions GROUP BY skill_name ORDER BY count DESC LIMIT 10"
    )
    stats["top_skills"] = {row["skill_name"]: row["count"] for row in rows}

    return stats


# ==============================================================================
# Client Profile Operations
# ==============================================================================

def create_client_profile(
    name: str,
    slug: str,
    industry: Optional[str] = None,
    website: Optional[str] = None,
    description: Optional[str] = None,
    target_audience: Optional[str] = None,
    goals: Optional[str] = None,
    competitors: Optional[str] = None,
    brand_voice: Optional[str] = None,
    rules: Optional[Dict] = None,
    preferences: Optional[Dict] = None
) -> int:
    """Create a new client profile."""
    rules_json = json.dumps(rules) if rules else None
    preferences_json = json.dumps(preferences) if preferences else None
    return insert(
        """INSERT INTO client_profiles (
            name, slug, industry, website, description, target_audience,
            goals, competitors, brand_voice, rules, preferences
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (name, slug, industry, website, description, target_audience,
         goals, competitors, brand_voice, rules_json, preferences_json)
    )


def get_client_profile(slug: str) -> Optional[Dict[str, Any]]:
    """Get a client profile by slug."""
    row = query_one("SELECT * FROM client_profiles WHERE slug = ?", (slug,))
    return row_to_dict(row)


def get_client_profile_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Get a client profile by name."""
    row = query_one("SELECT * FROM client_profiles WHERE name = ?", (name,))
    return row_to_dict(row)


def get_all_client_profiles() -> List[Dict[str, Any]]:
    """Get all client profiles."""
    rows = query("SELECT * FROM client_profiles ORDER BY name")
    return rows_to_dicts(rows)


def update_client_profile(slug: str, **kwargs) -> int:
    """Update a client profile by slug. Pass only the fields to update."""
    allowed_fields = {
        'name', 'industry', 'website', 'description', 'target_audience',
        'goals', 'competitors', 'brand_voice', 'rules', 'preferences'
    }
    sets = []
    params = []
    for key, value in kwargs.items():
        if key not in allowed_fields:
            continue
        if key in ('rules', 'preferences') and isinstance(value, dict):
            value = json.dumps(value)
        sets.append(f"{key} = ?")
        params.append(value)

    if not sets:
        return 0

    sets.append("updated_at = datetime('now')")
    params.append(slug)

    return execute(
        f"UPDATE client_profiles SET {', '.join(sets)} WHERE slug = ?",
        tuple(params)
    )


def delete_client_profile(slug: str) -> int:
    """Delete a client profile by slug."""
    return execute("DELETE FROM client_profiles WHERE slug = ?", (slug,))


def search_client_profiles(query_str: str) -> List[Dict[str, Any]]:
    """Search client profiles by name, industry, or description."""
    pattern = f"%{query_str}%"
    rows = query(
        """SELECT * FROM client_profiles
        WHERE name LIKE ? OR industry LIKE ? OR description LIKE ?
        ORDER BY name""",
        (pattern, pattern, pattern)
    )
    return rows_to_dicts(rows)


# ==============================================================================
# User Settings Operations
# ==============================================================================

def get_setting(key: str) -> Optional[str]:
    """Get a user setting value by key."""
    row = query_one("SELECT value FROM user_settings WHERE key = ?", (key,))
    return row["value"] if row else None


def set_setting(key: str, value: str) -> int:
    """Set a user setting (upsert)."""
    return execute(
        """INSERT INTO user_settings (key, value, updated_at)
        VALUES (?, ?, datetime('now'))
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            updated_at = datetime('now')""",
        (key, value)
    )


def get_all_settings() -> Dict[str, str]:
    """Get all user settings as a dictionary."""
    rows = query("SELECT key, value FROM user_settings ORDER BY key")
    return {row["key"]: row["value"] for row in rows}


def delete_setting(key: str) -> int:
    """Delete a user setting."""
    return execute("DELETE FROM user_settings WHERE key = ?", (key,))


def get_settings_by_prefix(prefix: str) -> Dict[str, str]:
    """Get all settings matching a key prefix (e.g. 'api_key.')."""
    rows = query(
        "SELECT key, value FROM user_settings WHERE key LIKE ? ORDER BY key",
        (f"{prefix}%",)
    )
    return {row["key"]: row["value"] for row in rows}


# ==============================================================================
# Deployment Operations (Phase 3)
# ==============================================================================

def log_deployment(
    workflow_id: Optional[str],
    workflow_name: str,
    version: Optional[str] = None,
    config: Optional[Dict] = None,
    deployed_by: str = "system"
) -> int:
    """Log a deployment."""
    config_json = json.dumps(config) if config else None
    return insert(
        """INSERT INTO deployments (workflow_id, workflow_name, version, config, deployed_by, status)
        VALUES (?, ?, ?, ?, ?, 'deploying')""",
        (workflow_id, workflow_name, version, config_json, deployed_by)
    )


def complete_deployment(deployment_id: int, status: str, error_message: Optional[str] = None) -> int:
    """Mark a deployment as complete."""
    return execute(
        """UPDATE deployments SET
            status = ?,
            completed_at = CURRENT_TIMESTAMP,
            error_message = ?
        WHERE id = ?""",
        (status, error_message, deployment_id)
    )


def get_deployments(workflow_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
    """Get deployments, optionally filtered by workflow."""
    if workflow_id:
        rows = query(
            "SELECT * FROM deployments WHERE workflow_id = ? ORDER BY deployed_at DESC LIMIT ?",
            (workflow_id, limit)
        )
    else:
        rows = query(
            "SELECT * FROM deployments ORDER BY deployed_at DESC LIMIT ?",
            (limit,)
        )
    return rows_to_dicts(rows)
