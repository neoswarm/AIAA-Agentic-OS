#!/usr/bin/env python3
"""Tests for setup-token profile schema and model helpers."""

import database
import models
import pytest


@pytest.fixture()
def isolated_db(tmp_path, monkeypatch):
    """Create a fresh SQLite DB with a stable encryption key."""
    monkeypatch.setenv("FLASK_SECRET_KEY", "setup-token-profile-secret")
    database.set_db_path(str(tmp_path / "setup-token-profiles.db"))

    conn = getattr(database._thread_local, "connection", None)
    if conn is not None:
        conn.close()
        delattr(database._thread_local, "connection")

    database.init_db()
    yield

    conn = getattr(database._thread_local, "connection", None)
    if conn is not None:
        conn.close()
        delattr(database._thread_local, "connection")


def test_setup_token_profiles_table_exists_after_migration(isolated_db):
    """Migrations create setup_token_profiles table."""
    row = database.query_one(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'setup_token_profiles'"
    )
    assert row is not None


def test_set_setting_persists_default_profile_with_encrypted_token(isolated_db):
    """Saving claude_setup_token creates/updates the default setup-token profile."""
    original = "setup-token-abc123"
    models.set_setting("claude_setup_token", original)

    raw = database.query_one(
        "SELECT profile_id, encrypted_token, status, created_at, updated_at "
        "FROM setup_token_profiles WHERE profile_id = ?",
        ("default",),
    )
    assert raw is not None
    assert raw["profile_id"] == "default"
    assert raw["encrypted_token"] != original
    assert raw["encrypted_token"].startswith("enc:v1:")
    assert raw["status"] == "active"
    assert raw["created_at"] is not None
    assert raw["updated_at"] is not None

    profile = models.get_setup_token_profile("default")
    assert profile is not None
    assert profile["profile_id"] == "default"
    assert profile["token"] == original
    assert profile["status"] == "active"


def test_namespaced_setup_token_setting_maps_to_profile_id(isolated_db):
    """Namespaced setup-token keys map cleanly to profile_id rows."""
    models.set_setting("student-a.claude_setup_token", "token-value-1")

    profile = models.get_setup_token_profile("student-a")
    assert profile is not None
    assert profile["profile_id"] == "student-a"
    assert profile["token"] == "token-value-1"
    assert profile["status"] == "active"


def test_delete_setting_marks_setup_token_profile_revoked(isolated_db):
    """Deleting setup token keys revokes the associated profile record."""
    models.set_setting("student-b.claude_setup_token", "token-value-2")
    models.delete_setting("student-b.claude_setup_token")

    profile = models.get_setup_token_profile("student-b")
    assert profile is not None
    assert profile["token"] == ""
    assert profile["status"] == "revoked"
