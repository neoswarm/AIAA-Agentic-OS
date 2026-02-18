#!/usr/bin/env python3
"""
Hook 15: Checkpoint Enforcer
Type: PostToolUse on Write tool
Tier: Advisory (always allows)

Tracks all writes to .tmp/ directories and detects multi-step workflow
patterns. Validates that checkpoints are written in order and warns if
a step is written out of sequence (e.g., step 3 before step 2).

Supported patterns:
  - vsl_funnel_*: expects 01_research, 02_vsl_script, 03_sales_page, 04_email_sequence
  - cold_email_*: expects research, emails
  - Generic numbered: 01_, 02_, 03_, etc.

Protocol:
  - Reads JSON from stdin: {"tool_name": "Write", "tool_input": {...}, "tool_result": "..."}
  - Prints JSON to stdout: {"decision": "ALLOW"}
  - Warnings written to stderr
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


STATE_DIR = Path("/Users/lucasnolan/Agentic OS/.tmp/hooks")
CHECKPOINT_FILE = STATE_DIR / "checkpoints.json"
TMP_ROOT = "/Users/lucasnolan/Agentic OS/.tmp/"

# Known workflow patterns and their expected files
WORKFLOW_PATTERNS = {
    "vsl_funnel": {
        "match": r"vsl_funnel",
        "expected": ["01_research", "02_vsl_script", "03_sales_page", "04_email_sequence"],
    },
    "cold_email": {
        "match": r"cold_email",
        "expected": ["research", "emails"],
    },
}


def load_checkpoints():
    """Load checkpoint state."""
    try:
        if CHECKPOINT_FILE.exists():
            with open(CHECKPOINT_FILE, "r") as f:
                return json.load(f)
    except (json.JSONDecodeError, OSError):
        pass
    return {"projects": {}}


def save_checkpoints(data):
    """Save checkpoint state."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_project_name(file_path: str) -> str:
    """Extract project name from .tmp/ path."""
    # Path like: .tmp/vsl_funnel_acme/01_research.md
    # Project name: vsl_funnel_acme
    rel = file_path.split(".tmp/")[-1] if ".tmp/" in file_path else ""
    parts = rel.split("/")
    if len(parts) >= 2:
        return parts[0]
    return ""


def detect_workflow_type(project_name: str) -> dict:
    """Detect which workflow pattern this project matches."""
    for wf_name, wf_info in WORKFLOW_PATTERNS.items():
        if re.search(wf_info["match"], project_name):
            return {"name": wf_name, "expected": wf_info["expected"]}
    return None


def detect_step_number(filename: str) -> int:
    """Extract step number from filename like 01_research.md."""
    match = re.match(r'^(\d{2})_', filename)
    if match:
        return int(match.group(1))
    return -1


def get_expected_for_project(project_name: str, files_written: list) -> list:
    """Determine expected files for a project."""
    wf = detect_workflow_type(project_name)
    if wf:
        return wf["expected"]

    # Generic numbered pattern: detect from files already written
    numbered_files = []
    for fw in files_written:
        fname = os.path.basename(fw.get("file", ""))
        num = detect_step_number(fname)
        if num > 0:
            numbered_files.append(num)
    if numbered_files:
        max_num = max(numbered_files)
        return [f"{i:02d}_*" for i in range(1, max_num + 1)]

    return []


def check_missing_predecessors(project: dict, current_file: str) -> list:
    """Check if any predecessor steps are missing."""
    filename = os.path.basename(current_file)
    current_step = detect_step_number(filename)
    if current_step <= 1:
        return []

    files_written = project.get("files_written", [])
    written_steps = set()
    for fw in files_written:
        fname = os.path.basename(fw.get("file", ""))
        step = detect_step_number(fname)
        if step > 0:
            written_steps.add(step)

    missing = []
    for i in range(1, current_step):
        if i not in written_steps:
            missing.append(i)

    return missing


