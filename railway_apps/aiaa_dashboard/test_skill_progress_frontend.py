from pathlib import Path


def test_skill_progress_uses_reconnect_backoff_script():
    template_path = Path(__file__).parent / "templates" / "skill_progress.html"
    content = template_path.read_text(encoding="utf-8")

    assert "reconnect_backoff.js" in content
    assert "getReconnectDelay" in content
    assert "scheduleNextPoll(delayMs)" in content
