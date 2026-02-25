#!/usr/bin/env python3
"""Unit tests for profile upsert service."""

import os
import sys
import tempfile
from pathlib import Path

import pytest
from flask import Flask

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import database
import models
from services.profile_service import ProfileServiceError, upsert_profile


@pytest.fixture
def app_context():
    if hasattr(database._thread_local, "connection"):
        database._thread_local.connection.close()
        del database._thread_local.connection

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test-secret-key"

    tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = tmp_db.name
    tmp_db.close()

    database.set_db_path(db_path)
    with app.app_context():
        database.init_db(app)
        yield

    if hasattr(database._thread_local, "connection"):
        database._thread_local.connection.close()
        del database._thread_local.connection

    try:
        os.unlink(db_path)
    except OSError:
        pass


def test_upsert_profile_creates_new_record(app_context):
    result = upsert_profile(
        {
            "name": "Nova Labs",
            "website": "https://nova.example",
            "preferences": {"tone": "friendly"},
        }
    )
    assert result["action"] == "created"
    assert result["slug"] == "nova-labs"
    created = models.get_client_profile("nova-labs")
    assert created is not None
    assert created["name"] == "Nova Labs"


def test_upsert_profile_updates_existing_record(app_context):
    models.create_client_profile(name="Nova Labs", slug="nova-labs", industry="Old")

    result = upsert_profile({"slug": "nova-labs", "industry": "SaaS"})
    assert result["action"] == "updated"
    updated = models.get_client_profile("nova-labs")
    assert updated["industry"] == "SaaS"


def test_upsert_profile_validates_required_identity(app_context):
    with pytest.raises(ProfileServiceError) as exc_info:
        upsert_profile({"website": "https://nova.example"})

    assert exc_info.value.status_code == 400
    assert "slug" in exc_info.value.errors
