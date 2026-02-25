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
