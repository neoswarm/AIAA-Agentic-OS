#!/usr/bin/env python3
"""
Tests for skill execution latency metrics.
"""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import database
import models


@pytest.fixture()
def isolated_db(tmp_path):
    """Initialize a fresh SQLite database per test."""
    if hasattr(database._thread_local, "connection"):
        database._thread_local.connection.close()
        delattr(database._thread_local, "connection")

    db_path = tmp_path / "latency_metrics.db"
    database.set_db_path(str(db_path))
    database.init_db()

    yield

    if hasattr(database._thread_local, "connection"):
        database._thread_local.connection.close()
        delattr(database._thread_local, "connection")


def test_skill_execution_lifecycle_records_latency_metrics(isolated_db):
    execution_id = "exec-latency-1"
    models.create_skill_execution(execution_id, "blog-post", {"topic": "latency"})

    database.execute(
        "UPDATE skill_executions SET created_at = datetime('now', '-5 seconds') WHERE id = ?",
        (execution_id,),
    )

    models.update_skill_execution_status(execution_id, "running")
    running = models.get_skill_execution(execution_id)
    assert running["status"] == "running"
    assert running["queue_wait_ms"] is not None
    assert running["queue_wait_ms"] >= 4000
    assert running["first_token_ms"] is None

    models.update_skill_execution_status(
        execution_id,
        "running",
        output_preview="First output line",
    )
    with_first_token = models.get_skill_execution(execution_id)
    assert with_first_token["first_token_ms"] is not None
    assert with_first_token["first_token_ms"] >= with_first_token["queue_wait_ms"]

    models.update_skill_execution_status(
        execution_id,
        "success",
        output_preview="Completed output",
    )
    completed = models.get_skill_execution(execution_id)
    assert completed["status"] == "success"
    assert completed["duration_ms"] is not None
    assert completed["total_runtime_ms"] is not None
    assert completed["total_runtime_ms"] >= completed["first_token_ms"]


def test_first_token_latency_is_only_recorded_once(isolated_db):
    execution_id = "exec-latency-2"
    models.create_skill_execution(execution_id, "newsletter", {"topic": "timing"})

    database.execute(
        "UPDATE skill_executions SET created_at = datetime('now', '-10 seconds') WHERE id = ?",
        (execution_id,),
    )

    models.update_skill_execution_status(execution_id, "running", output_preview="token-1")
    first_record = models.get_skill_execution(execution_id)["first_token_ms"]
    assert first_record is not None

    # If first-token latency is already set, later updates must not overwrite it.
    database.execute(
        "UPDATE skill_executions SET created_at = datetime('now', '-30 seconds') WHERE id = ?",
        (execution_id,),
    )
    models.update_skill_execution_status(execution_id, "running", output_preview="token-2")
    second_record = models.get_skill_execution(execution_id)["first_token_ms"]
    assert second_record == first_record


def test_execution_stats_include_latency_aggregates(isolated_db):
    database.insert(
        """INSERT INTO skill_executions (
            id, skill_name, status, queue_wait_ms, first_token_ms, total_runtime_ms, duration_ms
        ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
        ("stats-1", "blog-post", "success", 100, 200, 1000, 900),
    )
    database.insert(
        """INSERT INTO skill_executions (
            id, skill_name, status, queue_wait_ms, first_token_ms, total_runtime_ms, duration_ms
        ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
        ("stats-2", "blog-post", "error", 300, None, 1500, 1200),
    )

    stats = models.get_skill_execution_stats()
    assert stats["total_executions"] == 2
    assert stats["by_status"]["success"] == 1
    assert stats["by_status"]["error"] == 1
    assert stats["avg_queue_wait_ms"] == 200
    assert stats["avg_first_token_ms"] == 200
    assert stats["avg_total_runtime_ms"] == 1250
    assert stats["top_skills"]["blog-post"] == 2
