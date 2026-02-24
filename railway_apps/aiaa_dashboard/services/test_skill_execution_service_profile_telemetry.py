#!/usr/bin/env python3
"""Tests for profile telemetry recorded on skill runs."""

import sys
from pathlib import Path

# Add dashboard root for direct module imports.
sys.path.insert(0, str(Path(__file__).parent.parent))

from services import skill_execution_service as svc


class _ThreadStub:
    """Non-executing thread replacement for deterministic unit tests."""

    def __init__(self, target=None, args=None, daemon=None):
        self.target = target
        self.args = args or ()
        self.daemon = daemon

    def start(self):
        return None


def _make_skill_dir(tmp_path: Path, skill_name: str) -> None:
    skill_dir = tmp_path / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "run.py").write_text("print('ok')\n", encoding="utf-8")


def test_execute_skill_records_profile_used_telemetry(monkeypatch, tmp_path):
    skill_name = "telemetry-skill"
    _make_skill_dir(tmp_path, skill_name)

    monkeypatch.setattr(svc, "SKILLS_DIR", tmp_path)
    monkeypatch.setattr(svc, "parse_skill_md", lambda _: {"name": skill_name})
    monkeypatch.setattr(svc.threading, "Thread", _ThreadStub)

    captured = {}

    def fake_create_skill_execution(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(svc.models, "create_skill_execution", fake_create_skill_execution, raising=False)

    execution_id = svc.execute_skill(skill_name, {"client": "acme", "topic": "launch"})

    assert execution_id
    assert captured["skill_name"] == skill_name
    assert captured["params"] == {"client": "acme", "topic": "launch"}
    assert captured["telemetry"] == {"profile_used": "acme"}
    assert captured["profile_used"] == "acme"


def test_execute_skill_falls_back_for_legacy_model_signature(monkeypatch, tmp_path):
    skill_name = "legacy-skill"
    _make_skill_dir(tmp_path, skill_name)

    monkeypatch.setattr(svc, "SKILLS_DIR", tmp_path)
    monkeypatch.setattr(svc, "parse_skill_md", lambda _: {"name": skill_name})
    monkeypatch.setattr(svc.threading, "Thread", _ThreadStub)

    calls = []

    def legacy_create_skill_execution(execution_id, skill_name, params):
        calls.append(
            {
                "execution_id": execution_id,
                "skill_name": skill_name,
                "params": params,
            }
        )

    monkeypatch.setattr(svc.models, "create_skill_execution", legacy_create_skill_execution, raising=False)

    execution_id = svc.execute_skill(skill_name, {"client": "acme"})

    assert execution_id
    assert len(calls) == 1
    assert calls[0]["skill_name"] == skill_name
    assert calls[0]["params"] == {"client": "acme"}


def test_extract_profile_used_prefers_profile_fields():
    assert svc._extract_profile_used({"profile": "research", "client": "acme"}) == "research"
    assert svc._extract_profile_used({"client_profile": "acme", "client": "other"}) == "acme"
    assert svc._extract_profile_used({"client": "   "}) is None
    assert svc._extract_profile_used(None) is None
