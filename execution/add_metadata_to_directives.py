#!/usr/bin/env python3
"""
Add YAML Frontmatter to Directives

Converts legacy directives (plain markdown) to new format with YAML frontmatter.
Intelligently extracts metadata from markdown structure.

Usage:
    python3 execution/add_metadata_to_directives.py --directive cold_email_scriptwriter
    python3 execution/add_metadata_to_directives.py --all --dry-run
    python3 execution/add_metadata_to_directives.py --all --verify
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, Any, List
import yaml

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DIRECTIVES_PATH = PROJECT_ROOT / "directives"
EXECUTION_PATH = PROJECT_ROOT / "execution"

def extract_title(content: str) -> str:
    """Extract title from first # heading."""
    match = re.search(r'^#\s+(.+?)$', content, re.MULTILINE)
    return match.group(1).strip() if match else "Untitled Workflow"

def extract_description(content: str) -> str:
    """Extract description from ## What This Workflow Does section."""
    # Look for common description patterns
    patterns = [
        r'##\s+What\s+This\s+Workflow\s+(?:Does|Is)\s*\n+(.+?)(?=\n##|\n\n##|\Z)',
        r'##\s+Description\s*\n+(.+?)(?=\n##|\n\n##|\Z)',
        r'##\s+Overview\s*\n+(.+?)(?=\n##|\n\n##|\Z)',
    ]

    for pattern in patterns:
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            desc = match.group(1).strip()
            # Clean up: take first paragraph, max 500 chars
            desc = desc.split('\n\n')[0]
            desc = re.sub(r'\n+', ' ', desc)
            return desc[:500]

    # Fallback: take first paragraph after title
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if line.strip() and not line.startswith('#'):
            return lines[i].strip()[:500]

    return ""

def extract_execution_scripts(content: str) -> List[str]:
    """Extract execution scripts from ## How to Run section."""
    scripts = []

    # Pattern 1: python3 execution/<script>.py
    matches = re.findall(r'python3?\s+execution/(\w+\.py)', content)
    scripts.extend(matches)

    # Pattern 2: Code blocks with script names
    code_blocks = re.findall(r'```(?:bash|sh|python)?\n(.+?)```', content, re.DOTALL)
    for block in code_blocks:
        script_matches = re.findall(r'execution/(\w+\.py)', block)
        scripts.extend(script_matches)

    # Pattern 3: Explicit mentions in "Execution" or "Script" sections
    sections = re.findall(r'##\s+(?:Execution|Script|File).*?\n+(.+?)(?=\n##|\Z)', content, re.DOTALL | re.IGNORECASE)
    for section in sections:
        script_matches = re.findall(r'(\w+\.py)', section)
        scripts.extend(script_matches)

    # Deduplicate and verify existence
    unique_scripts = []
    seen = set()
    for script in scripts:
        if script not in seen:
            seen.add(script)
            if (EXECUTION_PATH / script).exists():
                unique_scripts.append(script)

    return unique_scripts if unique_scripts else ["workflow_placeholder.py"]

def extract_env_vars(content: str) -> List[str]:
    """Extract environment variables from ## Required API Keys or code examples."""
    env_vars = set()

    # Pattern 1: Look in "Required API Keys" or "Prerequisites" sections
    sections = re.findall(r'##\s+(?:Required\s+API\s+Keys|Prerequisites|Environment).*?\n+(.+?)(?=\n##|\Z)', content, re.DOTALL | re.IGNORECASE)
    for section in sections:
        # Extract from table or list
        var_matches = re.findall(r'[`\|]?\s*([A-Z][A-Z_0-9]{3,})\s*[`\|]?', section)
        env_vars.update(var_matches)

    # Pattern 2: Code blocks with .env examples
    code_blocks = re.findall(r'```(?:bash|env)?\n(.+?)```', content, re.DOTALL)
    for block in code_blocks:
        var_matches = re.findall(r'^([A-Z][A-Z_0-9]{3,})=', block, re.MULTILINE)
        env_vars.update(var_matches)

    # Pattern 3: os.getenv() calls
    getenv_matches = re.findall(r'os\.getenv\(["\']([A-Z_]+)["\']', content)
    env_vars.update(getenv_matches)

    # Filter common false positives
    exclude = {"API", "KEY", "URL", "PATH", "TOKEN", "ID", "SECRET"}
    return sorted([v for v in env_vars if v not in exclude and len(v) > 3])

def detect_integrations(content: str) -> List[str]:
    """Detect integrations from content."""
    integrations = set()

    # Map keywords to integration names
    integration_map = {
        'slack': ['slack', 'slack webhook'],
        'google_docs': ['google doc', 'google docs'],
        'google_sheets': ['google sheet', 'google sheets'],
        'perplexity': ['perplexity'],
        'openrouter': ['openrouter'],
        'anthropic': ['claude', 'anthropic'],
        'openai': ['openai', 'gpt'],
        'apify': ['apify'],
        'calendly': ['calendly'],
        'stripe': ['stripe'],
        'hubspot': ['hubspot'],
        'instantly': ['instantly'],
    }

    content_lower = content.lower()
    for integration, keywords in integration_map.items():
        if any(kw in content_lower for kw in keywords):
            integrations.add(integration)

    return sorted(integrations)

def detect_type(content: str) -> str:
    """Detect workflow type (manual, cron, webhook, web)."""
    content_lower = content.lower()

    # Check for webhook indicators
    if any(word in content_lower for word in ['webhook', 'post /webhook', 'http trigger', 'calendly webhook']):
        return "webhook"

    # Check for cron indicators
    if any(word in content_lower for word in ['cron', 'schedule', 'every', 'hourly', 'daily']):
        # Look for actual cron expressions
        if re.search(r'\d+\s+[\*/\d]+\s+\*\s+\*\s+\*', content):
            return "cron"

    # Check for web service indicators
    if any(word in content_lower for word in ['gunicorn', 'flask', 'fastapi', 'web app', 'dashboard']):
        return "web"

    # Default to manual
    return "manual"

