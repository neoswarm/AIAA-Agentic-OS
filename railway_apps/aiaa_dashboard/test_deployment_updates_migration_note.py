from pathlib import Path


def test_migration_notes_include_default_backend_rollout_strategy():
    notes_path = Path(__file__).with_name("DEPLOYMENT_UPDATES.md")
    notes = notes_path.read_text(encoding="utf-8")

    assert "### Default Backend Rollout Strategy" in notes
    assert "no `REDIS_URL`" in notes
    assert "InMemoryChatStore" in notes
    assert "`REDIS_URL` set" in notes
    assert "RedisChatStore" in notes
    assert "rollback is immediate by unsetting it" in notes


def test_migration_notes_include_gateway_canary_and_triage_steps():
    notes_path = Path(__file__).with_name("DEPLOYMENT_UPDATES.md")
    notes = notes_path.read_text(encoding="utf-8")

    assert "### Gateway Rollout Staged Canary Checklist" in notes
    assert "Stage 0 (preflight)" in notes
    assert "Stage 1 (internal canary)" in notes
    assert "Stage 2 (limited production canary)" in notes
    assert "Stage 3 (full rollout)" in notes
    assert "runtime canary succeeding" in notes

    assert "### Gateway Rollout Failure Triage" in notes
    assert "switch `CHAT_BACKEND` back to `sdk`" in notes
    assert "401/403" in notes
    assert "5xx/timeouts" in notes
    assert "correlation ID" in notes
    assert "resume from Stage 1" in notes
