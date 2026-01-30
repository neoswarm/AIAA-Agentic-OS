# Starter Hooks - Ready to Download

Copy these hooks to your `.claude/hooks/` folder and register them in `.claude/settings.local.json`.

---

## Hook 1: Agent Limiter (Essential)

**What it does:** Stops Claude from launching too many tasks at once (prevents crashes)

**File:** `.claude/hooks/agent_limiter.py`

```python
#!/usr/bin/env python3
"""
Agent Limiter Hook - Prevents launching too many tasks at once.

Exit codes:
  0 = Allow
  2 = Block
"""
import json
import sys
from pathlib import Path
from datetime import datetime

STATE_FILE = Path(".tmp/active_agents.json")
MAX_AGENTS = 5  # Adjust based on your needs

def load_state():
    """Load list of active agents."""
    if not STATE_FILE.exists():
        return {"active": []}
    try:
        return json.loads(STATE_FILE.read_text())
    except:
        return {"active": []}

def save_state(state):
    """Save list of active agents."""
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))

def cleanup_old_agents(state):
    """Remove agents older than 30 minutes (likely finished)."""
    from datetime import timedelta
    now = datetime.now()
    active = []

    for agent in state.get("active", []):
        try:
            started = datetime.fromisoformat(agent["started"])
            age_minutes = (now - started).total_seconds() / 60
            if age_minutes < 30:
                active.append(agent)
        except:
            pass

    state["active"] = active
    return state

def main():
    # CLI mode
    if len(sys.argv) > 1:
        if sys.argv[1] == "--status":
            state = load_state()
            state = cleanup_old_agents(state)
            print(f"\n[AGENT LIMITER]")
            print(f"Active agents: {len(state['active'])} / {MAX_AGENTS}")
            if state['active']:
                print("\nActive:")
                for agent in state['active']:
                    print(f"  - {agent['description'][:50]} ({agent['started']})")
            return 0

        if sys.argv[1] == "--reset":
            save_state({"active": []})
            print("State reset.")
            return 0

    # Hook mode
    try:
        hook_input = json.load(sys.stdin)
    except:
        sys.exit(0)

    tool_name = hook_input.get("tool_name", "")

    # Only check Task tool
    if tool_name != "Task":
        sys.exit(0)

    # Load state
    state = load_state()
    state = cleanup_old_agents(state)

    # Check limit
    if len(state["active"]) >= MAX_AGENTS:
        sys.stderr.write(f"""
[BLOCKED] Agent limit exceeded!

Active: {len(state['active'])} / {MAX_AGENTS}

TO PROCEED:
  1. Collect outputs from existing agents (TaskOutput)
  2. OR wait for agents to complete
  3. OR use run_in_background: true

Check status: py .claude/hooks/agent_limiter.py --status
Reset: py .claude/hooks/agent_limiter.py --reset
""")
        sys.exit(2)  # BLOCK

    # Register new agent
    tool_input = hook_input.get("tool_input", {})
    state["active"].append({
        "description": tool_input.get("description", "unknown"),
        "started": datetime.now().isoformat()
    })
    save_state(state)

    sys.exit(0)  # ALLOW

if __name__ == "__main__":
    sys.exit(main() or 0)
```

**Register in `.claude/settings.local.json`:**
```json
{
  "hooks": {
    "PreToolUse": [
      {"tool": "Task", "command": "py .claude/hooks/agent_limiter.py"}
    ]
  }
}
```

---

## Hook 2: Context Budget Guard (Essential)

**What it does:** Warns when context is filling up, blocks at 85%

**File:** `.claude/hooks/context_budget_guard.py`