def compute_completion(project: dict) -> float:
    """Compute completion percentage."""
    expected = project.get("expected_files", [])
    written = project.get("files_written", [])
    if not expected:
        return 0.0
    written_basenames = set()
    for fw in written:
        fname = os.path.basename(fw.get("file", ""))
        # Strip extension and match against expected
        name_no_ext = os.path.splitext(fname)[0]
        written_basenames.add(name_no_ext)

    matched = 0
    for exp in expected:
        if exp.endswith("*"):
            prefix = exp[:-1]
            if any(wb.startswith(prefix) for wb in written_basenames):
                matched += 1
        elif exp in written_basenames:
            matched += 1

    return (matched / len(expected)) * 100 if expected else 0.0


def check_status():
    """Show active projects and their completion."""
    print("Checkpoint Enforcer - Status")
    print("=" * 50)
    data = load_checkpoints()
    projects = data.get("projects", {})

    if not projects:
        print("\nNo active projects tracked.")
        sys.exit(0)

    print(f"\nActive projects: {len(projects)}")
    for name, project in projects.items():
        files = project.get("files_written", [])
        expected = project.get("expected_files", [])
        completion = project.get("completion_percentage", 0)
        print(f"\n  Project: {name}")
        print(f"  Completion: {completion:.0f}%")
        print(f"  Expected: {expected}")
        print(f"  Written ({len(files)}):")
        for fw in files:
            print(f"    - {os.path.basename(fw.get('file', '?'))} ({fw.get('timestamp', '?')[:19]})")

    sys.exit(0)


def check_reset():
    """Clear checkpoint data."""
    print("Checkpoint Enforcer - Reset")
    if CHECKPOINT_FILE.exists():
        os.remove(CHECKPOINT_FILE)
        print("Checkpoint data cleared.")
    else:
        print("No checkpoint file to clear.")
    sys.exit(0)


def main():
    # Handle CLI flags
    if len(sys.argv) > 1:
        if sys.argv[1] == "--status":
            check_status()
        elif sys.argv[1] == "--reset":
            check_reset()

    # Read hook input from stdin
    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except (json.JSONDecodeError, Exception):
        print(json.dumps({"decision": "ALLOW"}))
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    if tool_name != "Write":
        print(json.dumps({"decision": "ALLOW"}))
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    # Only care about .tmp/ writes
    if TMP_ROOT not in file_path:
        print(json.dumps({"decision": "ALLOW"}))
        sys.exit(0)

    project_name = get_project_name(file_path)
    if not project_name:
        print(json.dumps({"decision": "ALLOW"}))
        sys.exit(0)

    # Load and update checkpoints
    checkpoints = load_checkpoints()
    projects = checkpoints.setdefault("projects", {})

    if project_name not in projects:
        projects[project_name] = {
            "files_written": [],
            "expected_files": [],
            "completion_percentage": 0,
        }

    project = projects[project_name]

    # Add this file
    filename = os.path.basename(file_path)
    entry = {
        "file": file_path,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Avoid duplicate entries for the same file
    existing_files = [fw.get("file") for fw in project["files_written"]]
    if file_path not in existing_files:
        project["files_written"].append(entry)

    # Update expected files
    expected = get_expected_for_project(project_name, project["files_written"])
    if expected:
        project["expected_files"] = expected

    # Compute completion
    project["completion_percentage"] = compute_completion(project)

    # Check for missing predecessors
    missing = check_missing_predecessors(project, file_path)
    if missing:
        missing_str = ", ".join(f"step {m:02d}" for m in missing)
        sys.stderr.write(
            f"\n[CHECKPOINT WARNING] Writing step {detect_step_number(filename):02d} "
            f"but missing predecessor(s): {missing_str}. "
            f"Ensure earlier steps are completed.\n\n"
        )

    save_checkpoints(checkpoints)

    print(json.dumps({"decision": "ALLOW"}))
    sys.exit(0)


if __name__ == "__main__":
    main()
