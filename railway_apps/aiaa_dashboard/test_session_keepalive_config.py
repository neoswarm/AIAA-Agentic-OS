#!/usr/bin/env python3
"""
Session configuration tests for keepalive and idle-timeout behavior.
"""

import importlib.util
from pathlib import Path


def _load_config_module():
    """Load config.py fresh so class attributes pick up current env vars."""
    module_path = Path(__file__).with_name("config.py")
    spec = importlib.util.spec_from_file_location("aiaa_dashboard_config", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_session_defaults_use_sliding_keepalive_with_24h_idle_timeout(monkeypatch):
    """Default config enables request-based keepalive and a 24-hour idle timeout."""
    monkeypatch.delenv("SESSION_REFRESH_EACH_REQUEST", raising=False)
    monkeypatch.delenv("PERMANENT_SESSION_LIFETIME", raising=False)

    config_module = _load_config_module()
    config = config_module.Config

    assert config.SESSION_REFRESH_EACH_REQUEST is True
    assert config.PERMANENT_SESSION_LIFETIME_SECONDS == 86400
    assert int(config.PERMANENT_SESSION_LIFETIME.total_seconds()) == 86400


def test_session_keepalive_and_idle_timeout_are_env_configurable(monkeypatch):
    """Session keepalive/idle-timeout behavior follows environment overrides."""
    monkeypatch.setenv("SESSION_REFRESH_EACH_REQUEST", "false")
    monkeypatch.setenv("PERMANENT_SESSION_LIFETIME", "1800")

    config_module = _load_config_module()
    config = config_module.Config

    assert config.SESSION_REFRESH_EACH_REQUEST is False
    assert config.PERMANENT_SESSION_LIFETIME_SECONDS == 1800
    assert int(config.PERMANENT_SESSION_LIFETIME.total_seconds()) == 1800