```python
#!/usr/bin/env python3
"""
Context Budget Guard - Prevents context overflow.

Exit codes:
  0 = Allow (with optional warning)
  2 = Block
"""
import json
import sys
from pathlib import Path

WARN_THRESHOLD = 0.60   # 60%
HIGH_THRESHOLD = 0.75   # 75%
BLOCK_THRESHOLD = 0.85  # 85%

STATE_FILE = Path(".tmp/active_agents.json")
BASE_CONTEXT = 50000     # Estimated base tokens
AGENT_OUTPUT_AVG = 5000  # Estimated per-agent tokens

def count_active_agents():
    """Count active agents."""
    if not STATE_FILE.exists():
        return 0
    try:
        state = json.loads(STATE_FILE.read_text())
        return len(state.get("active", []))
    except:
        return 0

def estimate_usage():
    """Estimate context usage as percentage."""
    active = count_active_agents()
    estimated_tokens = BASE_CONTEXT + (active * AGENT_OUTPUT_AVG)
    percentage = estimated_tokens / 200000
    return percentage, active

def main():
    # CLI mode
    if len(sys.argv) > 1 and sys.argv[1] == "--status":
        pct, active = estimate_usage()
        print(f"\n[CONTEXT BUDGET]")
        print(f"Estimated usage: {pct*100:.1f}%")
        print(f"Active agents: {active}")
        print(f"\nThresholds:")
        print(f"  WARN at: {WARN_THRESHOLD*100:.0f}%")
        print(f"  HIGH at: {HIGH_THRESHOLD*100:.0f}%")
        print(f"  BLOCK at: {BLOCK_THRESHOLD*100:.0f}%")
        return 0

    # Hook mode
    try:
        hook_input = json.load(sys.stdin)
    except:
        sys.exit(0)

    tool_name = hook_input.get("tool_name", "")

    # Only check Task, TaskOutput, Read
    if tool_name not in ["Task", "TaskOutput", "Read"]:
        sys.exit(0)

    pct, active = estimate_usage()

    # Block at critical threshold (only for new agents)
    if pct >= BLOCK_THRESHOLD and tool_name == "Task":
        sys.stderr.write(f"""
[BLOCKED] Context budget at {pct*100:.0f}%

Active agents: {active}
Checkpoint required before launching more agents.

TO PROCEED:
  1. Collect existing outputs
  2. Summarize findings
  3. Start new session if needed
""")
        sys.exit(2)  # BLOCK

    # Warn at high threshold
    if pct >= HIGH_THRESHOLD:
        sys.stderr.write(f"\n[WARNING] Context at {pct*100:.0f}%. Consider summarizing.\n")

    # Info at moderate threshold
    elif pct >= WARN_THRESHOLD:
        sys.stderr.write(f"\n[INFO] Context at {pct*100:.0f}%. Monitor usage.\n")

    sys.exit(0)  # ALLOW

if __name__ == "__main__":
    sys.exit(main() or 0)
```

**Register:**
```json
{
  "hooks": {
    "PreToolUse": [
      {"tool": "Task", "command": "py .claude/hooks/agent_limiter.py"},
      {"tool": "Task", "command": "py .claude/hooks/context_budget_guard.py"}
    ]
  }
}
```

---

## Hook 3: Output Quality Gate (Recommended)

**What it does:** Validates files meet minimum quality standards (word count, sections, etc.)

**File:** `.claude/hooks/output_quality_gate.py`

```python
#!/usr/bin/env python3
"""
Output Quality Gate - Validates deliverable quality.

PostToolUse hook for Write tool.
"""
import json
import sys
import re
from pathlib import Path

# Customize these for your deliverables
QUALITY_RULES = {
    "*.md": {
        "min_words": 500,
        "min_sections": 3,
        "required_keywords": []  # e.g., ["Introduction", "Conclusion"]
    },
    "*_report.md": {
        "min_words": 2000,
        "min_sections": 5,
        "required_keywords": ["Summary", "Recommendations"]
    }
}

def count_words(content):
    """Count words in content."""
    text = re.sub(r'[#*_`\[\]()>-]', ' ', content)
    return len(text.split())

def count_sections(content):
    """Count markdown headers."""
    headers = re.findall(r'^#{1,6}\s+.+$', content, re.MULTILINE)
    return len(headers)

def check_keywords(content, keywords):
    """Check if keywords present."""
    content_lower = content.lower()
    missing = []
    for keyword in keywords:
        if keyword.lower() not in content_lower:
            missing.append(keyword)
    return missing

def get_rules(file_path):
    """Get quality rules for file."""
    from fnmatch import fnmatch
    for pattern, rules in QUALITY_RULES.items():
        if fnmatch(Path(file_path).name, pattern):
            return rules
    return None

def main():
    # Hook mode only (no CLI)
    try:
        input_data = json.load(sys.stdin)
    except:
        print(json.dumps({"decision": "ALLOW"}))
        return

    tool_name = input_data.get("tool_name", "")

    # Only check Write
    if tool_name != "Write":
        print(json.dumps({"decision": "ALLOW"}))
        return

    tool_input = input_data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    content = tool_input.get("content", "")

    # Get rules for this file
    rules = get_rules(file_path)
    if not rules:
        print(json.dumps({"decision": "ALLOW"}))
        return

    # Check quality
    issues = []

    word_count = count_words(content)
    if word_count < rules.get("min_words", 0):
        issues.append(f"Word count {word_count} < {rules['min_words']} minimum")

    section_count = count_sections(content)
    if section_count < rules.get("min_sections", 0):
        issues.append(f"Section count {section_count} < {rules['min_sections']} minimum")

    missing_keywords = check_keywords(content, rules.get("required_keywords", []))
    if missing_keywords:
        issues.append(f"Missing keywords: {', '.join(missing_keywords)}")

    if issues:
        msg = f"[BLOCKED] Quality check failed for {Path(file_path).name}\n\n"
        msg += "Issues:\n"
        for issue in issues:
            msg += f"  - {issue}\n"
        msg += "\nFix these issues and try again."

        print(json.dumps({
            "decision": "BLOCK",
            "reason": msg
        }))
        return

    print(json.dumps({"decision": "ALLOW"}))

if __name__ == "__main__":
    main()
