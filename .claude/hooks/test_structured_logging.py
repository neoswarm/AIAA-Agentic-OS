import importlib.util
from pathlib import Path


def _load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


HOOKS_DIR = Path(__file__).resolve().parent
session_activity_logger = _load_module(
    HOOKS_DIR / "session_activity_logger.py",
    "session_activity_logger_under_test",
)
execution_logger = _load_module(
    HOOKS_DIR / "execution_logger.py",
    "execution_logger_under_test",
)


def test_session_terminal_status_from_text_exit_code():
    status = session_activity_logger.parse_terminal_status("job failed with exit code 2")
    assert status["status"] == "error"
    assert status["exit_code"] == 2
    assert status["error_detected"] is True


def test_session_terminal_status_from_structured_result():
    status = session_activity_logger.parse_terminal_status(
        {"stdout": "all good", "stderr": "", "exit_code": 0}
    )
    assert status["status"] == "success"
    assert status["exit_code"] == 0
    assert status["error_detected"] is False


def test_session_build_log_entry_includes_structured_payloads():
    entry = session_activity_logger.build_log_entry(
        tool_name="Bash",
        command="python3 execution/generate_blog_post.py --topic test",
        tool_result="completed with exit code 0",
        timestamp="2026-02-24T00:00:00+00:00",
    )

    assert entry["event_type"] == "tool_event"
    assert entry["type"] == "workflow_execution"
    assert entry["command_summary"] == "execution/generate_blog_post.py"
    assert entry["tool_event"]["name"] == "Bash"
    assert entry["tool_event"]["category"] == "workflow_execution"
    assert entry["terminal_status"]["status"] == "success"


def test_execution_terminal_status_detects_error_signal():
    status = execution_logger.parse_terminal_status("Traceback: boom")
    assert status["status"] == "error"
    assert status["exit_code"] is None
    assert status["error_detected"] is True


def test_execution_build_log_entry_includes_tool_event_and_terminal_status():
    entry = execution_logger.build_log_entry(
        command="python3 execution/scrape_apify.py --arg value",
        tool_result="finished with exit code 1",
        tool_name="Bash",
        timestamp="2026-02-24T00:00:00+00:00",
    )

    assert entry["script_name"] == "scrape_apify.py"
    assert entry["event_type"] == "tool_event"
    assert entry["tool_event"]["name"] == "Bash"
    assert entry["tool_event"]["script_name"] == "scrape_apify.py"
    assert entry["terminal_status"]["status"] == "error"
    assert entry["exit_code"] == 1
    assert entry["success"] is False
