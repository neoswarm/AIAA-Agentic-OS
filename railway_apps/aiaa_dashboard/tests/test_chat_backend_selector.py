#!/usr/bin/env python3
"""Tests for chat backend selection and startup logging."""

from __future__ import annotations

import hashlib
import importlib
import sys
from pathlib import Path


DASHBOARD_DIR = Path(__file__).resolve().parents[1]
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_DIR))

from services.chat_backend import select_chat_backend


def _reload_app_module():
    if "app" in sys.modules:
        return importlib.reload(sys.modules["app"])
    import app

    return app


def test_select_chat_backend_defaults_to_sdk(monkeypatch):
    monkeypatch.delenv("CHAT_BACKEND", raising=False)

    backend, warning = select_chat_backend()

    assert backend == "sdk"
    assert warning is None


def test_select_chat_backend_accepts_gateway(monkeypatch):
    monkeypatch.setenv("CHAT_BACKEND", " GATEWAY ")

    backend, warning = select_chat_backend()

    assert backend == "gateway"
    assert warning is None


def test_select_chat_backend_invalid_value_falls_back_to_sdk(monkeypatch):
    monkeypatch.setenv("CHAT_BACKEND", "invalid-backend")

    backend, warning = select_chat_backend()

    assert backend == "sdk"
    assert warning is not None
    assert "Invalid CHAT_BACKEND='invalid-backend'" in warning


def test_create_app_logs_selected_chat_backend(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.setenv("DASHBOARD_USERNAME", "testadmin")
    monkeypatch.setenv(
        "DASHBOARD_PASSWORD_HASH", hashlib.sha256(b"testpass123").hexdigest()
    )
    monkeypatch.setenv("FLASK_SECRET_KEY", hashlib.sha256(b"chat-backend").hexdigest())
    monkeypatch.setenv("CHAT_TOKEN_ENCRYPTION_KEY", "x" * 32)
    monkeypatch.setenv("DB_PATH", str(tmp_path / "dashboard.db"))
    monkeypatch.setenv("CHAT_BACKEND", "gateway")

    app_module = _reload_app_module()
    capsys.readouterr()
    app = app_module.create_app()
    captured = capsys.readouterr()

    assert app.config["CHAT_BACKEND"] == "gateway"
    assert "Chat backend selected: gateway" in captured.out
