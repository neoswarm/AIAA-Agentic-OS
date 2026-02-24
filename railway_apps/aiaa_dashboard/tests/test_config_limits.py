#!/usr/bin/env python3
"""Tests for configurable dashboard limits in config.py."""

import importlib
import sys
from pathlib import Path


DASHBOARD_DIR = Path(__file__).resolve().parents[1]
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_DIR))


def _reload_config_module():
    if "config" in sys.modules:
        return importlib.reload(sys.modules["config"])
    import config

    return config


def test_limit_defaults(monkeypatch):
    """Config should expose sensible defaults for common limits."""
    limit_env_vars = [
        "DEFAULT_RECENT_WORKFLOWS_LIMIT",
        "DEFAULT_EXECUTIONS_LIMIT",
        "DEFAULT_EVENTS_LIMIT",
        "DEFAULT_OUTPUTS_LIMIT",
        "DEFAULT_RECENT_SKILL_EXECUTIONS_LIMIT",
        "DEFAULT_RECOMMENDED_SKILLS_LIMIT",
        "MAX_RECOMMENDED_SKILLS_LIMIT",
        "MAX_EXECUTIONS_LIMIT",
        "DEFAULT_DEPLOYMENTS_LIMIT",
        "SKILL_EXECUTION_TIMEOUT_SECONDS",
        "GOOGLE_DOC_DELIVERY_TIMEOUT_SECONDS",
    ]
    for var in limit_env_vars:
        monkeypatch.delenv(var, raising=False)

    config_module = _reload_config_module()
    cfg = config_module.Config

    assert cfg.DEFAULT_RECENT_WORKFLOWS_LIMIT == 5
    assert cfg.DEFAULT_EXECUTIONS_LIMIT == 50
    assert cfg.DEFAULT_EVENTS_LIMIT == 100
    assert cfg.DEFAULT_OUTPUTS_LIMIT == 50
    assert cfg.DEFAULT_RECENT_SKILL_EXECUTIONS_LIMIT == 10
    assert cfg.DEFAULT_RECOMMENDED_SKILLS_LIMIT == 8
    assert cfg.MAX_RECOMMENDED_SKILLS_LIMIT == 20
    assert cfg.MAX_EXECUTIONS_LIMIT == 200
    assert cfg.DEFAULT_DEPLOYMENTS_LIMIT == 50
    assert cfg.SKILL_EXECUTION_TIMEOUT_SECONDS == 600
    assert cfg.GOOGLE_DOC_DELIVERY_TIMEOUT_SECONDS == 60


def test_limit_overrides_from_environment(monkeypatch):
    """Config limits should be overridable via environment variables."""
    monkeypatch.setenv("DEFAULT_EXECUTIONS_LIMIT", "75")
    monkeypatch.setenv("MAX_EXECUTIONS_LIMIT", "150")
    monkeypatch.setenv("DEFAULT_RECOMMENDED_SKILLS_LIMIT", "12")
    monkeypatch.setenv("MAX_RECOMMENDED_SKILLS_LIMIT", "30")
    monkeypatch.setenv("SKILL_EXECUTION_TIMEOUT_SECONDS", "900")
    monkeypatch.setenv("GOOGLE_DOC_DELIVERY_TIMEOUT_SECONDS", "90")

    config_module = _reload_config_module()
    cfg = config_module.Config

    assert cfg.DEFAULT_EXECUTIONS_LIMIT == 75
    assert cfg.MAX_EXECUTIONS_LIMIT == 150
    assert cfg.DEFAULT_RECOMMENDED_SKILLS_LIMIT == 12
    assert cfg.MAX_RECOMMENDED_SKILLS_LIMIT == 30
    assert cfg.SKILL_EXECUTION_TIMEOUT_SECONDS == 900
    assert cfg.GOOGLE_DOC_DELIVERY_TIMEOUT_SECONDS == 90