```

**Register:**
```json
{
  "hooks": {
    "PostToolUse": [
      {"tool": "Write", "command": "py .claude/hooks/output_quality_gate.py"}
    ]
  }
}
```

---

## Hook 4: Large File Read Blocker (Recommended)

**What it does:** Prevents reading huge files that flood context

**File:** `.claude/hooks/large_file_read_blocker.py`

```python
#!/usr/bin/env python3
"""
Large File Read Blocker - Prevents reading huge files when agents are active.

Exit codes:
  0 = Allow
  2 = Block
"""
import json
import sys
from pathlib import Path

MAX_LINES = 300  # Block files larger than this
STATE_FILE = Path(".tmp/active_agents.json")

def count_active_agents():
    """Count active agents."""
    if not STATE_FILE.exists():
        return 0
    try:
        state = json.loads(STATE_FILE.read_text())
        return len(state.get("active", []))
    except:
        return 0

def count_file_lines(file_path):
    """Count lines in file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return sum(1 for _ in f)
    except:
        return 0

def main():
    # Hook mode
    try:
        hook_input = json.load(sys.stdin)
    except:
        sys.exit(0)

    tool_name = hook_input.get("tool_name", "")

    # Only check Read
    if tool_name != "Read":
        sys.exit(0)

    # Check if agents are active
    active = count_active_agents()
    if active == 0:
        sys.exit(0)  # No agents, allow any read

    # Check file size
    tool_input = hook_input.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    if not file_path or not Path(file_path).exists():
        sys.exit(0)  # File doesn't exist, let Read tool handle it

    line_count = count_file_lines(file_path)

    if line_count > MAX_LINES:
        sys.stderr.write(f"""
[BLOCKED] Large file read while agents active

File: {Path(file_path).name}
Lines: {line_count} (max {MAX_LINES} when agents active)
Active agents: {active}

WHY: Reading large files with agents active floods context.

TO PROCEED:
  1. Collect agent outputs first
  2. OR use Grep to search for specific content
  3. OR read file in chunks with offset/limit

Example: Use Grep instead
  Grep(pattern="function_name", path="{file_path}")
""")
        sys.exit(2)  # BLOCK

    sys.exit(0)  # ALLOW

if __name__ == "__main__":
    sys.exit(main() or 0)
```

**Register:**
```json
{
  "hooks": {
    "PreToolUse": [
      {"tool": "Task", "command": "py .claude/hooks/agent_limiter.py"},
      {"tool": "Task", "command": "py .claude/hooks/context_budget_guard.py"},
      {"tool": "Read", "command": "py .claude/hooks/large_file_read_blocker.py"}
    ]
  }
}
```

---

## Complete Settings File

**File:** `.claude/settings.local.json`

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "tool": "Task",
        "command": "py .claude/hooks/agent_limiter.py"
      },
      {
        "tool": "Task",
        "command": "py .claude/hooks/context_budget_guard.py"
      },
      {
        "tool": "Read",
        "command": "py .claude/hooks/large_file_read_blocker.py"
      }
    ],
    "PostToolUse": [
      {
        "tool": "Write",
        "command": "py .claude/hooks/output_quality_gate.py"
      }
    ]
  }
}
```

---

## Testing Your Hooks

```bash
# 1. Test agent limiter
py .claude/hooks/agent_limiter.py --status

# 2. Test context budget
py .claude/hooks/context_budget_guard.py --status

# 3. Try launching 6 tasks (should block at 5)
# Claude will be stopped by agent_limiter.py

# 4. Try reading a huge file with agents active
# Should be blocked by large_file_read_blocker.py
```

---

## Customization Tips

### Adjust Agent Limit
```python
# In agent_limiter.py
MAX_AGENTS = 3  # Change to 3, 5, or 10 based on your machine
```

### Adjust Context Thresholds
```python
# In context_budget_guard.py
WARN_THRESHOLD = 0.50   # Warn earlier
BLOCK_THRESHOLD = 0.80  # Block earlier
```

### Add Custom Quality Rules
```python
# In output_quality_gate.py
QUALITY_RULES = {
    "*_vsl.md": {
        "min_words": 3000,
        "min_sections": 10,
        "required_keywords": ["Hook", "Problem", "Solution", "CTA"]
    },
    "*_email.md": {
        "min_words": 500,
        "min_sections": 3,
        "required_keywords": ["Subject", "Body", "CTA"]
    }
}
```

---

## Quick Start Checklist

- [ ] Create `.claude/hooks/` folder
- [ ] Copy 4 hook files
- [ ] Create `.claude/settings.local.json`
- [ ] Test with `--status` commands
- [ ] Try launching multiple tasks (should stop at 5)
- [ ] Customize quality rules for your files

---

**Need Help?**

Each hook has `--status` and `--reset` commands:
```bash
py .claude/hooks/agent_limiter.py --status
py .claude/hooks/agent_limiter.py --reset
```

**Made Simple by OJay Media | January 2026**
