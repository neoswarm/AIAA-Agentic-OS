"""
AIAA Dashboard - Skill Execution Service
Parses SKILL.md files, lists available skills, and executes skill scripts.
"""

import os
import re
import sys
import uuid
import json
import subprocess
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent directory to path so we can import models/database
sys.path.insert(0, str(Path(__file__).parent.parent))
import models
from services.run_guard import (
    bind_run_to_reservation,
    release_run_reservation,
    mark_run_running,
    mark_run_finished,
)


# ==============================================================================
# Configuration
# ==============================================================================

# Skills directory: resolve relative to the Agentic OS project root
_DASHBOARD_DIR = Path(__file__).parent.parent
_PROJECT_ROOT = _DASHBOARD_DIR.parent.parent  # railway_apps/aiaa_dashboard -> Agentic OS
SKILLS_DIR = _PROJECT_ROOT / ".claude" / "skills"

# Override via environment variable if set
if os.getenv("SKILLS_DIR"):
    SKILLS_DIR = Path(os.getenv("SKILLS_DIR"))


# ==============================================================================
# Category Mapping
# ==============================================================================

CATEGORY_KEYWORDS = {
    "content": [
        "blog", "content", "newsletter", "press-release", "carousel",
        "podcast", "rss", "case-study", "product-description", "faq",
    ],
    "email": [
        "email", "cold-email", "campaign-launcher", "campaign-report",
        "ecommerce-email", "ecom-email", "follow-up", "webinar-followup",
        "email-deliverability", "email-validator", "email-reply",
        "email-autoreply", "email-sequence",
    ],
    "research": [
        "research", "company-research", "market-research", "niche-research",
        "prospect-research", "ab-test", "seo-audit", "competitor-monitor",
        "brand-monitor", "win-loss",
    ],
    "social": [
        "linkedin", "twitter", "instagram", "social", "carousel-post",
        "x-youtube", "reddit",
    ],
    "video": [
        "video", "youtube", "vsl", "thumbnail", "reel", "pan-3d",
        "jump-cut", "zoom-content", "niche-outlier",
    ],
    "ads": [
        "ad-creative", "meta-ads", "google-ads", "static-ad", "fb-ad",
        "landing-page", "funnel", "video-ad",
    ],
    "leads": [
        "lead", "scraping", "scraper", "gmaps", "crunchbase", "job-board",
        "yelp", "serp", "hubspot", "ghl", "upwork", "linkedin-lead",
        "linkedin-group", "funding-tracker",
    ],
    "sales": [
        "sales", "proposal", "pricing", "objection", "demo", "cold-email-campaign",
        "contract-renewal", "payment", "invoice", "qbr",
    ],
    "client": [
        "client", "onboarding", "churn", "milestone", "monthly-report",
        "review-collector", "testimonial",
    ],
    "automation": [
        "automation", "n8n", "webhook", "crm", "task-assignment",
        "stripe", "meeting-alert", "meeting-prep",
    ],
    "deploy": [
        "deploy", "railway", "modal", "dashboard", "agency-dashboard",
    ],
}

SYNONYM_MAP = {
    "email": ["cold-email", "email-sequence", "email-deliverability",
              "campaign-launcher", "follow-up", "ecommerce-email"],
    "blog": ["blog-post", "content", "newsletter", "press-release"],
    "research": ["company-research", "market-research", "niche-research",
                  "prospect-research", "competitor-monitor", "brand-monitor"],
    "video": ["vsl", "youtube", "reel", "thumbnail", "video-ad"],
    "social": ["linkedin", "twitter", "instagram", "carousel-post"],
    "funnel": ["vsl-funnel", "landing-page"],
    "outreach": ["cold-email", "cold-dm", "linkedin-lead"],
    "ads": ["ad-creative", "meta-ads", "google-ads", "static-ad", "fb-ad"],
    "lead": ["lead-list-builder", "scraping", "gmaps", "crunchbase",
             "linkedin-lead", "funding-tracker"],
    "seo": ["seo-audit", "blog-post"],
    "write": ["blog-post", "case-study", "press-release", "newsletter",
              "product-description", "cold-email-campaign"],
    "automate": ["automation-builder", "n8n", "webhook"],
    "image": ["ai-image-generator", "thumbnail", "static-ad"],
    "proposal": ["proposal", "pricing", "sales-deck"],
    "client": ["client-onboarding", "client-feedback", "client-health",
               "client-report", "churn-alert"],
}

ROLE_SKILL_MAP = {
    "marketing": ["content", "social", "email", "ads", "video"],
    "sales": ["sales", "leads", "email", "research"],
    "operations": ["automation", "deploy", "client"],
    "executive": ["research", "client", "content"],
}


