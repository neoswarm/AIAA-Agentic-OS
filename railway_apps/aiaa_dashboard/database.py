"""
AIAA Dashboard - Database Module
Thread-safe SQLite connection with migration support and helper functions.
"""

import sqlite3
import threading
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from contextlib import contextmanager

# Thread-local storage for connections
_thread_local = threading.local()

# Default DB path (Railway volume or local)
DB_PATH = Path(__file__).parent / "data" / "dashboard.db"


def set_db_path(path: str):
    """Set custom database path (call before init_db)."""
    global DB_PATH
    DB_PATH = Path(path)
    # Reset thread-local connection when switching database paths so tests
    # and app factories do not reuse a stale connection to another DB file.
    if hasattr(_thread_local, "connection"):
        try:
            _thread_local.connection.close()
        except Exception:
            pass
        delattr(_thread_local, "connection")


def get_db() -> sqlite3.Connection:
    """Get thread-safe database connection."""
    if not hasattr(_thread_local, "connection"):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # Enable JSON support and foreign keys
        conn.execute("PRAGMA foreign_keys = ON")
        _thread_local.connection = conn
    return _thread_local.connection


@contextmanager
def get_cursor():
    """Context manager for database cursor."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()


def init_db(app=None):
    """Initialize database, run migrations, and migrate legacy data."""
    # Ensure data directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    conn = get_db()
    migrations_dir = Path(__file__).parent / "migrations"
    
    # Run all migrations in order
    if migrations_dir.exists():
        migration_files = sorted(migrations_dir.glob("*.sql"))
        for migration_file in migration_files:
            migration_name = migration_file.name
            
            # Check if already applied
            try:
                cursor = conn.execute(
                    "SELECT 1 FROM migration_history WHERE migration_name = ?",
                    (migration_name,)
                )
                if cursor.fetchone():
                    continue  # Already applied
            except sqlite3.OperationalError:
                # migration_history table doesn't exist yet, first run
                pass
            
            # Apply migration
            with open(migration_file, 'r') as f:
                sql = f.read()
                # Strip comment-only lines before splitting
                cleaned_lines = []
                for line in sql.split('\n'):
                    stripped = line.strip()
                    if not stripped.startswith('--') and stripped:
                        cleaned_lines.append(line)
                cleaned_sql = '\n'.join(cleaned_lines)
                # Split on semicolons and execute each statement
                for statement in cleaned_sql.split(';'):
                    statement = statement.strip()
                    if statement:
                        try:
                            conn.execute(statement)
                        except sqlite3.OperationalError as exc:
                            if _should_normalize_user_settings(statement, exc):
                                _normalize_user_settings_schema(conn)
                                conn.execute(statement)
                            else:
                                raise
            conn.commit()
            print(f"Applied migration: {migration_name}")

    # Final guard: ensure runtime model expectations for user_settings columns.
    _normalize_user_settings_schema(conn)
    
    # Migrate legacy JSON files if they exist
    _migrate_legacy_workflow_config()
    _migrate_legacy_webhook_config()
    _migrate_legacy_cron_states()
    
    return conn


def _should_normalize_user_settings(statement: str, exc: Exception) -> bool:
    """Return True when user_settings schema should be normalized then retried."""
    msg = str(exc).lower()
    stmt = (statement or "").lower()
    return "user_settings" in stmt and (
        "no such column: setting_key" in msg
        or "no such column: setting_value" in msg
        or "no such column: key" in msg
        or "no such column: value" in msg
    )


def _normalize_user_settings_schema(conn: sqlite3.Connection):
    """Upgrade legacy user_settings table variants to the canonical schema."""
    table_row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='user_settings'"
    ).fetchone()
    if table_row is None:
        return

    columns = [row[1] for row in conn.execute("PRAGMA table_info(user_settings)").fetchall()]
    column_set = set(columns)

    # Legacy schema: key/value. Migrate to setting_key/setting_value.
    if "setting_key" not in column_set and {"key", "value"}.issubset(column_set):
        conn.execute("DROP TABLE IF EXISTS user_settings_v2")
        conn.execute(
            """
            CREATE TABLE user_settings_v2 (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL,
                last_validated_at TEXT,
                validation_status TEXT,
                last_error TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        updated_expr = "updated_at" if "updated_at" in column_set else "CURRENT_TIMESTAMP"
        conn.execute(
            f"""
            INSERT INTO user_settings_v2 (setting_key, setting_value, updated_at)
            SELECT key, value, {updated_expr}
            FROM user_settings
            """
        )
        conn.execute("DROP TABLE user_settings")
        conn.execute("ALTER TABLE user_settings_v2 RENAME TO user_settings")
        column_set = {
            "setting_key",
            "setting_value",
            "last_validated_at",
            "validation_status",
            "last_error",
            "updated_at",
        }

    # Ensure metadata columns exist for newer token validation features.
    if "setting_key" in column_set and "setting_value" in column_set:
        if "last_validated_at" not in column_set:
            conn.execute("ALTER TABLE user_settings ADD COLUMN last_validated_at TEXT")
            column_set.add("last_validated_at")
        if "validation_status" not in column_set:
            conn.execute("ALTER TABLE user_settings ADD COLUMN validation_status TEXT")
            column_set.add("validation_status")
        if "last_error" not in column_set:
            conn.execute("ALTER TABLE user_settings ADD COLUMN last_error TEXT")
            column_set.add("last_error")
        if "updated_at" not in column_set:
            conn.execute("ALTER TABLE user_settings ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            column_set.add("updated_at")

        conn.execute("CREATE INDEX IF NOT EXISTS idx_user_settings_key ON user_settings(setting_key)")


def _migrate_legacy_workflow_config():
    """Migrate workflow_config.json to workflows table."""
    config_path = Path(__file__).parent / "workflow_config.json"
    if not config_path.exists():
        return
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        workflows = config.get("workflows", {})
        project_id = config.get("project_id", "")
        
        with get_cursor() as cursor:
            for service_id, meta in workflows.items():
                if not meta.get("enabled", True):
                    continue
                
                cursor.execute("""
                    INSERT OR IGNORE INTO workflows (
                        id, name, description, type, status, cron_schedule, 
                        project_id, service_id, config
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    service_id,
                    meta.get("name", service_id),
                    meta.get("description", ""),
                    "cron",
                    "active",
                    None,  # Will be fetched from Railway
                    project_id,
                    service_id,
                    json.dumps(meta)
                ))
        
        print(f"Migrated {len(workflows)} workflows from workflow_config.json")
    except Exception as e:
        print(f"Error migrating workflow_config.json: {e}")


def _migrate_legacy_webhook_config():
    """Migrate webhook_config.json to workflows table."""
    config_path = Path(__file__).parent / "webhook_config.json"
    if not config_path.exists():
        return
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        webhooks = config.get("webhooks", {})
        
        with get_cursor() as cursor:
            for slug, meta in webhooks.items():
                cursor.execute("""
                    INSERT OR IGNORE INTO workflows (
                        id, name, description, type, status, webhook_slug, 
                        forward_url, slack_notify, config
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    f"webhook:{slug}",
                    meta.get("name", slug),
                    meta.get("description", ""),
                    "webhook",
                    "active" if meta.get("enabled", True) else "paused",
                    slug,
                    meta.get("forward_url", ""),
                    1 if meta.get("slack_notify", False) else 0,
                    json.dumps(meta)
                ))
        
        print(f"Migrated {len(webhooks)} webhooks from webhook_config.json")
    except Exception as e:
        print(f"Error migrating webhook_config.json: {e}")


def _migrate_legacy_cron_states():
    """Migrate cron_states.json to cron_states table."""
    states_path = Path(__file__).parent / "cron_states.json"
    if not states_path.exists():
        return
    
    try:
        with open(states_path, 'r') as f:
            states = json.load(f)
        
        with get_cursor() as cursor:
            for service_id, state in states.items():
                cursor.execute("""
                    INSERT OR REPLACE INTO cron_states (
                        service_id, active, original_cron, last_toggled_at
                    ) VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    service_id,
                    1 if state.get("active", True) else 0,
                    state.get("original_cron", "0 */3 * * *")
                ))
        
        print(f"Migrated {len(states)} cron states from cron_states.json")
    except Exception as e:
        print(f"Error migrating cron_states.json: {e}")


# ==============================================================================
# Query Helper Functions
# ==============================================================================

def query(sql: str, params: Tuple = ()) -> List[sqlite3.Row]:
    """Execute a SELECT query and return all rows."""
    with get_cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchall()


def query_one(sql: str, params: Tuple = ()) -> Optional[sqlite3.Row]:
    """Execute a SELECT query and return one row."""
    with get_cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchone()


def execute(sql: str, params: Tuple = ()) -> int:
    """Execute an INSERT/UPDATE/DELETE and return affected rows."""
    with get_cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.rowcount


def insert(sql: str, params: Tuple = ()) -> int:
    """Execute an INSERT and return the last row ID."""
    with get_cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.lastrowid


def executemany(sql: str, params_list: List[Tuple]) -> int:
    """Execute multiple statements and return total affected rows."""
    with get_cursor() as cursor:
        cursor.executemany(sql, params_list)
        return cursor.rowcount


# ==============================================================================
# JSON Helper Functions
# ==============================================================================

def row_to_dict(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
    """Convert sqlite3.Row to dictionary with JSON parsing."""
    if row is None:
        return None
    
    result = dict(row)
    
    # Parse JSON columns
    for key, value in result.items():
        if value and isinstance(value, str):
            # Try to parse as JSON
            if value.startswith('{') or value.startswith('['):
                try:
                    result[key] = json.loads(value)
                except (json.JSONDecodeError, ValueError):
                    pass
    
    return result


def rows_to_dicts(rows: List[sqlite3.Row]) -> List[Dict[str, Any]]:
    """Convert list of sqlite3.Row to list of dictionaries."""
    return [row_to_dict(row) for row in rows]


# ==============================================================================
# Transaction Support
# ==============================================================================

@contextmanager
def transaction():
    """Context manager for explicit transactions."""
    conn = get_db()
    try:
        conn.execute("BEGIN")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


# ==============================================================================
# Health Check
# ==============================================================================

def check_health() -> Dict[str, Any]:
    """Check database health and return stats."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get table counts
        stats = {}
        tables = ["workflows", "executions", "webhook_logs", "events", "api_keys"]
        
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                stats[table] = cursor.fetchone()[0]
            except sqlite3.OperationalError:
                stats[table] = 0
        
        # Get database size
        cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
        db_size = cursor.fetchone()[0]
        stats["db_size_bytes"] = db_size
        stats["db_size_mb"] = round(db_size / (1024 * 1024), 2)
        
        return {
            "status": "healthy",
            "path": str(DB_PATH),
            "stats": stats
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


# ==============================================================================
# Cleanup Functions
# ==============================================================================

def cleanup_old_events(days: int = 30):
    """Delete events older than N days."""
    with get_cursor() as cursor:
        cursor.execute("""
            DELETE FROM events 
            WHERE created_at < datetime('now', ? || ' days')
        """, (f'-{days}',))
        return cursor.rowcount


def cleanup_old_webhook_logs(days: int = 7):
    """Delete webhook logs older than N days."""
    with get_cursor() as cursor:
        cursor.execute("""
            DELETE FROM webhook_logs 
            WHERE received_at < datetime('now', ? || ' days')
        """, (f'-{days}',))
        return cursor.rowcount


def vacuum():
    """Vacuum database to reclaim space."""
    conn = get_db()
    conn.execute("VACUUM")
    conn.commit()
