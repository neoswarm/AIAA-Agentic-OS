from pathlib import Path


TEMPLATES_DIR = Path(__file__).parent / "templates"


def read_template(name: str) -> str:
    return (TEMPLATES_DIR / name).read_text(encoding="utf-8")


def test_skill_execute_has_runner_recovery_flow():
    html = read_template("skill_execute.html")

    assert "Runner still active" in html
    assert "aiaa.activeExecution" in html
    assert "restoreActiveExecutionIfRunning" in html
    assert html.count("persistActiveExecution(data.execution_id, skillName)") == 2
    assert "/executions/' + encodeURIComponent(activeExecution.executionId) + '/progress'" in html


def test_skill_progress_recovers_runner_after_reload():
    html = read_template("skill_progress.html")

    assert "Runner still active. Reconnected to live progress." in html
    assert "shouldShowReloadRecovery" in html
    assert "showReloadRecoveryBanner()" in html
    assert "clearActiveExecution();" in html
    assert "if (isTerminalExecutionStatus(data.status))" in html
