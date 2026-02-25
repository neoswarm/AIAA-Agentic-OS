"""
AIAA Dashboard - Database Models
All database operations for workflows, events, webhooks, and executions.
"""

import json
import os
import base64
import hashlib
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


def get_skill_executions(
    skill_name: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Get executions with skill-listing friendly fields and optional filters."""
    filters: List[str] = []
    params: List[Any] = []

    if skill_name:
        filters.append("workflow_name = ?")
        params.append(skill_name)

    if status:
        filters.append("status = ?")
        params.append(status)

    if date_from:
        filters.append("DATE(started_at) >= DATE(?)")
        params.append(date_from)

    if date_to:
        filters.append("DATE(started_at) <= DATE(?)")
        params.append(date_to)

    if search:
        search_term = f"%{search.strip().lower()}%"
        filters.append(
            "("
            "LOWER(workflow_name) LIKE ? OR "
            "LOWER(COALESCE(trigger_type, '')) LIKE ? OR "
            "LOWER(COALESCE(output_summary, '')) LIKE ? OR "
            "LOWER(COALESCE(error_message, '')) LIKE ?"
            ")"
        )
        params.extend([search_term, search_term, search_term, search_term])

    sql = """
        SELECT
            id,
            workflow_id,
            workflow_name,
            workflow_name AS skill_name,
            trigger_type,
            status,
            started_at,
            started_at AS created_at,
            completed_at,
            duration_ms,
            output_summary,
            output_summary AS output_preview,
            error_message,
            metadata
        FROM executions
    """
    if filters:
        sql += " WHERE " + " AND ".join(filters)
    sql += " ORDER BY started_at DESC LIMIT ?"

    params.append(max(1, limit))
    rows = query(sql, tuple(params))
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
# Skill Execution Operations
# ==============================================================================

def create_skill_execution(
    execution_id: str,
    skill_name: str,
    params: Optional[Dict[str, Any]] = None,
) -> int:
    """Create a queued skill execution record."""
    params_json = json.dumps(params) if params is not None else None
    return execute(
        """INSERT INTO skill_executions (
            id, skill_name, status, params, created_at
        ) VALUES (?, ?, 'queued', ?, CURRENT_TIMESTAMP)""",
        (execution_id, skill_name, params_json),
    )


def update_skill_execution_status(
    execution_id: str,
    status: str,
    output_preview: Optional[str] = None,
    output_path: Optional[str] = None,
    error_message: Optional[str] = None,
) -> int:
    """Update a skill execution status and latency metrics."""
    has_preview = bool(output_preview)

    if status == "running":
        return execute(
            """UPDATE skill_executions SET
                status = 'running',
                started_at = COALESCE(started_at, CURRENT_TIMESTAMP),
                queue_wait_ms = COALESCE(
                    queue_wait_ms,
                    CAST((julianday(CURRENT_TIMESTAMP) - julianday(created_at)) * 86400000 AS INTEGER)
                ),
                first_token_at = CASE
                    WHEN first_token_at IS NULL AND ? = 1 THEN CURRENT_TIMESTAMP
                    ELSE first_token_at
                END,
                first_token_ms = CASE
                    WHEN first_token_ms IS NULL AND ? = 1 THEN CAST((julianday(CURRENT_TIMESTAMP) - julianday(created_at)) * 86400000 AS INTEGER)
                    ELSE first_token_ms
                END,
                output_preview = COALESCE(?, output_preview),
                output_path = COALESCE(?, output_path),
                error_message = COALESCE(?, error_message)
            WHERE id = ?""",
            (
                1 if has_preview else 0,
                1 if has_preview else 0,
                output_preview,
                output_path,
                error_message,
                execution_id,
            ),
        )

    if status in {"success", "error", "cancelled", "timeout"}:
        return execute(
            """UPDATE skill_executions SET
                status = ?,
                completed_at = COALESCE(completed_at, CURRENT_TIMESTAMP),
                queue_wait_ms = COALESCE(
                    queue_wait_ms,
                    CASE
                        WHEN started_at IS NOT NULL
                            THEN CAST((julianday(started_at) - julianday(created_at)) * 86400000 AS INTEGER)
                        ELSE CAST((julianday(CURRENT_TIMESTAMP) - julianday(created_at)) * 86400000 AS INTEGER)
                    END
                ),
                first_token_at = CASE
                    WHEN first_token_at IS NULL AND ? = 1 THEN CURRENT_TIMESTAMP
                    ELSE first_token_at
                END,
                first_token_ms = CASE
                    WHEN first_token_ms IS NULL AND ? = 1 THEN CAST((julianday(CURRENT_TIMESTAMP) - julianday(created_at)) * 86400000 AS INTEGER)
                    ELSE first_token_ms
                END,
                duration_ms = COALESCE(
                    duration_ms,
                    CASE
                        WHEN started_at IS NOT NULL
                            THEN CAST((julianday(CURRENT_TIMESTAMP) - julianday(started_at)) * 86400000 AS INTEGER)
                        ELSE NULL
                    END
                ),
                total_runtime_ms = COALESCE(
                    total_runtime_ms,
                    CAST((julianday(CURRENT_TIMESTAMP) - julianday(created_at)) * 86400000 AS INTEGER)
                ),
                output_preview = COALESCE(?, output_preview),
                output_path = COALESCE(?, output_path),
                error_message = COALESCE(?, error_message)
            WHERE id = ?""",
            (
                status,
                1 if has_preview else 0,
                1 if has_preview else 0,
                output_preview,
                output_path,
                error_message,
                execution_id,
            ),
        )

    return execute(
        """UPDATE skill_executions SET
            status = ?,
            output_preview = COALESCE(?, output_preview),
            output_path = COALESCE(?, output_path),
            error_message = COALESCE(?, error_message)
        WHERE id = ?""",
        (status, output_preview, output_path, error_message, execution_id),
    )


def get_skill_execution(execution_id: str) -> Optional[Dict[str, Any]]:
    """Get a single skill execution by ID."""
    row = query_one("SELECT * FROM skill_executions WHERE id = ?", (execution_id,))
    return row_to_dict(row)


def get_skill_executions(
    skill_name: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Get skill executions with optional filters."""
    sql = "SELECT * FROM skill_executions WHERE 1=1"
    params: List[Any] = []

    if skill_name:
        sql += " AND skill_name = ?"
        params.append(skill_name)
    if status:
        sql += " AND status = ?"
        params.append(status)

    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    rows = query(sql, tuple(params))
    return rows_to_dicts(rows)


def get_recent_skill_executions(limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent skill executions."""
    return get_skill_executions(limit=limit)


def cancel_skill_execution(execution_id: str) -> int:
    """Cancel a queued or running skill execution."""
    return execute(
        """UPDATE skill_executions SET
            status = 'cancelled',
            completed_at = CURRENT_TIMESTAMP,
            queue_wait_ms = COALESCE(
                queue_wait_ms,
                CASE
                    WHEN started_at IS NOT NULL
                        THEN CAST((julianday(started_at) - julianday(created_at)) * 86400000 AS INTEGER)
                    ELSE CAST((julianday(CURRENT_TIMESTAMP) - julianday(created_at)) * 86400000 AS INTEGER)
                END
            ),
            duration_ms = CASE
                WHEN started_at IS NOT NULL
                    THEN CAST((julianday(CURRENT_TIMESTAMP) - julianday(started_at)) * 86400000 AS INTEGER)
                ELSE duration_ms
            END,
            total_runtime_ms = CAST((julianday(CURRENT_TIMESTAMP) - julianday(created_at)) * 86400000 AS INTEGER)
        WHERE id = ? AND status IN ('queued', 'running')""",
        (execution_id,),
    )


def get_skill_execution_stats() -> Dict[str, Any]:
    """Get aggregate skill execution statistics."""
    stats: Dict[str, Any] = {}

    row = query_one("SELECT COUNT(*) AS total FROM skill_executions")
    stats["total_executions"] = row["total"] if row else 0

    rows = query("SELECT status, COUNT(*) AS count FROM skill_executions GROUP BY status")
    stats["by_status"] = {r["status"]: r["count"] for r in rows}

    success_count = stats["by_status"].get("success", 0)
    total_count = stats["total_executions"]
    stats["success_rate"] = round((success_count / total_count) * 100, 2) if total_count > 0 else 0

    row = query_one("SELECT AVG(duration_ms) AS avg_duration FROM skill_executions WHERE duration_ms IS NOT NULL")
    stats["avg_duration_ms"] = int(row["avg_duration"]) if row and row["avg_duration"] else 0

    row = query_one("SELECT AVG(queue_wait_ms) AS avg_queue_wait FROM skill_executions WHERE queue_wait_ms IS NOT NULL")
    stats["avg_queue_wait_ms"] = int(row["avg_queue_wait"]) if row and row["avg_queue_wait"] else 0

    row = query_one("SELECT AVG(first_token_ms) AS avg_first_token FROM skill_executions WHERE first_token_ms IS NOT NULL")
    stats["avg_first_token_ms"] = int(row["avg_first_token"]) if row and row["avg_first_token"] else 0

    row = query_one("SELECT AVG(total_runtime_ms) AS avg_total_runtime FROM skill_executions WHERE total_runtime_ms IS NOT NULL")
    stats["avg_total_runtime_ms"] = int(row["avg_total_runtime"]) if row and row["avg_total_runtime"] else 0

    rows = query(
        """SELECT skill_name, COUNT(*) AS runs
        FROM skill_executions
        GROUP BY skill_name
        ORDER BY runs DESC
        LIMIT 8"""
    )
    stats["top_skills"] = {r["skill_name"]: r["runs"] for r in rows}

    return stats


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
    cost_estimate: Optional[float] = None,
    telemetry: Optional[Dict[str, Any]] = None,
    profile_used: Optional[str] = None,
) -> str:
    """Create a new skill execution record. Returns the execution ID."""
    params_json = json.dumps(params) if params is not None else None
    telemetry_json = json.dumps(telemetry) if telemetry is not None else None

    try:
        execute(
            """INSERT INTO skill_executions (
                id, skill_name, params, status, cost_estimate, telemetry, profile_used, created_at
            ) VALUES (?, ?, ?, 'queued', ?, ?, ?, datetime('now'))""",
            (execution_id, skill_name, params_json, cost_estimate, telemetry_json, profile_used),
        )
    except Exception:
        # Backward-compatible fallback for older schemas without telemetry/profile_used.
        execute(
            """INSERT INTO skill_executions (
                id, skill_name, params, status, cost_estimate, created_at
            ) VALUES (?, ?, ?, 'queued', ?, datetime('now'))""",
            (execution_id, skill_name, params_json, cost_estimate),
        )
    return execution_id


def update_skill_execution_status(
    execution_id: str,
    status: str,
    output_preview: Optional[str] = None,
    output_path: Optional[str] = None,
    error_message: Optional[str] = None
) -> int:
    """Update a skill execution status and latency metrics."""
    has_preview = bool(output_preview)

    try:
        if status == "running":
            return execute(
                """UPDATE skill_executions SET
                    status = 'running',
                    started_at = COALESCE(started_at, CURRENT_TIMESTAMP),
                    queue_wait_ms = COALESCE(
                        queue_wait_ms,
                        CAST((julianday(CURRENT_TIMESTAMP) - julianday(created_at)) * 86400000 AS INTEGER)
                    ),
                    first_token_at = CASE
                        WHEN first_token_at IS NULL AND ? = 1 THEN CURRENT_TIMESTAMP
                        ELSE first_token_at
                    END,
                    first_token_ms = CASE
                        WHEN first_token_ms IS NULL AND ? = 1 THEN CAST((julianday(CURRENT_TIMESTAMP) - julianday(created_at)) * 86400000 AS INTEGER)
                        ELSE first_token_ms
                    END,
                    output_preview = COALESCE(?, output_preview),
                    output_path = COALESCE(?, output_path),
                    error_message = COALESCE(?, error_message)
                WHERE id = ?""",
                (
                    1 if has_preview else 0,
                    1 if has_preview else 0,
                    output_preview,
                    output_path,
                    error_message,
                    execution_id,
                ),
            )

        if status in {"success", "error", "cancelled", "timeout"}:
            return execute(
                """UPDATE skill_executions SET
                    status = ?,
                    completed_at = COALESCE(completed_at, CURRENT_TIMESTAMP),
                    queue_wait_ms = COALESCE(
                        queue_wait_ms,
                        CASE
                            WHEN started_at IS NOT NULL
                                THEN CAST((julianday(started_at) - julianday(created_at)) * 86400000 AS INTEGER)
                            ELSE CAST((julianday(CURRENT_TIMESTAMP) - julianday(created_at)) * 86400000 AS INTEGER)
                        END
                    ),
                    first_token_at = CASE
                        WHEN first_token_at IS NULL AND ? = 1 THEN CURRENT_TIMESTAMP
                        ELSE first_token_at
                    END,
                    first_token_ms = CASE
                        WHEN first_token_ms IS NULL AND ? = 1 THEN CAST((julianday(CURRENT_TIMESTAMP) - julianday(created_at)) * 86400000 AS INTEGER)
                        ELSE first_token_ms
                    END,
                    duration_ms = COALESCE(
                        duration_ms,
                        CASE
                            WHEN started_at IS NOT NULL
                                THEN CAST((julianday(CURRENT_TIMESTAMP) - julianday(started_at)) * 86400000 AS INTEGER)
                            ELSE NULL
                        END
                    ),
                    total_runtime_ms = COALESCE(
                        total_runtime_ms,
                        CAST((julianday(CURRENT_TIMESTAMP) - julianday(created_at)) * 86400000 AS INTEGER)
                    ),
                    output_preview = COALESCE(?, output_preview),
                    output_path = COALESCE(?, output_path),
                    error_message = COALESCE(?, error_message)
                WHERE id = ?""",
                (
                    status,
                    1 if has_preview else 0,
                    1 if has_preview else 0,
                    output_preview,
                    output_path,
                    error_message,
                    execution_id,
                ),
            )
    except Exception:
        # Compatibility fallback for pre-latency schemas.
        if status == 'running':
            return execute(
                "UPDATE skill_executions SET status = ?, started_at = datetime('now') WHERE id = ?",
                (status, execution_id),
            )
        if status in ('success', 'error', 'cancelled'):
            return execute(
                """UPDATE skill_executions SET
                    status = ?,
                    completed_at = datetime('now'),
                    duration_ms = CAST((julianday(datetime('now')) - julianday(started_at)) * 86400000 AS INTEGER),
                    output_preview = COALESCE(?, output_preview),
                    output_path = COALESCE(?, output_path),
                    error_message = COALESCE(?, error_message)
                WHERE id = ?""",
                (status, output_preview, output_path, error_message, execution_id),
            )

    return execute(
        """UPDATE skill_executions SET
            status = ?,
            output_preview = COALESCE(?, output_preview),
            output_path = COALESCE(?, output_path),
            error_message = COALESCE(?, error_message)
        WHERE id = ?""",
        (status, output_preview, output_path, error_message, execution_id),
    )


def get_skill_execution(execution_id: str) -> Optional[Dict[str, Any]]:
    """Get a single skill execution by ID."""
    row = query_one("SELECT * FROM skill_executions WHERE id = ?", (execution_id,))
    payload = row_to_dict(row)
    if payload is None:
        return None

    params_value = payload.get("params")
    if isinstance(params_value, str):
        try:
            payload["params"] = json.loads(params_value)
        except Exception:
            pass

    telemetry_value = payload.get("telemetry")
    if isinstance(telemetry_value, str):
        try:
            payload["telemetry"] = json.loads(telemetry_value)
        except Exception:
            pass

    return payload


def get_skill_executions(
    skill_name: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Get executions with skill-listing friendly fields and optional filters."""
    filters: List[str] = []
    params: List[Any] = []

    if skill_name:
        filters.append("workflow_name = ?")
        params.append(skill_name)

    if status:
        filters.append("status = ?")
        params.append(status)

    if date_from:
        filters.append("DATE(started_at) >= DATE(?)")
        params.append(date_from)

    if date_to:
        filters.append("DATE(started_at) <= DATE(?)")
        params.append(date_to)

    if search:
        search_term = f"%{search.strip().lower()}%"
        filters.append(
            "("
            "LOWER(workflow_name) LIKE ? OR "
            "LOWER(COALESCE(trigger_type, '')) LIKE ? OR "
            "LOWER(COALESCE(output_summary, '')) LIKE ? OR "
            "LOWER(COALESCE(error_message, '')) LIKE ?"
            ")"
        )
        params.extend([search_term, search_term, search_term, search_term])

    sql = """
        SELECT
            id,
            workflow_id,
            workflow_name,
            workflow_name AS skill_name,
            trigger_type,
            status,
            started_at,
            started_at AS created_at,
            completed_at,
            duration_ms,
            output_summary,
            output_summary AS output_preview,
            error_message,
            metadata
        FROM executions
    """
    if filters:
        sql += " WHERE " + " AND ".join(filters)
    sql += " ORDER BY started_at DESC LIMIT ?"

    params.append(max(1, limit))
    rows = query(sql, tuple(params))
    return rows_to_dicts(rows)


def get_recent_skill_executions(limit: int = 10) -> List[Dict[str, Any]]:
    """Get most recent skill executions."""
    rows = query(
        "SELECT * FROM skill_executions ORDER BY created_at DESC LIMIT ?",
        (max(1, limit),),
    )
    return rows_to_dicts(rows)


def cancel_skill_execution(execution_id: str) -> int:
    """Cancel a queued or running skill execution."""
    try:
        return execute(
            """UPDATE skill_executions SET
                status = 'cancelled',
                completed_at = CURRENT_TIMESTAMP,
                queue_wait_ms = COALESCE(
                    queue_wait_ms,
                    CASE
                        WHEN started_at IS NOT NULL
                            THEN CAST((julianday(started_at) - julianday(created_at)) * 86400000 AS INTEGER)
                        ELSE CAST((julianday(CURRENT_TIMESTAMP) - julianday(created_at)) * 86400000 AS INTEGER)
                    END
                ),
                duration_ms = CASE
                    WHEN started_at IS NOT NULL
                        THEN CAST((julianday(CURRENT_TIMESTAMP) - julianday(started_at)) * 86400000 AS INTEGER)
                    ELSE duration_ms
                END,
                total_runtime_ms = CAST((julianday(CURRENT_TIMESTAMP) - julianday(created_at)) * 86400000 AS INTEGER)
            WHERE id = ? AND status IN ('queued', 'running')""",
            (execution_id,),
        )
    except Exception:
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
            (execution_id,),
        )


def get_skill_execution_stats() -> Dict[str, Any]:
    """Get aggregate skill execution statistics."""
    stats: Dict[str, Any] = {}

    row = query_one("SELECT COUNT(*) AS total FROM skill_executions")
    stats["total_executions"] = row["total"] if row else 0
    stats["total"] = stats["total_executions"]

    rows = query("SELECT status, COUNT(*) AS count FROM skill_executions GROUP BY status")
    stats["by_status"] = {r["status"]: r["count"] for r in rows}

    success_count = stats["by_status"].get("success", 0)
    total_count = stats["total_executions"]
    stats["success_rate"] = round((success_count / total_count) * 100, 2) if total_count > 0 else 0

    row = query_one("SELECT AVG(duration_ms) AS avg_duration FROM skill_executions WHERE duration_ms IS NOT NULL")
    stats["avg_duration_ms"] = int(row["avg_duration"]) if row and row["avg_duration"] else 0

    row = query_one("SELECT AVG(queue_wait_ms) AS avg_queue_wait FROM skill_executions WHERE queue_wait_ms IS NOT NULL")
    stats["avg_queue_wait_ms"] = int(row["avg_queue_wait"]) if row and row["avg_queue_wait"] else 0

    row = query_one("SELECT AVG(first_token_ms) AS avg_first_token FROM skill_executions WHERE first_token_ms IS NOT NULL")
    stats["avg_first_token_ms"] = int(row["avg_first_token"]) if row and row["avg_first_token"] else 0

    row = query_one("SELECT AVG(total_runtime_ms) AS avg_total_runtime FROM skill_executions WHERE total_runtime_ms IS NOT NULL")
    stats["avg_total_runtime_ms"] = int(row["avg_total_runtime"]) if row and row["avg_total_runtime"] else 0

    rows = query(
        """SELECT skill_name, COUNT(*) AS runs
        FROM skill_executions
        GROUP BY skill_name
        ORDER BY runs DESC
        LIMIT 8"""
    )
    stats["top_skills"] = {r["skill_name"]: r["runs"] for r in rows}

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
# Session History Operations
# ==============================================================================

def upsert_session_history(session_id: str, metadata: Optional[Dict[str, Any]] = None) -> int:
    """Insert or update a session history envelope."""
    metadata_json = json.dumps(metadata or {})
    return execute(
        """INSERT INTO session_history_sessions (id, metadata, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(id) DO UPDATE SET
            metadata = excluded.metadata,
            updated_at = CURRENT_TIMESTAMP""",
        (session_id, metadata_json),
    )


def log_session_history_message(
    session_id: str,
    role: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> int:
    """Append one chat message to session history."""
    metadata_json = json.dumps(metadata or {})
    # Ensure session shell exists without clobbering existing metadata.
    execute(
        """INSERT INTO session_history_sessions (id, metadata, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(id) DO UPDATE SET
            updated_at = CURRENT_TIMESTAMP""",
        (session_id, json.dumps({})),
    )
    return insert(
        """INSERT INTO session_history_messages (session_id, role, content, metadata)
        VALUES (?, ?, ?, ?)""",
        (session_id, role, content, metadata_json),
    )


def get_session_history_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Get one session history row by session id."""
    row = query_one(
        "SELECT id, metadata, created_at, updated_at FROM session_history_sessions WHERE id = ?",
        (session_id,),
    )
    payload = row_to_dict(row)
    if payload is None:
        return None

    metadata = payload.get("metadata")
    if isinstance(metadata, str):
        try:
            payload["metadata"] = json.loads(metadata)
        except Exception:
            payload["metadata"] = {}
    elif metadata is None:
        payload["metadata"] = {}

    return payload


def get_session_history_messages(
    session_id: str,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """Get paginated session history messages in insertion order."""
    rows = query(
        """SELECT id, session_id, role, content, metadata, created_at
        FROM session_history_messages
        WHERE session_id = ?
        ORDER BY id ASC
        LIMIT ? OFFSET ?""",
        (session_id, max(1, limit), max(0, offset)),
    )
    payloads = rows_to_dicts(rows)
    for item in payloads:
        metadata = item.get("metadata")
        if isinstance(metadata, str):
            try:
                item["metadata"] = json.loads(metadata)
            except Exception:
                item["metadata"] = {}
        elif metadata is None:
            item["metadata"] = {}
    return payloads


def count_session_history_messages(session_id: str) -> int:
    """Count messages for a given session history id."""
    row = query_one(
        "SELECT COUNT(*) AS total FROM session_history_messages WHERE session_id = ?",
        (session_id,),
    )
    return int(row["total"]) if row else 0


# ==============================================================================
# User Settings Operations
# ==============================================================================

_ENCRYPTED_SETTING_PREFIX = "enc:v1:"


def _requires_encryption(setting_key: str) -> bool:
    """Return True for setting keys that must be encrypted at rest."""
    return setting_key == "claude_setup_token" or setting_key.endswith(".claude_setup_token")


def _get_settings_fernet() -> Fernet:
    """Build a Fernet cipher from explicit key or Flask secret."""
    raw_key = (
        os.getenv("SETTINGS_ENCRYPTION_KEY")
        or os.getenv("FLASK_SECRET_KEY")
        or os.getenv("SECRET_KEY")
    )
    if not raw_key:
        raise RuntimeError(
            "Missing encryption key. Set SETTINGS_ENCRYPTION_KEY or FLASK_SECRET_KEY."
        )

    try:
        return Fernet(raw_key.encode("utf-8"))
    except Exception:
        derived = base64.urlsafe_b64encode(hashlib.sha256(raw_key.encode("utf-8")).digest())
        return Fernet(derived)


def _encrypt_setting_value(setting_key: str, setting_value: Optional[str]) -> Optional[str]:
    """Encrypt sensitive setting values before persisting to storage."""
    if setting_value is None or not _requires_encryption(setting_key):
        return setting_value
    if setting_value.startswith(_ENCRYPTED_SETTING_PREFIX):
        return setting_value

    cipher = _get_settings_fernet()
    encrypted = cipher.encrypt(setting_value.encode("utf-8")).decode("utf-8")
    return f"{_ENCRYPTED_SETTING_PREFIX}{encrypted}"


def _decrypt_setting_value(setting_key: str, stored_value: Optional[str]) -> Optional[str]:
    """Decrypt sensitive setting values after reading from storage."""
    if stored_value is None or not _requires_encryption(setting_key):
        return stored_value
    if not stored_value.startswith(_ENCRYPTED_SETTING_PREFIX):
        # Backward compatibility for pre-encryption rows.
        return stored_value

    cipher = _get_settings_fernet()
    token = stored_value[len(_ENCRYPTED_SETTING_PREFIX):]
    try:
        return cipher.decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise RuntimeError("Unable to decrypt claude_setup_token setting value.") from exc


def _upsert_user_setting(
    setting_key: str,
    setting_value: Optional[str],
    last_validated_at: Optional[str] = None,
    validation_status: Optional[str] = None,
    last_error: Optional[str] = None,
) -> int:
    """Upsert user_settings row with optional token metadata."""
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
        (setting_key, setting_value or "", last_validated_at, validation_status, last_error),
    )


def set_setting(
    setting_key: str,
    setting_value: Optional[str],
    last_validated_at: Optional[str] = None,
    validation_status: Optional[str] = None,
    last_error: Optional[str] = None,
) -> int:
    """Create or update a setting value with optional metadata.

    `settings` remains the canonical encrypted store for `claude_setup_token`.
    `user_settings` stores dashboard/runtime settings and token metadata.
    """
    value_to_store = _encrypt_setting_value(setting_key, setting_value)
    rows = execute(
        """INSERT INTO settings (key, value, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            updated_at = CURRENT_TIMESTAMP""",
        (setting_key, value_to_store),
    )

    if not _requires_encryption(setting_key):
        _upsert_user_setting(
            setting_key,
            setting_value,
            last_validated_at=last_validated_at,
            validation_status=validation_status,
            last_error=last_error,
        )

    return rows


def get_setting(setting_key: str, default: Optional[str] = None) -> Optional[str]:
    """Get a setting value, preferring user_settings and falling back to settings."""
    if not _requires_encryption(setting_key):
        row = query_one(
            "SELECT setting_value FROM user_settings WHERE setting_key = ?",
            (setting_key,),
        )
        if row is not None:
            return row["setting_value"]

    row = query_one("SELECT value FROM settings WHERE key = ?", (setting_key,))
    if row is None:
        return default
    return _decrypt_setting_value(setting_key, row["value"])


def get_setting_metadata(setting_key: str) -> Dict[str, Optional[str]]:
    """Get token validation metadata for a setting key."""
    row = query_one(
        """SELECT last_validated_at, validation_status, last_error
        FROM user_settings
        WHERE setting_key = ?""",
        (setting_key,),
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
    last_validated_at: Optional[str] = None,
) -> int:
    """Update token metadata for a setting key."""
    if last_validated_at is None:
        last_validated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    rows = execute(
        """UPDATE user_settings
        SET
            last_validated_at = ?,
            validation_status = ?,
            last_error = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE setting_key = ?""",
        (last_validated_at, validation_status, last_error, setting_key),
    )

    if rows == 0:
        return _upsert_user_setting(
            setting_key,
            get_setting(setting_key) or "",
            last_validated_at=last_validated_at,
            validation_status=validation_status,
            last_error=last_error,
        )
    return rows


def get_all_settings() -> Dict[str, Optional[str]]:
    """Get all settings merged from user_settings and encrypted settings."""
    user_rows = query(
        "SELECT setting_key, setting_value FROM user_settings ORDER BY setting_key"
    )
    merged: Dict[str, Optional[str]] = {
        row["setting_key"]: row["setting_value"] for row in user_rows
    }

    settings_rows = query("SELECT key, value FROM settings ORDER BY key")
    for row in settings_rows:
        key = row["key"]
        if key not in merged:
            merged[key] = _decrypt_setting_value(key, row["value"])

    return merged


def delete_setting(setting_key: str) -> int:
    """Delete a setting from both legacy and user_settings stores."""
    user_deleted = execute(
        "DELETE FROM user_settings WHERE setting_key = ?",
        (setting_key,),
    )
    settings_deleted = execute(
        "DELETE FROM settings WHERE key = ?",
        (setting_key,),
    )
    return user_deleted + settings_deleted


def get_settings_by_prefix(prefix: str) -> Dict[str, Optional[str]]:
    """Get settings that begin with a key prefix."""
    merged: Dict[str, Optional[str]] = {}

    user_rows = query(
        "SELECT setting_key, setting_value FROM user_settings WHERE setting_key LIKE ? ORDER BY setting_key",
        (f"{prefix}%",),
    )
    for row in user_rows:
        merged[row["setting_key"]] = row["setting_value"]

    settings_rows = query(
        "SELECT key, value FROM settings WHERE key LIKE ? ORDER BY key",
        (f"{prefix}%",),
    )
    for row in settings_rows:
        if row["key"] not in merged:
            merged[row["key"]] = _decrypt_setting_value(row["key"], row["value"])

    return merged


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
