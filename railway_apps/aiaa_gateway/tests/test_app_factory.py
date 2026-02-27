"""Tests for the AIAA Gateway app factory scaffold."""

from datetime import datetime
from pathlib import Path
import sys

from flask import Flask


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from aiaa_gateway import create_app


def test_create_app_returns_flask_instance():
    app = create_app({"TESTING": True})

    assert isinstance(app, Flask)
    assert app.config["SERVICE_NAME"] == "aiaa_gateway"


def test_create_app_allows_config_override():
    app = create_app({"TESTING": True, "SERVICE_NAME": "custom_gateway"})

    assert app.config["SERVICE_NAME"] == "custom_gateway"


def test_health_endpoint_uses_factory_config():
    app = create_app({"TESTING": True, "SERVICE_NAME": "test_gateway"})
    client = app.test_client()

    response = client.get("/health")
    payload = response.get_json()

    assert response.status_code == 200
    assert set(payload) >= {"service", "status", "timestamp"}
    assert payload["status"] == "healthy"
    assert payload["service"] == "test_gateway"


def test_health_endpoint_emits_iso8601_utc_timestamp():
    app = create_app({"TESTING": True})
    client = app.test_client()

    response = client.get("/health")
    payload = response.get_json()

    assert response.status_code == 200
    timestamp = payload["timestamp"]
    parsed = datetime.fromisoformat(timestamp)
    assert parsed.tzinfo is not None
