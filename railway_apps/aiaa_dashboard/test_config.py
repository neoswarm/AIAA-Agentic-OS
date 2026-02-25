#!/usr/bin/env python3
"""
Configuration validation tests for chat token encryption settings.
"""

import importlib
import sys
from pathlib import Path

# Ensure local module imports resolve when running from repo root
sys.path.insert(0, str(Path(__file__).parent))


def _load_config_module():
    """Import and reload config module to pick up env var changes."""
    if "config" in sys.modules:
        return importlib.reload(sys.modules["config"])
    import config  # pylint: disable=import-outside-toplevel
    return config


def _build_config(monkeypatch, tmp_path, chat_key):
    """Create a Config class instance with controlled environment vars."""
    monkeypatch.setenv("DASHBOARD_PASSWORD_HASH", "a" * 64)
    monkeypatch.setenv("DB_PATH", str(tmp_path / "dashboard.db"))

    if chat_key is None:
        monkeypatch.delenv("CHAT_TOKEN_ENCRYPTION_KEY", raising=False)
    else:
        monkeypatch.setenv("CHAT_TOKEN_ENCRYPTION_KEY", chat_key)

    config_module = _load_config_module()
    return config_module.Config


def test_tracked_vars_include_chat_token_encryption_key(monkeypatch, tmp_path):
    config = _build_config(monkeypatch, tmp_path, "x" * 32)
    assert "CHAT_TOKEN_ENCRYPTION_KEY" in config.TRACKED_ENV_VARS


def test_validate_config_requires_chat_token_encryption_key(monkeypatch, tmp_path):
    config = _build_config(monkeypatch, tmp_path, None)
    validation = config.validate_config()

    assert validation["valid"] is False
    assert any(
        "CHAT_TOKEN_ENCRYPTION_KEY is not set" in issue
        for issue in validation["issues"]
    )


def test_validate_config_rejects_short_chat_token_encryption_key(monkeypatch, tmp_path):
    config = _build_config(monkeypatch, tmp_path, "too-short")
    validation = config.validate_config()

    assert validation["valid"] is False
    assert any(
        "CHAT_TOKEN_ENCRYPTION_KEY must be at least 32 characters long" in issue
        for issue in validation["issues"]
    )


def test_validate_config_accepts_valid_chat_token_encryption_key(monkeypatch, tmp_path):
    config = _build_config(monkeypatch, tmp_path, "x" * 32)
    validation = config.validate_config()

    assert validation["valid"] is True
    assert all("CHAT_TOKEN_ENCRYPTION_KEY" not in issue for issue in validation["issues"])
