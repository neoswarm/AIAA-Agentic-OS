#!/usr/bin/env python3
"""
Hook 109: project_scope_guard.py (PreToolUse on Bash)
Purpose: Prevent scope creep beyond defined project boundaries.
Logic: When client context is active, check if the current operation matches
the project scope defined in the client profile. Warn if executing workflows
not in scope.

Protocol:
  - PreToolUse: reads JSON from stdin, exits 0 (allow) or 2 (block)
  - Messages to user via sys.stderr.write()
  - Supports --status and --reset CLI flags
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "project_scope.json"

# Common workflow categories for scope matching
WORKFLOW_CATEGORIES = {
    "vsl": ["vsl_funnel", "vsl_script", "generate_vsl"],
    "email": ["cold_email", "email_sequence", "email_campaign", "write_cold_emails"],
    "content": ["blog_post", "linkedin_post", "newsletter", "social_media"],
    "research": ["research_company", "research_market", "research_prospect"],
    "funnel": ["funnel_copy", "sales_page", "landing_page"],
    "advertising": ["ad_copy", "facebook_ads", "google_ads"],
    "seo": ["seo_audit", "keyword_research", "seo_content"],
    "branding": ["brand_voice", "brand_guide", "logo"],
    "consulting": ["strategy", "audit", "proposal"],
    "scraping": ["scrape_linkedin", "scrape_website", "lead_scraping"],
}


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "active_client": None,
        "client_scopes": {},
        "scope_warnings": [],
        "total_checks": 0,
        "total_warnings": 0
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def load_client_scope(client_name):
    """Try to load scope from client profile."""
    profile_paths = [
        Path(f"clients/{client_name}/profile.md"),
        Path(f"clients/{client_name}/scope.md"),
        Path(f"clients/{client_name}/rules.md"),
    ]

    scope_keywords = []
    for profile_path in profile_paths:
        if profile_path.exists():
            try:
                content = profile_path.read_text().lower()
                # Look for scope/service indicators
                for category, keywords in WORKFLOW_CATEGORIES.items():
                    for keyword in keywords:
                        if keyword.replace("_", " ") in content or keyword in content:
                            if category not in scope_keywords:
                                scope_keywords.append(category)
            except OSError:
                pass

    return scope_keywords if scope_keywords else None


def detect_workflow_category(command):
    """Detect the workflow category from a command."""
    command_lower = command.lower()
    for category, keywords in WORKFLOW_CATEGORIES.items():
        for keyword in keywords:
            if keyword in command_lower:
                return category
    return None


def detect_client_from_context(state):
    """Get active client from state or context isolation hook."""
    # Check our own state first
    if state.get("active_client"):
        return state["active_client"]

    # Check context isolation hook state
    isolation_state_file = STATE_DIR / "client_context_isolation.json"
    if isolation_state_file.exists():
        try:
            isolation_state = json.loads(isolation_state_file.read_text())
            return isolation_state.get("active_client")
        except (json.JSONDecodeError, OSError):
            pass

    return None


def show_status():
    state = load_state()
    print("=== Project Scope Guard ===")
    print(f"Total checks: {state.get('total_checks', 0)}")
    print(f"Total warnings: {state.get('total_warnings', 0)}")
    print(f"Active client: {state.get('active_client', 'None')}")

    client_scopes = state.get("client_scopes", {})
    if client_scopes:
        print("\nClient scopes:")
        for client, scope in sorted(client_scopes.items()):
            categories = scope.get("categories", [])
            print(f"  {client}: {', '.join(categories) if categories else 'unlimited'}")

    warnings = state.get("scope_warnings", [])
    if warnings:
        print(f"\nRecent scope warnings (last {min(10, len(warnings))}):")
        for w in warnings[-10:]:
            ts = w.get("timestamp", "?")[:19]
            client = w.get("client", "?")
            requested = w.get("requested_category", "?")
            print(f"  [{ts}] {client}: attempted '{requested}' (out of scope)")

    print("\nWorkflow categories:")
    for category in sorted(WORKFLOW_CATEGORIES.keys()):
        print(f"  {category}")

    sys.exit(0)


def reset_state():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    print("Project scope guard state reset.")
    sys.exit(0)


def main():
    if "--status" in sys.argv:
        show_status()
    if "--reset" in sys.argv:
        reset_state()

    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool_name not in ("Bash", "bash"):
        sys.exit(0)

    command = tool_input.get("command", "")
    if not command or "execution/" not in command:
        sys.exit(0)

    state = load_state()
    state["total_checks"] = state.get("total_checks", 0) + 1
    now = datetime.now().isoformat()

    # Update active client if command references client
    client_match = re.search(r'clients/([a-zA-Z0-9_-]+)/', command)
    if client_match:
        state["active_client"] = client_match.group(1)

    active_client = detect_client_from_context(state)
    if not active_client:
        save_state(state)
        sys.exit(0)

    # Load or cache client scope
    client_scopes = state.get("client_scopes", {})
    if active_client not in client_scopes:
        scope_categories = load_client_scope(active_client)
        if scope_categories:
            client_scopes[active_client] = {
                "categories": scope_categories,
                "loaded_at": now
            }
            state["client_scopes"] = client_scopes
        else:
            # No scope defined - allow everything
            save_state(state)
            sys.exit(0)

    scope = client_scopes.get(active_client, {})
    allowed_categories = scope.get("categories", [])

    if not allowed_categories:
        save_state(state)
        sys.exit(0)

    # Detect what workflow is being run
    requested_category = detect_workflow_category(command)
    if not requested_category:
        save_state(state)
        sys.exit(0)

    # Check if in scope
    if requested_category not in allowed_categories:
        state["total_warnings"] = state.get("total_warnings", 0) + 1
        warnings = state.get("scope_warnings", [])
        warnings.append({
            "timestamp": now,
            "client": active_client,
            "requested_category": requested_category,
            "allowed_categories": allowed_categories,
            "command": command[:150]
        })
        state["scope_warnings"] = warnings[-100:]
        save_state(state)

        sys.stderr.write(
            f"[Scope Guard] WARNING: '{requested_category}' may be out of scope for {active_client}.\n"
            f"  Client scope: {', '.join(allowed_categories)}\n"
            f"  Requested: {requested_category}\n"
            f"  Verify this is intentional before proceeding.\n"
        )
        # Warn but don't block
        sys.exit(0)

    save_state(state)
    sys.exit(0)


if __name__ == "__main__":
    main()
