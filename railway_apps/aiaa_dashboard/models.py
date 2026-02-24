"""
AIAA Dashboard - Database Models
All database operations for workflows, events, webhooks, and executions.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
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