# ==============================================================================
# SKILL.md Parsing
# ==============================================================================

def parse_skill_md(skill_name: str) -> Optional[Dict[str, Any]]:
    """Parse a SKILL.md file and extract structured metadata.

    Returns a dict with keys: name, description, goal, prerequisites,
    execution_command, inputs, quality_checklist, process_steps,
    related_directives, related_skill_bibles, category.
    Returns None if the skill directory or SKILL.md doesn't exist.
    """
    skill_dir = SKILLS_DIR / skill_name
    skill_md_path = skill_dir / "SKILL.md"

    if not skill_md_path.exists():
        return None

    content = skill_md_path.read_text(encoding="utf-8")
    result = {
        "name": skill_name,
        "description": "",
        "goal": "",
        "prerequisites": [],
        "execution_command": "",
        "inputs": [],
        "quality_checklist": [],
        "process_steps": [],
        "related_directives": [],
        "related_skill_bibles": [],
        "output_examples": [],
        "category": _categorize_skill(skill_name, ""),
    }

    # Parse YAML frontmatter
    frontmatter_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if frontmatter_match:
        fm = frontmatter_match.group(1)
        for line in fm.strip().split('\n'):
            if ':' in line:
                key, _, value = line.partition(':')
                key = key.strip()
                value = value.strip()
                if key == 'name':
                    result["name"] = value
                elif key == 'description':
                    result["description"] = value

    # Parse Goal section
    goal_match = re.search(r'## Goal\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
    if goal_match:
        result["goal"] = goal_match.group(1).strip()

    # Parse Prerequisites section
    prereq_match = re.search(r'## Prerequisites\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
    if prereq_match:
        prereqs = []
        for line in prereq_match.group(1).strip().split('\n'):
            line = line.strip().lstrip('- ')
            if line:
                prereqs.append(line)
        result["prerequisites"] = prereqs

    # Parse Execution Command section
    exec_match = re.search(r'## Execution Command\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
    if exec_match:
        # Extract first code block
        code_match = re.search(r'```(?:bash)?\s*\n(.*?)```', exec_match.group(1), re.DOTALL)
        if code_match:
            result["execution_command"] = code_match.group(1).strip()

    # Parse Input Specifications table
    input_match = re.search(r'## Input Specifications\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
    if input_match:
        result["inputs"] = _parse_input_table(input_match.group(1))

    # Parse Quality Checklist
    quality_match = re.search(r'## Quality Checklist\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
    if quality_match:
        checklist = []
        for line in quality_match.group(1).strip().split('\n'):
            line = line.strip()
            # Match "- [ ] item" or "- [x] item"
            item_match = re.match(r'-\s*\[[ x]\]\s*(.*)', line)
            if item_match:
                checklist.append(item_match.group(1).strip())
        result["quality_checklist"] = checklist

    # Parse Process Steps
    steps_match = re.search(r'## Process Steps\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
    if steps_match:
        steps = []
        for line in steps_match.group(1).strip().split('\n'):
            line = line.strip()
            step_match = re.match(r'\d+\.\s+\*\*(.*?)\*\*\s*[-—]\s*(.*)', line)
            if step_match:
                steps.append({
                    "name": step_match.group(1).strip(),
                    "description": step_match.group(2).strip(),
                })
        result["process_steps"] = steps

    # Parse Related Directives
    directives_match = re.search(r'## Related Directives\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
    if directives_match:
        for line in directives_match.group(1).strip().split('\n'):
            line = line.strip().lstrip('- ')
            if line.startswith('`') and line.endswith('`'):
                line = line[1:-1]
            if line:
                result["related_directives"].append(line)

    # Parse Related Skill Bibles
    bibles_match = re.search(r'## Related Skill Bibles\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
    if bibles_match:
        for line in bibles_match.group(1).strip().split('\n'):
            line = line.strip().lstrip('- ')
            if line.startswith('`') and line.endswith('`'):
                line = line[1:-1]
            if line:
                result["related_skill_bibles"].append(line)

    # Parse Outputs section
    outputs_match = re.search(r'## Outputs?\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
    if outputs_match:
        output_lines = []
        for line in outputs_match.group(1).strip().split('\n'):
            line = line.strip().lstrip('- ')
            if line:
                output_lines.append(line)
        result["output_examples"] = output_lines
    else:
        result["output_examples"] = []

    # Update category with description context
    result["category"] = _categorize_skill(skill_name, result["description"])

    return result


def _parse_input_table(table_text: str) -> List[Dict[str, Any]]:
    """Parse a markdown table of input specifications.

    Expected format:
    | Arg | Required | Description |
    |-----|----------|-------------|
    | `--topic` | Yes | Blog post topic |
    """
    inputs = []
    lines = table_text.strip().split('\n')

    # Find header line to determine column mapping
    header_line = None
    header_idx = -1
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('|') and 'Arg' in stripped:
            header_line = stripped
            header_idx = i
            break

    if header_line is None:
        return inputs

    # Parse header columns
    headers = [h.strip().lower() for h in header_line.strip('|').split('|')]

    # Process data rows (skip header and separator)
    for line in lines[header_idx + 2:]:
        line = line.strip()
        if not line.startswith('|'):
            continue

        cells = [c.strip() for c in line.strip('|').split('|')]
        if len(cells) < len(headers):
            continue

        row = {}
        for j, header in enumerate(headers):
            if j < len(cells):
                row[header] = cells[j]

        # Normalize the arg name
        arg_name = row.get('arg', '').strip('`').strip()
        required_raw = row.get('required', 'No').strip()
        required = required_raw.lower() in ('yes', 'true', 'required')
        description = row.get('description', '').strip()

        # Try to extract a default value from description
        default = None
        default_match = re.search(r'\(default:\s*(.*?)\)', description)
        if default_match:
            default = default_match.group(1).strip().strip('`')

        # Infer type from description or arg name
        input_type = "string"
        if any(word in description.lower() for word in ['number', 'count', 'length', 'limit']):
            input_type = "number"
        elif any(word in description.lower() for word in ['csv', 'json', 'file']):
            input_type = "file"
        elif any(word in description.lower() for word in ['url', 'website', 'link']):
            input_type = "url"
        elif '/' in description and all(
            opt.strip() for opt in description.split('(')[0].split('/')
        ) is False:
            pass  # not an enum, keep as string

        # Check for enum-like values in description (e.g., "professional/casual/educational")
        enum_match = re.search(r'\(([a-z]+(?:/[a-z]+)+)\)', description)
        if enum_match:
            input_type = "enum"
            options = enum_match.group(1).split('/')
        else:
            options = None

        inputs.append({
            "name": arg_name,
            "required": required,
            "description": description,
            "type": input_type,
            "default": default,
            "options": options,
        })

    return inputs


def _categorize_skill(skill_name: str, description: str) -> str:
    """Categorize a skill based on its name and description.

    Prioritizes name matches over description matches to avoid
    misclassification (e.g., vsl-funnel mentioning 'email' in description).
    """
    name_lower = skill_name.lower()

    # First pass: match against skill name only (higher priority)
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in name_lower:
                return category

    # Second pass: match against description
    desc_lower = description.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in desc_lower:
                return category

    return "other"


# ==============================================================================
# Skill Discovery
# ==============================================================================

def list_available_skills() -> List[Dict[str, Any]]:
    """Scan the skills directory and return metadata for each skill.

    Returns a list of dicts with: name, description, category, has_script, inputs.
    Skips directories starting with '_' (like _shared).
    """
    if not SKILLS_DIR.exists():
        return []

    skills = []
    for entry in sorted(SKILLS_DIR.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name.startswith('_'):
            continue

        skill_md = entry / "SKILL.md"
        if not skill_md.exists():
            continue

        # Check for a .py script
        py_files = list(entry.glob("*.py"))
        has_script = len(py_files) > 0
        script_path = str(py_files[0]) if has_script else None

        # Quick parse: extract name and description from frontmatter
        content = skill_md.read_text(encoding="utf-8")
        name = entry.name
        description = ""

        fm_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
        if fm_match:
            for line in fm_match.group(1).split('\n'):
                if line.startswith('name:'):
                    name = line.split(':', 1)[1].strip()
                elif line.startswith('description:'):
                    description = line.split(':', 1)[1].strip()

        # Quick parse: extract input specs
        input_match = re.search(r'## Input Specifications\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
        inputs = _parse_input_table(input_match.group(1)) if input_match else []

        # Parse Process Steps for step count and time estimate
        steps_match = re.search(r'## Process Steps\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
        step_count = 0
        if steps_match:
            step_count = len(re.findall(r'^\d+\.', steps_match.group(1), re.MULTILINE))

        # Parse Prerequisites for complexity scoring
        prereq_count = 0
        prereq_match = re.search(r'## Prerequisites\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
        if prereq_match:
            prereq_count = len([l for l in prereq_match.group(1).strip().split('\n') if l.strip().startswith('-')])

        # Compute complexity and estimated run time
        required_inputs = sum(1 for i in inputs if i.get("required"))
        complexity_score = step_count + prereq_count + required_inputs
        complexity = "simple" if complexity_score <= 5 else ("moderate" if complexity_score <= 10 else "advanced")
        estimated_minutes = max(step_count // 2, 1)

        category = _categorize_skill(entry.name, description)

        skills.append({
            "name": entry.name,
            "display_name": name,
            "description": description,
            "category": category,
            "has_script": has_script,
            "script_path": script_path,
            "inputs": inputs,
            "estimated_minutes": estimated_minutes,
            "complexity": complexity,
            "step_count": step_count,
        })

    return skills


def get_skill_categories() -> Dict[str, List[Dict[str, str]]]:
    """Return skills grouped by category.

    Returns a dict mapping category name to a list of
    {name, display_name, description} dicts.
    """
    skills = list_available_skills()
    categories = {}

    for skill in skills:
        cat = skill["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append({
            "name": skill["name"],
            "display_name": skill["display_name"],
            "description": skill["description"],
        })

    # Sort categories by number of skills (descending)
    return dict(sorted(categories.items(), key=lambda x: -len(x[1])))


def get_recommended_skills(role: str, limit: int = 8) -> list:
    """Get skills recommended for a user role."""
    categories = ROLE_SKILL_MAP.get(role.lower(), []) if role else []
    if not categories:
        return _get_popular_skills(limit)
    skills = list_available_skills()
    recommended = [s for s in skills if s["category"] in categories]
    recommended.sort(key=lambda s: (
        categories.index(s["category"]) if s["category"] in categories else 99
    ))
    return recommended[:limit]


def _get_popular_skills(limit: int = 8) -> list:
    """Fallback: get popular skills by execution count, or curated defaults."""
    try:
        stats = models.get_skill_execution_stats()
        top = stats.get("top_skills", {})
        if len(top) >= 3:
            skills = list_available_skills()
            skill_map = {s["name"]: s for s in skills}
            popular = []
            for name in sorted(top, key=lambda n: -top[n]):
                if name in skill_map:
                    popular.append(skill_map[name])
                if len(popular) >= limit:
                    break
            if popular:
                return popular
    except Exception:
        pass
    # Curated fallback
    default_names = ["blog-post", "cold-email-campaign", "company-research",
                     "market-research", "vsl-funnel", "lead-list-builder"]
    skills = list_available_skills()
    skill_map = {s["name"]: s for s in skills}
    return [skill_map[n] for n in default_names if n in skill_map][:limit]


def search_skills(query: str) -> List[Dict[str, Any]]:
    """Search skills with partial matching and synonym support.

    Expands query tokens using SYNONYM_MAP for broader discovery,
    then scores each skill by relevance. Returns sorted by descending score.
    """
    if not query or not query.strip():
        return list_available_skills()

    tokens = query.lower().split()
    skills = list_available_skills()
    scored = []

    # Expand tokens with synonyms
    expanded_tokens = set(tokens)
    for token in tokens:
        if token in SYNONYM_MAP:
            expanded_tokens.update(SYNONYM_MAP[token])
        # Also check partial synonym keys (e.g., "auto" matches "automate")
        for syn_key, syn_values in SYNONYM_MAP.items():
            if syn_key.startswith(token) or token.startswith(syn_key):
                expanded_tokens.update(syn_values)

    for skill in skills:
        searchable = (
            f"{skill['name']} {skill['display_name']} "
            f"{skill['description']} {skill['category']}"
        ).lower()
        score = 0

        for token in expanded_tokens:
            if token in searchable:
                score += 1
                if token in skill["name"].lower():
                    score += 2  # Boost exact name match
                if token == skill["category"]:
                    score += 1  # Boost category match

        # Also check original tokens for partial name matching
        for token in tokens:
            # Partial match: "email" in "cold-email-campaign"
            if token in skill["name"].lower():
                score += 3  # Strong boost for direct partial name match

        if score > 0:
            skill_copy = dict(skill)
            skill_copy["relevance_score"] = score
            scored.append(skill_copy)

    scored.sort(key=lambda x: -x["relevance_score"])
    return scored


# ==============================================================================
# Skill Execution
# ==============================================================================

def execute_skill(
    skill_name: str,
    params: Optional[Dict[str, str]] = None,
    run_guard_session_key: Optional[str] = None,
    run_guard_reservation_id: Optional[str] = None,
) -> str:
    """Execute a skill's Python script with the given parameters.

    Creates a DB record, launches subprocess in a background thread,
    and returns the execution ID immediately.
    """
    # Parse skill to get execution info
    skill_info = parse_skill_md(skill_name)
    if skill_info is None:
        raise ValueError(f"Skill not found: {skill_name}")

    # Find the Python script
    skill_dir = SKILLS_DIR / skill_name
    py_files = list(skill_dir.glob("*.py"))
    if not py_files:
        raise ValueError(f"No Python script found for skill: {skill_name}")

    script_path = str(py_files[0])

    # Generate execution ID
    execution_id = str(uuid.uuid4())

    # Create DB record
    models.create_skill_execution(
        execution_id=execution_id,
        skill_name=skill_name,
        params=params,
    )

    # Build command
    cmd = [sys.executable, script_path]
    if params:
        for key, value in params.items():
            if value is None or value == "":
                continue
            # Normalize arg name
            arg = key if key.startswith('--') else f"--{key}"
            cmd.extend([arg, str(value)])

    slot_bound = False
    if run_guard_session_key and run_guard_reservation_id:
        slot_bound = bind_run_to_reservation(
            run_guard_session_key,
            run_guard_reservation_id,
            execution_id,
        )
        if not slot_bound:
            raise RuntimeError("Failed to reserve session run slot")

    # Launch in background thread
    thread = threading.Thread(
        target=_run_skill_subprocess,
        args=(execution_id, cmd, skill_name),
        daemon=True,
    )
    try:
        thread.start()
    except Exception:
        if slot_bound:
            mark_run_finished(execution_id)
        elif run_guard_session_key and run_guard_reservation_id:
            release_run_reservation(run_guard_session_key, run_guard_reservation_id)
        raise

    return execution_id


def _run_skill_subprocess(execution_id: str, cmd: List[str], skill_name: str):
    """Run a skill subprocess and update the DB with results.

    This runs in a background thread.
    """
    mark_run_running(execution_id)
    # Mark as running
    models.update_skill_execution_status(execution_id, 'running')

    try:
        # Set up environment with project root
        env = os.environ.copy()
        env["PYTHONPATH"] = str(_PROJECT_ROOT)

        # Run the subprocess
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout
            cwd=str(_PROJECT_ROOT),
            env=env,
        )

        stdout = process.stdout or ""
        stderr = process.stderr or ""

        if process.returncode == 0:
            # Determine output path from stdout (many scripts print the path)
            output_path = _extract_output_path(stdout)
            preview = stdout[:500] if stdout else None

            models.update_skill_execution_status(
                execution_id,
                'success',
                output_preview=preview,
                output_path=output_path,
            )
        else:
            error_msg = stderr[:1000] if stderr else f"Process exited with code {process.returncode}"
            preview = stdout[:500] if stdout else None

            models.update_skill_execution_status(
                execution_id,
                'error',
                output_preview=preview,
                error_message=error_msg,
            )

    except subprocess.TimeoutExpired:
        models.update_skill_execution_status(
            execution_id,
            'error',
            error_message="Execution timed out after 10 minutes",
        )
    except Exception as e:
        models.update_skill_execution_status(
            execution_id,
            'error',
            error_message=str(e)[:1000],
        )
    finally:
        mark_run_finished(execution_id)


def _extract_output_path(stdout: str) -> Optional[str]:
    """Try to extract an output file path from subprocess stdout."""
    # Common patterns in skill scripts:
    # "Saved to .tmp/blog_post.md"
    # "Output: .tmp/emails.json"
    # "Created: .tmp/vsl_funnel_acme/01_research.md"
    for pattern in [
        r'(?:Saved|Output|Created|Written|Generated)(?:\s+to)?:\s*(.+\.(?:md|json|txt|html|csv))',
        r'(\.tmp/[^\s]+\.(?:md|json|txt|html|csv))',
    ]:
        match = re.search(pattern, stdout, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def get_execution_status(execution_id: str) -> Optional[Dict[str, Any]]:
    """Get the current status and output of a skill execution."""
    return models.get_skill_execution(execution_id)


# ==============================================================================
# Utility
# ==============================================================================

def get_skill_script_path(skill_name: str) -> Optional[str]:
    """Get the path to a skill's Python script."""
    skill_dir = SKILLS_DIR / skill_name
    if not skill_dir.exists():
        return None
    py_files = list(skill_dir.glob("*.py"))
    return str(py_files[0]) if py_files else None


def get_skill_count() -> int:
    """Get total number of available skills."""
    if not SKILLS_DIR.exists():
        return 0
    return sum(
        1 for d in SKILLS_DIR.iterdir()
        if d.is_dir() and not d.name.startswith('_') and (d / "SKILL.md").exists()
    )
