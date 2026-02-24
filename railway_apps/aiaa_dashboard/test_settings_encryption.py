#!/usr/bin/env python3
"""Focused tests for encrypted-at-rest settings storage."""

import database
import models
import pytest


@pytest.fixture()
def isolated_db(tmp_path, monkeypatch):
    """Create a fresh SQLite DB with a stable encryption key."""
    monkeypatch.setenv("FLASK_SECRET_KEY", "test-flask-secret")
    database.set_db_path(str(tmp_path / "settings-test.db"))

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


def test_settings_table_exists_after_migration(isolated_db):
    """Migrations create the settings table."""
    row = database.query_one(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'settings'"
    )
    assert row is not None


def test_claude_setup_token_encrypted_at_rest(isolated_db):
    """claude_setup_token is encrypted in DB but readable via model helper."""
    original = "setup-token-abc123"
    models.set_setting("claude_setup_token", original)

    raw = database.query_one(
        "SELECT value FROM settings WHERE key = ?",
        ("claude_setup_token",),
    )
    assert raw is not None
    assert raw["value"] != original
    assert raw["value"].startswith("enc:v1:")
    assert models.get_setting("claude_setup_token") == original


def test_non_sensitive_setting_remains_plaintext(isolated_db):
    """Only claude_setup_token is encrypted; normal settings stay plain."""
    models.set_setting("pref.role", "marketer")
    raw = database.query_one(
        "SELECT value FROM settings WHERE key = ?",
        ("pref.role",),
    )
    assert raw is not None
    assert raw["value"] == "marketer"