def detect_category(content: str, title: str) -> str:
    """Detect workflow category from content."""
    content_lower = content.lower()
    title_lower = title.lower()

    categories = {
        "Lead Generation": ['lead', 'prospect', 'scrape', 'scraper', 'linkedin', 'google maps'],
        "Content Creation": ['blog', 'post', 'content', 'newsletter', 'article', 'video script'],
        "Sales & Outreach": ['email', 'cold', 'outreach', 'sales', 'follow up', 'sequence'],
        "Analytics & Reporting": ['report', 'analytics', 'dashboard', 'metrics', 'tracking'],
        "Client Management": ['client', 'customer', 'crm', 'onboarding', 'qbr'],
        "Video Production": ['video', 'thumbnail', 'edit', 'jump cut'],
        "Design": ['image', 'thumbnail', 'creative', 'design', 'photoshoot'],
        "Integration": ['webhook', 'integration', 'sync', 'automation'],
        "Automation": ['automate', 'automation', 'workflow'],
    }

    # Score each category
    scores = {}
    for category, keywords in categories.items():
        score = sum(1 for kw in keywords if kw in content_lower or kw in title_lower)
        if score > 0:
            scores[category] = score

    # Return highest score, default to General
    if scores:
        return max(scores, key=scores.get)
    return "General"

def extract_cron_schedule(content: str) -> str:
    """Extract cron schedule if present."""
    # Look for cron expressions
    patterns = [
        r'"cronSchedule":\s*"([^"]+)"',
        r'cronSchedule:\s*"([^"]+)"',
        r'cron:\s*"([^"]+)"',
        r'schedule:\s*"([^"]+)"',
    ]

    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            return match.group(1)

    # Look for explicit cron format in text
    cron_match = re.search(r'(\d+\s+[\*/\d]+\s+\*\s+\*\s+\*)', content)
    if cron_match:
        return cron_match.group(1)

    return None

def generate_metadata(filepath: Path, content: str) -> Dict[str, Any]:
    """Generate metadata from directive content."""
    metadata = {
        "id": filepath.stem,
        "name": extract_title(content),
        "version": "1.0.0",
        "category": detect_category(content, extract_title(content)),
        "type": detect_type(content),
        "description": extract_description(content),
        "execution_scripts": extract_execution_scripts(content),
    }

    # Optional fields
    env_vars = extract_env_vars(content)
    if env_vars:
        metadata["env_vars"] = env_vars

    integrations = detect_integrations(content)
    if integrations:
        metadata["integrations"] = integrations

    # Deployment config
    deployment = {}
    cron_schedule = extract_cron_schedule(content)
    if cron_schedule:
        deployment["cron_schedule"] = cron_schedule

    if deployment:
        metadata["deployment"] = deployment

    return metadata

def add_frontmatter(filepath: Path, dry_run: bool = False) -> bool:
    """Add YAML frontmatter to directive file."""
    content = filepath.read_text(encoding='utf-8')

    # Check if frontmatter already exists
    if content.startswith("---"):
        print(f"  ⚠ Already has frontmatter: {filepath.name}")
        return False

    # Generate metadata
    metadata = generate_metadata(filepath, content)

    # Create YAML frontmatter
    yaml_str = yaml.dump(metadata, sort_keys=False, allow_unicode=True)
    new_content = f"---\n{yaml_str}---\n\n{content}"

    if dry_run:
        print(f"\n{'='*60}")
        print(f"DRY RUN: {filepath.name}")
        print(f"{'='*60}")
        print(yaml_str)
        print(f"{'='*60}\n")
        return True

    # Write back
    filepath.write_text(new_content, encoding='utf-8')
    print(f"  ✓ Added frontmatter: {filepath.name}")
    return True

def main():
    parser = argparse.ArgumentParser(description="Add YAML frontmatter to directives")
    parser.add_argument("--directive", help="Convert single directive (name without .md)")
    parser.add_argument("--all", action="store_true", help="Convert all directives")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be added without writing")
    parser.add_argument("--verify", action="store_true", help="Run validation after conversion")
    args = parser.parse_args()

    if not args.directive and not args.all:
        print("Error: Must specify --directive or --all")
        return 1

    # Get files to convert
    if args.directive:
        files = [DIRECTIVES_PATH / f"{args.directive}.md"]
        if not files[0].exists():
            print(f"Error: Directive not found: {files[0]}")
            return 1
    else:
        files = sorted([f for f in DIRECTIVES_PATH.glob("*.md") if not f.name.startswith("_")])

    print(f"\nConverting {len(files)} directive(s)...\n")

    converted = 0
    skipped = 0

    for filepath in files:
        if add_frontmatter(filepath, dry_run=args.dry_run):
            converted += 1
        else:
            skipped += 1

    # Summary
    print(f"\n{'='*60}")
    print(f"Converted: {converted}")
    print(f"Skipped:   {skipped}")
    print(f"{'='*60}\n")

    # Verify if requested
    if args.verify and not args.dry_run and converted > 0:
        print("Running validation...\n")
        import subprocess
        result = subprocess.run(
            [sys.executable, str(EXECUTION_PATH / "validate_directive_metadata.py")],
            cwd=str(PROJECT_ROOT)
        )
        return result.returncode

    return 0

if __name__ == "__main__":
    sys.exit(main())
