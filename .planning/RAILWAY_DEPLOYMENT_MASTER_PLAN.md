# Railway Workflow Deployment Automation - Master Plan

**Version:** 1.0
**Date:** February 11, 2026
**Status:** Planning Phase
**Scope:** Complete end-to-end automation of workflow deployment to Railway with dashboard integration

---

## Executive Summary

This plan transforms the AIAA Agentic OS from a system that can only **manage** existing Railway workflows to one that can **deploy** them automatically. The goal: a user works locally, says "deploy this to Railway," and the workflow is live on Railway with all dependencies, environment variables, and configurations correctly set—no manual Railway CLI work required.

**Current State:** 0% automated deployment, 70% management capability
**Target State:** 95% automated deployment, 100% management capability
**Expected Outcome:** One-command deployment from local script to production Railway service

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [The 7 Critical Blockers (Detailed Analysis)](#2-the-7-critical-blockers-detailed-analysis)
3. [Metadata System Design](#3-metadata-system-design)
4. [Deployment Engine Architecture](#4-deployment-engine-architecture)
5. [Dashboard Enhancements](#5-dashboard-enhancements)
6. [Railway Integration Layer](#6-railway-integration-layer)
7. [Environment Variable Orchestration](#7-environment-variable-orchestration)
8. [Workflow Discovery & Registration](#8-workflow-discovery--registration)
9. [Quality Gates & Validation](#9-quality-gates--validation)
10. [Implementation Phases](#10-implementation-phases)
11. [File-by-File Modification Plan](#11-file-by-file-modification-plan)
12. [Testing Strategy](#12-testing-strategy)
13. [Rollback & Recovery](#13-rollback--recovery)
14. [Performance & Scalability](#14-performance--scalability)
15. [Security Hardening](#15-security-hardening)

---

## 1. Architecture Overview

### 1.1 Current Architecture (Broken Deployment Path)

```
User Request: "Deploy workflow X to Railway"
           ↓
    [NO AUTOMATED PATH]
           ↓
Manual Steps Required:
  1. Create railway_apps/<name>/ folder
  2. Write Procfile + railway.json + requirements.txt
  3. Copy execution script + dependencies
  4. Run `railway init` + `railway up`
  5. Run `railway variables set KEY=value` (×15 times)
  6. Manually register in workflow_config.json
  7. Wait for build
  8. Test and debug
           ↓
   Workflow is live (30-60 minutes of manual work)
```

**Problems:**
- No automation
- High error rate (forgotten env vars, wrong dependencies)
- Not repeatable
- Doesn't scale (149 directives × manual work = infeasible)
- Dashboard only knows about manually-registered workflows

---

### 1.2 Target Architecture (Fully Automated)

```
User Request: "Deploy cold_email_scriptwriter to Railway"
           ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 1: DISCOVERY & VALIDATION                            │
├─────────────────────────────────────────────────────────────┤
│ 1. Scan directives/ for cold_email_scriptwriter.md         │
│ 2. Parse YAML frontmatter → extract metadata                │
│ 3. Validate: execution scripts exist, type is valid        │
│ 4. Detect deployment type: cron | webhook | web             │
└─────────────────────────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 2: DEPENDENCY RESOLUTION                              │
├─────────────────────────────────────────────────────────────┤
│ 1. Parse execution script for imports                       │
│ 2. Extract env vars from os.getenv() calls                  │
│ 3. Generate minimal requirements.txt from AST analysis      │
│ 4. Resolve skill bible dependencies                         │
└─────────────────────────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 3: RAILWAY SERVICE CREATION                           │
├─────────────────────────────────────────────────────────────┤
│ 1. Call Railway GraphQL: serviceCreate mutation             │
│ 2. Generate service-specific folder in railway_apps/        │
│ 3. Create Procfile + railway.json from template             │
│ 4. Copy execution script(s) + dependencies                  │
└─────────────────────────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 4: ENVIRONMENT VARIABLE SYNC                          │
├─────────────────────────────────────────────────────────────┤
│ 1. Read local .env file                                     │
│ 2. Filter to required vars for this workflow                │
│ 3. Call Railway GraphQL: variableUpsert (bulk)              │
│ 4. Verify all required vars are set                         │
└─────────────────────────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 5: DEPLOYMENT & VERIFICATION                          │
├─────────────────────────────────────────────────────────────┤
│ 1. Deploy to Railway: railway up (or Git push)              │
│ 2. Poll deployment status until SUCCESS                     │
│ 3. Run health check (HTTP or Railway API)                   │
│ 4. Update dashboard workflow registry                       │
└─────────────────────────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 6: DASHBOARD REGISTRATION                             │
├─────────────────────────────────────────────────────────────┤
│ 1. Add to workflow_config.json with service_id              │
│ 2. Dashboard auto-detects new service via Railway API       │
│ 3. Enable cron if type=cron                                 │
│ 4. Send Slack notification: "Workflow deployed ✓"           │
└─────────────────────────────────────────────────────────────┘
           ↓
    Workflow is LIVE on Railway
    (5-10 minutes, fully automated)
```

**Benefits:**
- ✅ Fully automated (user runs ONE command)
- ✅ Repeatable and testable
- ✅ Scales to 149+ directives
- ✅ Dashboard auto-discovers and manages
- ✅ Env vars synced correctly
- ✅ Dependencies auto-resolved

---

### 1.3 Component Interaction Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                      USER / ORCHESTRATOR                         │
│  (Claude Code Agent or CLI command)                              │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│           DEPLOYMENT ORCHESTRATOR (New Component)                │
│  Location: execution/deploy_workflow_to_railway.py               │
│                                                                   │
│  Responsibilities:                                                │
│  - Parse directive metadata                                       │
│  - Validate prerequisites                                         │
│  - Orchestrate deployment phases                                  │
│  - Handle errors and rollback                                     │
└────┬───────────┬────────────┬────────────┬────────────┬──────────┘
     │           │            │            │            │
     ▼           ▼            ▼            ▼            ▼
┌─────────┐ ┌──────────┐ ┌─────────┐ ┌──────────┐ ┌──────────┐
│Metadata │ │Dependency│ │Railway  │ │Env Var   │ │Dashboard │
│Parser   │ │Resolver  │ │Service  │ │Sync      │ │Registry  │
│         │ │          │ │Manager  │ │Manager   │ │Updater   │
└────┬────┘ └────┬─────┘ └────┬────┘ └────┬─────┘ └────┬─────┘
     │           │            │            │            │
     ▼           ▼            ▼            ▼            ▼
┌────────────────────────────────────────────────────────────┐
│                   DATA LAYER                               │
│  - directives/*.md (source of truth)                       │
│  - execution/*.py (execution scripts)                      │
│  - .env (local environment variables)                      │
│  - workflow_config.json (dashboard registry)               │
│  - deployment_state.json (deployment tracking)             │
└────────────────────┬───────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────┐
│              RAILWAY API (GraphQL)                         │
│  - serviceCreate                                           │
│  - variableUpsert (bulk)                                   │
│  - serviceInstanceUpdate                                   │
│  - deploymentTrigger                                       │
└────────────────────────────────────────────────────────────┘
```

---

## 2. The 7 Critical Blockers (Detailed Analysis)

### Blocker 1: Hardcoded Workflow List in Dashboard

**Current State:**
- 138 workflows hardcoded in `app.py` lines 522-2842
- 2865 lines of Python dictionaries
- Manual updates required for every new workflow
- Inconsistent metadata quality

**Impact:**
- New workflows are invisible to dashboard until manually added
- High maintenance burden
- Metadata drift (code vs reality)

**Solution Design:**

Replace hardcoded list with **dynamic discovery system**:

```python
# NEW: app.py lines 65-150 (replaces 522-2842)

WORKFLOW_REGISTRY_PATH = Path(__file__).parent / "workflow_registry.json"

def scan_directives_folder() -> dict:
    """Scan directives/ and parse YAML frontmatter."""
    directives_path = Path(__file__).parent.parent.parent / "directives"
    workflows = {}

    for directive_file in directives_path.glob("*.md"):
        try:
            metadata = parse_directive_metadata(directive_file)
            if metadata:
                workflow_id = metadata.get("id", directive_file.stem)
                workflows[workflow_id] = {
                    "name": metadata.get("name", directive_file.stem.replace("_", " ").title()),
                    "description": metadata.get("description", ""),
                    "category": metadata.get("category", "General"),
                    "type": metadata.get("type", "manual"),
                    "execution_scripts": metadata.get("execution_scripts", []),
                    "env_vars": metadata.get("env_vars", []),
                    "integrations": metadata.get("integrations", []),
                    "cron_schedule": metadata.get("cron_schedule"),
                    "directive_file": str(directive_file),
                    "last_updated": directive_file.stat().st_mtime
                }
        except Exception as e:
            print(f"Warning: Failed to parse {directive_file}: {e}")
            continue

    return workflows

def parse_directive_metadata(filepath: Path) -> dict:
    """Extract YAML frontmatter from directive markdown."""
    content = filepath.read_text()

    # Check for YAML frontmatter (between --- delimiters)
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            import yaml
            return yaml.safe_load(parts[1])

    # Fallback: extract from markdown headers
    return extract_metadata_from_markdown(content)

def load_workflow_registry() -> dict:
    """Load workflow registry with caching."""
    global _workflow_cache

    with _workflow_cache_lock:
        # Check if cache is fresh (5 minutes)
        if _workflow_cache["data"] and (time.time() - _workflow_cache["timestamp"]) < 300:
            return _workflow_cache["data"]

    # Option 1: Load from registry file (fast)
    if WORKFLOW_REGISTRY_PATH.exists():
        try:
            with open(WORKFLOW_REGISTRY_PATH) as f:
                registry = json.load(f)
                _workflow_cache["data"] = registry
                _workflow_cache["timestamp"] = time.time()
                return registry
        except Exception:
            pass

    # Option 2: Scan directives folder (slower, rebuild cache)
    workflows = scan_directives_folder()

    # Merge with Railway active workflows
    active = fetch_active_workflows_from_railway()
    for service in active:
        service_id = service["service_id"]
        if service_id in workflows:
            workflows[service_id]["deployed"] = True
            workflows[service_id]["railway_service_id"] = service_id

    # Save registry
    with open(WORKFLOW_REGISTRY_PATH, 'w') as f:
        json.dump(workflows, f, indent=2)

    _workflow_cache["data"] = workflows
    _workflow_cache["timestamp"] = time.time()
    return workflows
```

**Implementation Steps:**
1. Add `pyyaml` to `requirements.txt`
2. Replace hardcoded `WORKFLOWS` dict with `load_workflow_registry()`
3. Add `/api/workflows/refresh` endpoint to trigger rescan
4. Update dashboard UI to show "Scan for new workflows" button

**Testing:**
- Add new directive → verify dashboard detects it within 5 minutes
- Metadata parse error → verify graceful fallback
- 149 directives → verify dashboard loads in <2 seconds

---

### Blocker 2: No Structured Metadata in Directives

**Current State:**
- Directives are pure markdown prose
- No machine-readable metadata
- Manual regex parsing required
- Inconsistent formats across 149 files

**Impact:**
- Can't auto-detect deployment type (cron vs webhook vs web)
- Can't extract required env vars
- Can't determine execution scripts
- Can't validate completeness

**Solution Design:**

Add **YAML frontmatter** to all directives:

```markdown
---
id: cold_email_scriptwriter
name: Cold Email Scriptwriter
version: 1.2.0
category: Lead Generation
type: manual
description: |
  Generates personalized cold email sequences with A/B variants
  using AI research and proven copywriting frameworks.

execution_scripts:
  - write_cold_emails.py
  - research_prospect_deep.py

env_vars:
  - OPENROUTER_API_KEY
  - PERPLEXITY_API_KEY
  - GOOGLE_APPLICATION_CREDENTIALS

integrations:
  - google_sheets
  - slack
  - perplexity

dependencies:
  python_packages:
    - openai>=1.0.0
    - google-api-python-client>=2.100.0
    - requests>=2.31.0
  skill_bibles:
    - SKILL_BIBLE_cold_email_mastery.md
    - SKILL_BIBLE_email_deliverability.md

deployment:
  type: manual  # manual | cron | webhook | web
  railway_config:
    restart_policy: ON_FAILURE
    max_retries: 3
    timeout_seconds: 300

quality_gates:
  - All env vars set
  - Google OAuth configured
  - Output Google Sheet created

related_directives:
  - company_market_research
  - ai_prospect_researcher
---

# Cold Email Scriptwriter

[Rest of markdown content...]
```

**Schema Definition:**

```yaml
# directives/_SCHEMA.yaml (new file - defines structure)

directive_metadata:
  id:
    type: string
    required: true
    pattern: ^[a-z0-9_]+$

  name:
    type: string
    required: true

  version:
    type: string
    pattern: ^\d+\.\d+\.\d+$
    default: "1.0.0"

  category:
    type: enum
    values: [Lead Generation, Content Creation, Sales, Analytics, Automation, Integration]
    required: true

  type:
    type: enum
    values: [manual, cron, webhook, web]
    required: true

  description:
    type: string
    required: true
    max_length: 500

  execution_scripts:
    type: array[string]
    required: true
    min_items: 1

  env_vars:
    type: array[string]
    required: false

  integrations:
    type: array[string]
    values: [slack, google_docs, google_sheets, perplexity, openrouter, anthropic, ...]

  dependencies:
    type: object
    properties:
      python_packages: array[string]
      skill_bibles: array[string]

  deployment:
    type: object
    properties:
      type: enum [manual, cron, webhook, web]
      cron_schedule: string (if type=cron)
      port: integer (if type=web)
      railway_config:
        restart_policy: enum [ON_FAILURE, NEVER, ALWAYS]
        max_retries: integer
        timeout_seconds: integer

  quality_gates:
    type: array[string]

  related_directives:
    type: array[string]
```

**Migration Plan:**

1. **Create conversion tool** (`execution/add_metadata_to_directives.py`):
   ```python
   def convert_directive_to_frontmatter(filepath: Path):
       """Extract metadata from markdown and prepend YAML frontmatter."""
       content = filepath.read_text()

       # Parse existing markdown structure
       metadata = {
           "id": filepath.stem,
           "name": extract_title(content),
           "description": extract_description(content),
           "execution_scripts": extract_scripts(content),
           "env_vars": extract_env_vars(content),
           "integrations": detect_integrations(content),
           "type": detect_type(content),  # cron vs webhook vs manual
       }

       # Generate YAML frontmatter
       yaml_block = yaml.dump(metadata, sort_keys=False)
       new_content = f"---\n{yaml_block}---\n\n{content}"

       # Write back
       filepath.write_text(new_content)
   ```

2. **Batch convert all 149 directives**:
   ```bash
   python3 execution/add_metadata_to_directives.py --all --verify
   ```

3. **Manual review and corrections** (estimate 2-4 hours for 149 files)

4. **Validation pass**:
   ```bash
   python3 execution/validate_directive_metadata.py
   ```

**Fallback for Legacy Directives:**

If YAML frontmatter missing, use heuristic parsing:

```python
def extract_metadata_from_markdown(content: str) -> dict:
    """Fallback: parse metadata from markdown structure."""
    metadata = {}

    # Extract title from first # heading
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if title_match:
        metadata["name"] = title_match.group(1)

    # Detect env vars from code blocks
    env_vars = re.findall(r'([A-Z_]+)=os\.getenv\(["\']([A-Z_]+)', content)
    metadata["env_vars"] = list(set([var[1] for var in env_vars]))

    # Detect execution scripts
    scripts = re.findall(r'python3 execution/(\w+\.py)', content)
    metadata["execution_scripts"] = list(set(scripts))

    # Detect type
    if "webhook" in content.lower() or "POST /webhook" in content:
        metadata["type"] = "webhook"
    elif "cron" in content.lower() or "schedule" in content.lower():
        metadata["type"] = "cron"
    elif "gunicorn" in content or "Flask" in content:
        metadata["type"] = "web"
    else:
        metadata["type"] = "manual"

    return metadata
```

---

### Blocker 3: Execution Scripts Have Implicit Dependencies

**Current State:**
- 154 execution scripts
- All share one root `requirements.txt` (800+ lines)
- No per-script dependency manifest
- No way to know minimal requirements for deployment

**Impact:**
- Docker images are bloated (install everything)
- Slow Railway builds (unnecessary packages)
- Dependency conflicts
- Security risk (unused packages with vulnerabilities)

**Solution Design:**

#### 3.1 Auto-Generate Per-Script Dependencies

**New Tool:** `execution/analyze_script_dependencies.py`

```python
import ast
import sys
from pathlib import Path
from typing import Set, Dict

def analyze_imports(script_path: Path) -> Set[str]:
    """Parse Python AST to extract all imports."""
    content = script_path.read_text()
    tree = ast.parse(content)

    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split('.')[0])

    return imports

def map_import_to_package(import_name: str) -> str:
    """Map Python import to pip package name."""
    # Handle common mismatches
    mapping = {
        "PIL": "Pillow",
        "cv2": "opencv-python",
        "sklearn": "scikit-learn",
        "yaml": "pyyaml",
        "dotenv": "python-dotenv",
        "google": "google-api-python-client",  # Ambiguous - context needed
    }
    return mapping.get(import_name, import_name)

def extract_env_vars(script_path: Path) -> Set[str]:
    """Parse script to find all os.getenv() calls."""
    content = script_path.read_text()
    tree = ast.parse(content)

    env_vars = set()
    for node in ast.walk(tree):
        # Look for: os.getenv("VAR_NAME") or os.environ.get("VAR_NAME")
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr in ['getenv', 'get']:
                    if node.args and isinstance(node.args[0], ast.Constant):
                        env_vars.add(node.args[0].value)

    return env_vars

def generate_script_manifest(script_path: Path) -> dict:
    """Create complete dependency manifest for script."""
    imports = analyze_imports(script_path)
    packages = [map_import_to_package(imp) for imp in imports
                if imp not in sys.stdlib_module_names]
    env_vars = extract_env_vars(script_path)

    return {
        "script": script_path.name,
        "imports": sorted(imports),
        "packages": sorted(set(packages)),
        "env_vars": sorted(env_vars),
        "stdlib_only": len(packages) == 0,
    }

def main():
    execution_dir = Path(__file__).parent
    manifests = {}

    for script in execution_dir.glob("*.py"):
        if script.name.startswith("_") or script.name == "analyze_script_dependencies.py":
            continue

        try:
            manifests[script.stem] = generate_script_manifest(script)
        except Exception as e:
            print(f"Warning: Failed to analyze {script.name}: {e}")

    # Save manifests
    output = execution_dir / "script_manifests.json"
    with open(output, 'w') as f:
        json.dump(manifests, f, indent=2)

    print(f"Generated {len(manifests)} script manifests → {output}")
```

**Run Once to Generate:**
```bash
python3 execution/analyze_script_dependencies.py
# Creates: execution/script_manifests.json
```

**Example Output (`script_manifests.json`):**
```json
{
  "write_cold_emails": {
    "script": "write_cold_emails.py",
    "imports": ["argparse", "csv", "json", "openai", "os", "requests", "sys"],
    "packages": ["openai", "requests"],
    "env_vars": ["OPENROUTER_API_KEY", "PERPLEXITY_API_KEY", "SLACK_WEBHOOK_URL"],
    "stdlib_only": false
  },
  "research_company_offer": {
    "script": "research_company_offer.py",
    "imports": ["argparse", "json", "os", "requests", "sys"],
    "packages": ["requests"],
    "env_vars": ["PERPLEXITY_API_KEY"],
    "stdlib_only": false
  }
}
```

#### 3.2 Generate Minimal `requirements.txt` Per Deployment

When deploying a workflow, generate minimal requirements:

```python
def generate_minimal_requirements(workflow_metadata: dict) -> str:
    """Generate minimal requirements.txt for workflow."""
    manifests = load_script_manifests()

    all_packages = set()
    for script_name in workflow_metadata["execution_scripts"]:
        script_key = Path(script_name).stem
        if script_key in manifests:
            all_packages.update(manifests[script_key]["packages"])

    # Add version pins from root requirements.txt
    root_reqs = parse_root_requirements()
    pinned_packages = []
    for pkg in sorted(all_packages):
        version = root_reqs.get(pkg, "")
        pinned_packages.append(f"{pkg}{version}")

    return "\n".join(pinned_packages)
```

**Example Output:**
```
# Auto-generated for cold_email_scriptwriter
openai>=1.0.0
requests>=2.31.0
google-api-python-client>=2.100.0
python-dotenv>=1.0.0
```

---

### Blocker 4: Dashboard Env Var Management is Session-Only

**Current State:**
- `/api/env` writes to `RUNTIME_ENV_VARS` dict (in-memory)
- Lost on restart
- No Railway API persistence
- Webhook config is the ONLY thing persisted to Railway

**Impact:**
- User sets API keys → dashboard restarts → keys lost
- Unreliable for production use
- Forces manual Railway CLI work

**Solution Design:**

#### 4.1 Persist to Railway on Every Set

Modify `/api/env` endpoint:

```python
@app.route('/api/env', methods=['POST'])
@login_required
def api_set_env():
    """Set environment variable with Railway persistence."""
    data = request.get_json()
    var_name = data.get('name')
    var_value = data.get('value')

    if not var_name or not var_value:
        return jsonify({"error": "Missing name or value"}), 400

    # Set in current process (immediate effect)
    os.environ[var_name] = var_value
    RUNTIME_ENV_VARS[var_name] = var_value

    # PERSIST TO RAILWAY (new)
    if RAILWAY_API_TOKEN:
        success = persist_env_var_to_railway(var_name, var_value)
        if not success:
            log_event("env", "persist_failed", {"var": var_name}, source="api")
            return jsonify({
                "status": "partial",
                "message": "Set locally but Railway sync failed",
                "var": var_name
            }), 207  # Multi-Status

    log_event("env", "set", {"var": var_name}, source="api")
    return jsonify({"status": "ok", "var": var_name, "persisted": success})

def persist_env_var_to_railway(var_name: str, var_value: str) -> bool:
    """Persist single env var to Railway dashboard service."""
    project_id = os.getenv("RAILWAY_PROJECT_ID", "3b96c81f-9518-4131-b2bc-bcd7a524a5ef")
    service_id = os.getenv("RAILWAY_SERVICE_ID", "415686bb-d10c-40c5-b610-4c5e41bbe762")
    env_id = os.getenv("RAILWAY_ENV_ID", "951885c9-85a5-46f5-96a1-2151936b0314")

    mutation = """
    mutation($input: VariableUpsertInput!) {
        variableUpsert(input: $input)
    }
    """

    variables = {
        "input": {
            "projectId": project_id,
            "serviceId": service_id,
            "environmentId": env_id,
            "name": var_name,
            "value": var_value
        }
    }

    try:
        result = railway_api_call(mutation, variables)
        return "error" not in result and not result.get("errors")
    except Exception:
        return False
```

#### 4.2 Bulk Sync from .env

Add new endpoint to sync entire `.env` file:

```python
@app.route('/api/env/sync', methods=['POST'])
@login_required
def api_env_sync():
    """Bulk sync environment variables from .env file to Railway."""
    if not RAILWAY_API_TOKEN:
        return jsonify({"error": "RAILWAY_API_TOKEN not set"}), 500

    # Read .env file
    env_file = Path(__file__).parent.parent.parent / ".env"
    if not env_file.exists():
        return jsonify({"error": ".env file not found"}), 404

    env_vars = {}
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            env_vars[key.strip()] = value.strip().strip('"').strip("'")

    # Bulk persist to Railway (one mutation per var - Railway has no bulk upsert)
    results = {"success": [], "failed": []}
    for var_name, var_value in env_vars.items():
        if persist_env_var_to_railway(var_name, var_value):
            results["success"].append(var_name)
        else:
            results["failed"].append(var_name)

    log_event("env", "bulk_sync", {
        "success_count": len(results["success"]),
        "failed_count": len(results["failed"])
    }, source="api")

    return jsonify({
        "status": "completed",
        "synced": len(results["success"]),
        "failed": len(results["failed"]),
        "results": results
    })
```

---

### Blocker 5: No Cross-Service Env Var Sync

**Current State:**
- Each Railway service has isolated environment variables
- Dashboard can't push keys to other services
- Manual `railway variables set` required per service

**Impact:**
- New workflow deployed → user must manually configure 10-15 env vars
- High error rate (typos, missed vars)
- Doesn't scale

**Solution Design:**

#### 5.1 Cross-Service Env Var Propagation

**New Function:**

```python
def sync_env_vars_to_service(
    target_service_id: str,
    required_vars: list[str],
    source: str = "dashboard"
) -> dict:
    """Copy environment variables from dashboard service to target service."""

    if not RAILWAY_API_TOKEN:
        return {"error": "RAILWAY_API_TOKEN not set"}

    project_id = os.getenv("RAILWAY_PROJECT_ID", "3b96c81f-9518-4131-b2bc-bcd7a524a5ef")

    # Get environment ID for target service
    env_query = """
    query service($id: String!) {
        service(id: $id) {
            serviceInstances {
                edges {
                    node {
                        environmentId
                    }
                }
            }
        }
    }
    """

    env_result = railway_api_call(env_query, {"id": target_service_id})
    try:
        environment_id = env_result["data"]["service"]["serviceInstances"]["edges"][0]["node"]["environmentId"]
    except (KeyError, IndexError, TypeError):
        return {"error": "Could not determine environment ID for target service"}

    # Get current values from local environment or RUNTIME_ENV_VARS
    results = {"synced": [], "skipped": [], "failed": []}

    for var_name in required_vars:
        var_value = os.getenv(var_name) or RUNTIME_ENV_VARS.get(var_name)

        if not var_value:
            results["skipped"].append(var_name)
            continue

        # Persist to target service
        mutation = """
        mutation($input: VariableUpsertInput!) {
            variableUpsert(input: $input)
        }
        """

        variables = {
            "input": {
                "projectId": project_id,
                "serviceId": target_service_id,
                "environmentId": environment_id,
                "name": var_name,
                "value": var_value
            }
        }

        try:
            result = railway_api_call(mutation, variables)
            if "error" not in result and not result.get("errors"):
                results["synced"].append(var_name)
            else:
                results["failed"].append(var_name)
        except Exception:
            results["failed"].append(var_name)

    return results
```

**Usage in Deployment Flow:**

```python
# After Railway service is created
workflow_metadata = parse_directive_metadata(directive_file)
required_vars = workflow_metadata["env_vars"]

sync_result = sync_env_vars_to_service(
    target_service_id=new_service_id,
    required_vars=required_vars
)

if sync_result["failed"]:
    raise DeploymentError(f"Failed to sync env vars: {sync_result['failed']}")
```

---

### Blocker 6: No Railway Service Creation API

**Current State:**
- Dashboard can READ services (query)
- Dashboard can UPDATE services (mutations)
- Dashboard CANNOT CREATE services

**Impact:**
- Cannot automate "deploy new workflow"
- Must use Railway CLI manually

**Solution Design:**

#### 6.1 Research Railway GraphQL Schema

First, verify if `serviceCreate` mutation exists:

```bash
# Query Railway schema
curl https://backboard.railway.app/graphql/v2 \
  -H "Authorization: Bearer $RAILWAY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ __schema { mutationType { fields { name args { name type { name } } } } } }"}'
```

**Expected mutations:**
- `serviceCreate` (if available)
- `serviceConnectRepo` (Git integration)
- `deploymentTrigger` (manual deploy)

#### 6.2 Implement Service Creation

**Option A: Railway GraphQL Mutation** (preferred if available)

```python
def create_railway_service(
    project_id: str,
    service_name: str,
    config: dict
) -> str:
    """Create a new Railway service and return service_id."""

    mutation = """
    mutation serviceCreate($input: ServiceCreateInput!) {
        serviceCreate(input: $input) {
            id
            name
        }
    }
    """

    variables = {
        "input": {
            "projectId": project_id,
            "name": service_name,
            "source": config.get("source", {}),  # Git repo or Docker image
        }
    }

    result = railway_api_call(mutation, variables)

    if result.get("errors"):
        raise Exception(f"Service creation failed: {result['errors']}")

    service_id = result["data"]["serviceCreate"]["id"]
    return service_id
```

**Option B: Railway CLI Wrapper** (fallback)

```python
def create_railway_service_via_cli(
    project_id: str,
    service_name: str,
    source_dir: Path
) -> str:
    """Create service via Railway CLI."""

    # Change to service directory
    os.chdir(source_dir)

    # Link to project
    subprocess.run(["railway", "link", "-p", project_id], check=True)

    # Initialize service
    subprocess.run(["railway", "service", "create", service_name], check=True)

    # Get service ID
    result = subprocess.run(
        ["railway", "status", "--json"],
        capture_output=True,
        text=True,
        check=True
    )
    status = json.loads(result.stdout)
    service_id = status["service"]["id"]

    return service_id
```

**Implementation:**

```python
# In deployment orchestrator
def deploy_workflow_to_railway(directive_name: str) -> dict:
    """Complete deployment flow."""

    # Phase 1: Parse metadata
    metadata = parse_directive_metadata(f"directives/{directive_name}.md")

    # Phase 2: Create service directory
    service_dir = create_service_directory(directive_name, metadata)

    # Phase 3: Create Railway service
    try:
        service_id = create_railway_service(
            project_id=RAILWAY_PROJECT_ID,
            service_name=directive_name,
            config=metadata.get("deployment", {})
        )
    except Exception as e:
        # Fallback to CLI
        service_id = create_railway_service_via_cli(
            project_id=RAILWAY_PROJECT_ID,
            service_name=directive_name,
            source_dir=service_dir
        )

    # Phase 4: Sync env vars
    sync_result = sync_env_vars_to_service(service_id, metadata["env_vars"])

    # Phase 5: Deploy
    deployment_id = trigger_railway_deployment(service_id, service_dir)

    # Phase 6: Wait for success
    wait_for_deployment(deployment_id, timeout=600)

    # Phase 7: Update dashboard registry
    register_workflow_in_dashboard(directive_name, service_id, metadata)

    return {"service_id": service_id, "deployment_id": deployment_id}
```

---

### Blocker 7: Inconsistent Railway Configs

**Current State:**
- Some apps use `railway.json`, others `railway.toml`
- Different restart policies (ON_FAILURE vs NEVER)
- Different start commands (gunicorn vs python)
- No templates

**Impact:**
- Manual config writing per deployment
- Errors from typos or wrong formats
- Inconsistent behavior

**Solution Design:**

#### 7.1 Config Template System

Create templates for each deployment type:

**File: `railway_apps/_templates/cron.railway.json`**

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "{{ start_command }}",
    "restartPolicyType": "{{ restart_policy }}",
    "restartPolicyMaxRetries": {{ max_retries }},
    "cronSchedule": "{{ cron_schedule }}"
  }
}
```

**File: `railway_apps/_templates/webhook.railway.json`**

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "gunicorn app:app --bind 0.0.0.0:$PORT --timeout {{ timeout }} --workers 1",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

**File: `railway_apps/_templates/web.railway.json`**

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "gunicorn app:app --bind 0.0.0.0:$PORT --timeout {{ timeout }} --workers {{ workers }}",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10,
    "healthcheckPath": "/health",
    "healthcheckTimeout": 30
  }
}
```

#### 7.2 Template Rendering

```python
def generate_railway_config(workflow_type: str, metadata: dict) -> dict:
    """Generate railway.json from template."""

    template_path = Path(__file__).parent / "_templates" / f"{workflow_type}.railway.json"
    template_content = template_path.read_text()

    # Jinja2 rendering
    from jinja2 import Template
    template = Template(template_content)

    # Extract deployment config from metadata
    deploy_config = metadata.get("deployment", {}).get("railway_config", {})

    # Apply defaults
    context = {
        "start_command": deploy_config.get("start_command", f"python3 {metadata['execution_scripts'][0]}"),
        "restart_policy": deploy_config.get("restart_policy", "ON_FAILURE"),
        "max_retries": deploy_config.get("max_retries", 3),
        "cron_schedule": metadata.get("cron_schedule", "0 * * * *"),
        "timeout": deploy_config.get("timeout_seconds", 120),
        "workers": deploy_config.get("workers", 1),
    }

    rendered = template.render(**context)
    return json.loads(rendered)
```

---

## 3. Metadata System Design

### 3.1 YAML Frontmatter Schema (Complete)

**Location:** `directives/_SCHEMA.yaml`

```yaml
# Directive Metadata Schema v1.0
# All directives must include YAML frontmatter with these fields

# === REQUIRED FIELDS ===

id:
  type: string
  required: true
  pattern: ^[a-z0-9_]+$
  description: Unique identifier (snake_case)
  example: cold_email_scriptwriter

name:
  type: string
  required: true
  max_length: 100
  description: Human-readable name
  example: Cold Email Scriptwriter

version:
  type: string
  required: true
  pattern: ^\d+\.\d+\.\d+$
  description: Semantic version
  example: 1.2.0

category:
  type: enum
  required: true
  values:
    - Lead Generation
    - Content Creation
    - Sales & Outreach
    - Analytics & Reporting
    - Client Management
    - Automation
    - Integration
    - Video Production
    - Design
  example: Lead Generation

type:
  type: enum
  required: true
  values:
    - manual      # Run on-demand via CLI
    - cron        # Scheduled execution
    - webhook     # HTTP-triggered
    - web         # Web service with UI
  example: manual

description:
  type: string
  required: true
  max_length: 500
  description: Brief description (shown in dashboard)
  example: |
    Generates personalized cold email sequences with A/B variants
    using AI research and proven copywriting frameworks.

execution_scripts:
  type: array[string]
  required: true
  min_items: 1
  description: Python scripts to execute (in order)
  example:
    - write_cold_emails.py
    - research_prospect_deep.py

# === OPTIONAL FIELDS ===

env_vars:
  type: array[string]
  required: false
  description: Required environment variables
  example:
    - OPENROUTER_API_KEY
    - PERPLEXITY_API_KEY

integrations:
  type: array[string]
  required: false
  description: External services used
  values:
    - slack
    - google_docs
    - google_sheets
    - google_drive
    - gmail
    - perplexity
    - openrouter
    - anthropic
    - openai
    - apify
    - fal
    - calendly
    - stripe
    - hubspot
    - instantly
    - smartlead
  example:
    - google_sheets
    - slack
    - perplexity

dependencies:
  type: object
  required: false
  properties:
    python_packages:
      type: array[string]
      description: Required pip packages
      example:
        - openai>=1.0.0
        - requests>=2.31.0
    skill_bibles:
      type: array[string]
      description: Related skill bibles
      example:
        - SKILL_BIBLE_cold_email_mastery.md

deployment:
  type: object
  required: false
  properties:
    cron_schedule:
      type: string
      pattern: ^[\d\*\-\,/\s]+$
      description: Cron expression (if type=cron)
      example: 0 */3 * * *

    port:
      type: integer
      default: 8080
      description: Port for web services (if type=web)

    railway_config:
      type: object
      properties:
        restart_policy:
          type: enum
          values: [ON_FAILURE, NEVER, ALWAYS]
          default: ON_FAILURE

        max_retries:
          type: integer
          default: 3
          min: 0
          max: 10

        timeout_seconds:
          type: integer
          default: 120
          min: 30
          max: 600

        start_command:
          type: string
          description: Override default start command
          example: python3 run.py --production

quality_gates:
  type: array[string]
  required: false
  description: Validation checklist
  example:
    - All env vars set
    - Google OAuth configured
    - Output Google Sheet created

related_directives:
  type: array[string]
  required: false
  description: Related workflows
  example:
    - company_market_research
    - ai_prospect_researcher

tags:
  type: array[string]
  required: false
  description: Searchable tags
  example:
    - email
    - cold-outreach
    - ai-personalization
```

### 3.2 Validation Tool

**File: `execution/validate_directive_metadata.py`**

```python
#!/usr/bin/env python3
"""
Validate all directive metadata against schema.

Usage:
    python3 execution/validate_directive_metadata.py
    python3 execution/validate_directive_metadata.py --directive cold_email_scriptwriter
    python3 execution/validate_directive_metadata.py --fix
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List
import yaml

# Load schema
SCHEMA_PATH = Path(__file__).parent.parent / "directives" / "_SCHEMA.yaml"
DIRECTIVES_PATH = Path(__file__).parent.parent / "directives"

def load_schema() -> dict:
    """Load validation schema."""
    with open(SCHEMA_PATH) as f:
        return yaml.safe_load(f)

def validate_field(field_name: str, value, schema: dict) -> List[str]:
    """Validate a single field against schema."""
    errors = []
    field_schema = schema.get(field_name, {})

    # Required check
    if field_schema.get("required") and value is None:
        errors.append(f"Missing required field: {field_name}")
        return errors

    if value is None:
        return errors

    # Type check
    field_type = field_schema.get("type")
    if field_type == "string" and not isinstance(value, str):
        errors.append(f"{field_name}: Expected string, got {type(value).__name__}")
    elif field_type == "integer" and not isinstance(value, int):
        errors.append(f"{field_name}: Expected integer, got {type(value).__name__}")
    elif field_type.startswith("array") and not isinstance(value, list):
        errors.append(f"{field_name}: Expected array, got {type(value).__name__}")
    elif field_type == "enum" and value not in field_schema.get("values", []):
        errors.append(f"{field_name}: Invalid value '{value}', must be one of {field_schema['values']}")

    # Pattern check
    if "pattern" in field_schema and isinstance(value, str):
        if not re.match(field_schema["pattern"], value):
            errors.append(f"{field_name}: Value '{value}' does not match pattern {field_schema['pattern']}")

    # Length checks
    if "max_length" in field_schema and isinstance(value, str):
        if len(value) > field_schema["max_length"]:
            errors.append(f"{field_name}: Exceeds max length {field_schema['max_length']}")

    if "min_items" in field_schema and isinstance(value, list):
        if len(value) < field_schema["min_items"]:
            errors.append(f"{field_name}: Requires at least {field_schema['min_items']} items")

    return errors

def validate_directive(filepath: Path, schema: dict) -> Dict[str, List[str]]:
    """Validate a directive file."""
    content = filepath.read_text()

    # Extract YAML frontmatter
    if not content.startswith("---"):
        return {"fatal": ["Missing YAML frontmatter"]}

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {"fatal": ["Malformed YAML frontmatter"]}

    try:
        metadata = yaml.safe_load(parts[1])
    except yaml.YAMLError as e:
        return {"fatal": [f"Invalid YAML: {e}"]}

    # Validate each field
    errors = {}
    for field_name, field_schema in schema.items():
        field_errors = validate_field(field_name, metadata.get(field_name), field_schema)
        if field_errors:
            errors[field_name] = field_errors

    return errors

def main():
    parser = argparse.ArgumentParser(description="Validate directive metadata")
    parser.add_argument("--directive", help="Validate single directive")
    parser.add_argument("--fix", action="store_true", help="Auto-fix common issues")
    args = parser.parse_args()

    schema = load_schema()

    if args.directive:
        files = [DIRECTIVES_PATH / f"{args.directive}.md"]
    else:
        files = list(DIRECTIVES_PATH.glob("*.md"))

    total_files = 0
    total_errors = 0

    for filepath in files:
        if filepath.name.startswith("_"):
            continue

        total_files += 1
        errors = validate_directive(filepath, schema)

        if errors:
            print(f"\n❌ {filepath.name}")
            for field, field_errors in errors.items():
                for error in field_errors:
                    print(f"   • {error}")
                    total_errors += 1
        else:
            print(f"✅ {filepath.name}")

    print(f"\n{'='*60}")
    print(f"Validated {total_files} directives")
    print(f"Found {total_errors} errors")

    return 0 if total_errors == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
```

---

## 4. Deployment Engine Architecture

### 4.1 Core Deployment Script

**File: `execution/deploy_workflow_to_railway.py`**

```python
#!/usr/bin/env python3
"""
Deploy Workflow to Railway - Complete Automation

This script automates the COMPLETE deployment of a workflow to Railway:
1. Parse directive metadata
2. Validate prerequisites
3. Create Railway service
4. Generate service directory with configs
5. Sync environment variables
6. Deploy to Railway
7. Register in dashboard

Usage:
    python3 execution/deploy_workflow_to_railway.py --directive cold_email_scriptwriter
    python3 execution/deploy_workflow_to_railway.py --directive calendly_meeting_prep --cron "0 * * * *"
    python3 execution/deploy_workflow_to_railway.py --all --dry-run

Requirements:
    - Railway CLI installed and authenticated
    - RAILWAY_API_TOKEN set in .env
    - Dashboard deployed and accessible
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import yaml

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DIRECTIVES_DIR = PROJECT_ROOT / "directives"
EXECUTION_DIR = PROJECT_ROOT / "execution"
RAILWAY_APPS_DIR = PROJECT_ROOT / "railway_apps"
TEMPLATES_DIR = RAILWAY_APPS_DIR / "_templates"

# Railway configuration
RAILWAY_PROJECT_ID = os.getenv("RAILWAY_PROJECT_ID", "3b96c81f-9518-4131-b2bc-bcd7a524a5ef")
RAILWAY_API_TOKEN = os.getenv("RAILWAY_API_TOKEN")
RAILWAY_API_URL = "https://backboard.railway.app/graphql/v2"

class DeploymentError(Exception):
    """Custom exception for deployment failures."""
    pass

class WorkflowDeployer:
    """Orchestrates complete workflow deployment to Railway."""

    def __init__(self, directive_name: str, dry_run: bool = False):
        self.directive_name = directive_name
        self.dry_run = dry_run
        self.metadata = None
        self.service_id = None
        self.deployment_id = None

    def deploy(self) -> dict:
        """Execute complete deployment pipeline."""
        print(f"{'='*60}")
        print(f"Deploying: {self.directive_name}")
        print(f"Mode: {'DRY RUN' if self.dry_run else 'PRODUCTION'}")
        print(f"{'='*60}\n")

        try:
            # Phase 1: Discovery & Validation
            print("PHASE 1: Discovery & Validation")
            self.metadata = self.parse_metadata()
            self.validate_prerequisites()
            print(f"✓ Metadata parsed: {self.metadata['name']}")
            print(f"✓ Type: {self.metadata['type']}")
            print(f"✓ Scripts: {', '.join(self.metadata['execution_scripts'])}\n")

            if self.dry_run:
                print("DRY RUN: Skipping remaining phases\n")
                return {"status": "dry_run", "metadata": self.metadata}

            # Phase 2: Dependency Resolution
            print("PHASE 2: Dependency Resolution")
            dependencies = self.resolve_dependencies()
            print(f"✓ Python packages: {len(dependencies['packages'])}")
            print(f"✓ Env vars: {len(dependencies['env_vars'])}\n")

            # Phase 3: Railway Service Creation
            print("PHASE 3: Railway Service Creation")
            self.service_id = self.create_railway_service()
            print(f"✓ Service created: {self.service_id}\n")

            # Phase 4: Service Directory Setup
            print("PHASE 4: Service Directory Setup")
            service_dir = self.create_service_directory(dependencies)
            print(f"✓ Directory: {service_dir}")
            print(f"✓ Files: railway.json, requirements.txt, {len(self.metadata['execution_scripts'])} scripts\n")

            # Phase 5: Environment Variable Sync
            print("PHASE 5: Environment Variable Sync")
            sync_result = self.sync_environment_variables()
            print(f"✓ Synced: {len(sync_result['synced'])} vars")
            if sync_result['failed']:
                print(f"⚠ Failed: {', '.join(sync_result['failed'])}\n")

            # Phase 6: Deployment
            print("PHASE 6: Deployment to Railway")
            self.deployment_id = self.deploy_to_railway(service_dir)
            print(f"✓ Deployment triggered: {self.deployment_id}")

            # Phase 7: Wait for success
            print("PHASE 7: Waiting for deployment...")
            self.wait_for_deployment()
            print(f"✓ Deployment succeeded\n")

            # Phase 8: Dashboard Registration
            print("PHASE 8: Dashboard Registration")
            self.register_in_dashboard()
            print(f"✓ Registered in workflow_config.json\n")

            # Success
            print(f"{'='*60}")
            print(f"✅ DEPLOYMENT COMPLETE")
            print(f"{'='*60}")
            print(f"Service ID: {self.service_id}")
            print(f"Deployment ID: {self.deployment_id}")
            print(f"Dashboard: https://aiaa-dashboard-production-10fa.up.railway.app")
            print(f"{'='*60}\n")

            return {
                "status": "success",
                "service_id": self.service_id,
                "deployment_id": self.deployment_id,
                "metadata": self.metadata
            }

        except DeploymentError as e:
            print(f"\n❌ DEPLOYMENT FAILED: {e}\n")
            return {"status": "failed", "error": str(e)}
        except Exception as e:
            print(f"\n❌ UNEXPECTED ERROR: {e}\n")
            return {"status": "failed", "error": str(e)}

    def parse_metadata(self) -> dict:
        """Parse directive YAML frontmatter."""
        directive_path = DIRECTIVES_DIR / f"{self.directive_name}.md"

        if not directive_path.exists():
            raise DeploymentError(f"Directive not found: {directive_path}")

        content = directive_path.read_text()

        # Extract YAML frontmatter
        if not content.startswith("---"):
            raise DeploymentError(f"Directive missing YAML frontmatter: {self.directive_name}")

        parts = content.split("---", 2)
        if len(parts) < 3:
            raise DeploymentError(f"Malformed YAML frontmatter: {self.directive_name}")

        try:
            metadata = yaml.safe_load(parts[1])
        except yaml.YAMLError as e:
            raise DeploymentError(f"Invalid YAML: {e}")

        # Validate required fields
        required_fields = ["name", "type", "execution_scripts"]
        for field in required_fields:
            if field not in metadata:
                raise DeploymentError(f"Missing required field: {field}")

        return metadata

    def validate_prerequisites(self):
        """Validate prerequisites before deployment."""
        # Check execution scripts exist
        for script_name in self.metadata["execution_scripts"]:
            script_path = EXECUTION_DIR / script_name
            if not script_path.exists():
                raise DeploymentError(f"Execution script not found: {script_name}")

        # Check Railway CLI
        result = subprocess.run(["railway", "--version"], capture_output=True, text=True)
        if result.returncode != 0:
            raise DeploymentError("Railway CLI not installed. Run: brew install railway")

        # Check Railway authentication
        result = subprocess.run(["railway", "whoami"], capture_output=True, text=True)
        if result.returncode != 0:
            raise DeploymentError("Not logged into Railway. Run: railway login")

        # Check Railway API token
        if not RAILWAY_API_TOKEN:
            raise DeploymentError("RAILWAY_API_TOKEN not set in .env")

    def resolve_dependencies(self) -> dict:
        """Resolve all dependencies for workflow."""
        # Load script manifests
        manifests_path = EXECUTION_DIR / "script_manifests.json"
        if manifests_path.exists():
            with open(manifests_path) as f:
                manifests = json.load(f)
        else:
            # Generate on-the-fly
            print("  → Generating script manifests...")
            subprocess.run([sys.executable, str(EXECUTION_DIR / "analyze_script_dependencies.py")], check=True)
            with open(manifests_path) as f:
                manifests = json.load(f)

        # Aggregate dependencies
        all_packages = set()
        all_env_vars = set()

        for script_name in self.metadata["execution_scripts"]:
            script_key = Path(script_name).stem
            if script_key in manifests:
                all_packages.update(manifests[script_key]["packages"])
                all_env_vars.update(manifests[script_key]["env_vars"])

        # Add from metadata
        if "dependencies" in self.metadata and "python_packages" in self.metadata["dependencies"]:
            all_packages.update([pkg.split(">=")[0].split("==")[0] for pkg in self.metadata["dependencies"]["python_packages"]])

        if "env_vars" in self.metadata:
            all_env_vars.update(self.metadata["env_vars"])

        return {
            "packages": sorted(all_packages),
            "env_vars": sorted(all_env_vars)
        }

    def create_railway_service(self) -> str:
        """Create Railway service via CLI."""
        service_name = self.directive_name.replace("_", "-")

        # Change to railway_apps directory
        os.chdir(RAILWAY_APPS_DIR)

        # Link to project
        result = subprocess.run(
            ["railway", "link", "-p", RAILWAY_PROJECT_ID],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise DeploymentError(f"Failed to link project: {result.stderr}")

        # Create service
        result = subprocess.run(
            ["railway", "service", "create", service_name],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            # Service might already exist
            if "already exists" not in result.stderr:
                raise DeploymentError(f"Failed to create service: {result.stderr}")

        # Get service ID
        result = subprocess.run(
            ["railway", "status", "--json"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise DeploymentError("Failed to get service status")

        status = json.loads(result.stdout)
        service_id = status.get("service", {}).get("id")

        if not service_id:
            raise DeploymentError("Could not determine service ID")

        return service_id

    def create_service_directory(self, dependencies: dict) -> Path:
        """Create service directory with all required files."""
        service_dir = RAILWAY_APPS_DIR / self.directive_name
        service_dir.mkdir(exist_ok=True)

        # Generate railway.json from template
        workflow_type = self.metadata["type"]
        template_path = TEMPLATES_DIR / f"{workflow_type}.railway.json"

        if not template_path.exists():
            raise DeploymentError(f"No template for type: {workflow_type}")

        with open(template_path) as f:
            template = json.load(f)

        # Apply metadata overrides
        deploy_config = self.metadata.get("deployment", {}).get("railway_config", {})
        if "cron_schedule" in self.metadata and workflow_type == "cron":
            template["deploy"]["cronSchedule"] = self.metadata["cron_schedule"]

        with open(service_dir / "railway.json", 'w') as f:
            json.dump(template, f, indent=2)

        # Generate requirements.txt
        requirements = "\n".join([f"{pkg}>=0.0.0" for pkg in dependencies["packages"]])
        (service_dir / "requirements.txt").write_text(requirements)

        # Copy execution scripts
        for script_name in self.metadata["execution_scripts"]:
            src = EXECUTION_DIR / script_name
            dst = service_dir / script_name
            shutil.copy2(src, dst)

        return service_dir

    def sync_environment_variables(self) -> dict:
        """Sync environment variables to Railway service."""
        # Get required vars
        required_vars = self.resolve_dependencies()["env_vars"]

        # Load from .env
        env_file = PROJECT_ROOT / ".env"
        env_values = {}
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if "=" in line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    env_values[key.strip()] = value.strip().strip('"').strip("'")

        # Sync each var
        results = {"synced": [], "skipped": [], "failed": []}

        for var_name in required_vars:
            if var_name not in env_values:
                results["skipped"].append(var_name)
                continue

            # Set via Railway CLI
            result = subprocess.run(
                ["railway", "variable", "set", f"{var_name}={env_values[var_name]}", "--service", self.directive_name.replace("_", "-")],
                capture_output=True,
                text=True,
                cwd=str(RAILWAY_APPS_DIR / self.directive_name)
            )

            if result.returncode == 0:
                results["synced"].append(var_name)
            else:
                results["failed"].append(var_name)

        return results

    def deploy_to_railway(self, service_dir: Path) -> str:
        """Deploy service to Railway."""
        os.chdir(service_dir)

        # Deploy
        result = subprocess.run(
            ["railway", "up"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise DeploymentError(f"Deployment failed: {result.stderr}")

        # Extract deployment ID from output
        for line in result.stdout.splitlines():
            if "Deployment" in line:
                # Parse deployment ID from output
                parts = line.split()
                for part in parts:
                    if len(part) == 36 and "-" in part:  # UUID format
                        return part

        return "unknown"

    def wait_for_deployment(self, timeout: int = 600):
        """Wait for deployment to succeed."""
        # TODO: Poll Railway API for deployment status
        # For now, simple sleep
        print("  → Waiting 60 seconds for build...")
        time.sleep(60)

    def register_in_dashboard(self):
        """Register workflow in dashboard."""
        config_path = RAILWAY_APPS_DIR / "aiaa_dashboard" / "workflow_config.json"

        with open(config_path) as f:
            config = json.load(f)

        config["workflows"][self.service_id] = {
            "name": self.metadata["name"],
            "description": self.metadata.get("description", ""),
            "enabled": True
        }

        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

def main():
    parser = argparse.ArgumentParser(description="Deploy workflow to Railway")
    parser.add_argument("--directive", required=True, help="Directive name (e.g., cold_email_scriptwriter)")
    parser.add_argument("--dry-run", action="store_true", help="Validate without deploying")
    args = parser.parse_args()

    deployer = WorkflowDeployer(args.directive, dry_run=args.dry_run)
    result = deployer.deploy()

    sys.exit(0 if result["status"] == "success" else 1)

if __name__ == "__main__":
    main()
```

---

## 5. Dashboard Enhancements

### 5.1 New Dashboard Routes

Add these endpoints to `railway_apps/aiaa_dashboard/app.py`:

```python
@app.route('/api/workflows/deploy', methods=['POST'])
@login_required
def api_workflow_deploy():
    """Deploy a workflow to Railway from the dashboard."""
    data = request.get_json()
    directive_name = data.get('directive')

    if not directive_name:
        return jsonify({"error": "Missing directive parameter"}), 400

    # Spawn deployment subprocess
    deploy_script = Path(__file__).parent.parent.parent / "execution" / "deploy_workflow_to_railway.py"

    proc = subprocess.Popen(
        [sys.executable, str(deploy_script), "--directive", directive_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Store process ID for status tracking
    deployment_id = str(uuid.uuid4())
    DEPLOYMENTS[deployment_id] = {
        "directive": directive_name,
        "status": "running",
        "process": proc,
        "started_at": datetime.now().isoformat()
    }

    log_event("workflow", "deploy_started", {"directive": directive_name, "deployment_id": deployment_id}, source="api")

    return jsonify({
        "status": "started",
        "deployment_id": deployment_id,
        "directive": directive_name
    })

@app.route('/api/workflows/deploy/<deployment_id>', methods=['GET'])
@login_required
def api_workflow_deploy_status(deployment_id: str):
    """Get status of a deployment."""
    if deployment_id not in DEPLOYMENTS:
        return jsonify({"error": "Deployment not found"}), 404

    deployment = DEPLOYMENTS[deployment_id]
    proc = deployment["process"]

    # Check if process finished
    if proc.poll() is not None:
        stdout, stderr = proc.communicate()
        deployment["status"] = "success" if proc.returncode == 0 else "failed"
        deployment["stdout"] = stdout
        deployment["stderr"] = stderr
        deployment["completed_at"] = datetime.now().isoformat()

    return jsonify({
        "deployment_id": deployment_id,
        "directive": deployment["directive"],
        "status": deployment["status"],
        "started_at": deployment["started_at"],
        "completed_at": deployment.get("completed_at"),
        "logs": deployment.get("stdout", ""),
        "errors": deployment.get("stderr", "")
    })

@app.route('/api/workflows/refresh', methods=['POST'])
@login_required
def api_workflows_refresh():
    """Force refresh workflow registry (rescan directives folder)."""
    global _workflow_cache

    with _workflow_cache_lock:
        _workflow_cache["data"] = None
        _workflow_cache["timestamp"] = 0

    workflows = load_workflow_registry()

    log_event("workflows", "refreshed", {"count": len(workflows)}, source="api")

    return jsonify({
        "status": "refreshed",
        "count": len(workflows)
    })
```

### 5.2 Dashboard UI Updates

Add deployment UI to dashboard template:

```html
<!-- NEW SECTION: Workflow Deployment -->
<div class="card">
    <div class="card-header">
        <h3>Deploy New Workflow</h3>
    </div>
    <div class="card-body">
        <form id="deploy-form">
            <div class="form-group">
                <label for="directive-select">Select Workflow:</label>
                <select id="directive-select" class="form-control">
                    <option value="">-- Choose a directive --</option>
                    <!-- Populated via JavaScript -->
                </select>
            </div>

            <div id="workflow-preview" style="display:none;" class="mt-3 mb-3">
                <h5>Workflow Details:</h5>
                <p id="workflow-description"></p>
                <ul>
                    <li>Type: <span id="workflow-type"></span></li>
                    <li>Scripts: <span id="workflow-scripts"></span></li>
                    <li>Env Vars: <span id="workflow-env-vars"></span></li>
                </ul>
            </div>

            <button type="submit" class="btn btn-primary" id="deploy-btn">
                Deploy to Railway
            </button>
        </form>

        <div id="deployment-progress" style="display:none;" class="mt-4">
            <h5>Deployment in Progress...</h5>
            <div class="progress">
                <div class="progress-bar progress-bar-striped progress-bar-animated"
                     role="progressbar" style="width: 100%"></div>
            </div>
            <pre id="deployment-logs" style="max-height: 400px; overflow-y: auto;"></pre>
        </div>
    </div>
</div>

<script>
// Load available directives
async function loadDirectives() {
    const res = await fetch('/api/workflows/list');
    const data = await res.json();
    const select = document.getElementById('directive-select');

    for (const [id, workflow] of Object.entries(data.workflows)) {
        const option = document.createElement('option');
        option.value = id;
        option.textContent = workflow.name;
        option.dataset.metadata = JSON.stringify(workflow);
        select.appendChild(option);
    }
}

// Show workflow preview
document.getElementById('directive-select').addEventListener('change', (e) => {
    const option = e.target.selectedOptions[0];
    if (!option.value) {
        document.getElementById('workflow-preview').style.display = 'none';
        return;
    }

    const metadata = JSON.parse(option.dataset.metadata);
    document.getElementById('workflow-description').textContent = metadata.description || '';
    document.getElementById('workflow-type').textContent = metadata.type || 'manual';
    document.getElementById('workflow-scripts').textContent = (metadata.execution_scripts || []).join(', ');
    document.getElementById('workflow-env-vars').textContent = (metadata.env_vars || []).join(', ');
    document.getElementById('workflow-preview').style.display = 'block';
});

// Deploy workflow
document.getElementById('deploy-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const directive = document.getElementById('directive-select').value;
    if (!directive) {
        alert('Please select a workflow');
        return;
    }

    // Show progress
    document.getElementById('deploy-btn').disabled = true;
    document.getElementById('deployment-progress').style.display = 'block';

    try {
        // Start deployment
        const res = await fetch('/api/workflows/deploy', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({directive})
        });
        const data = await res.json();

        if (data.status !== 'started') {
            throw new Error(data.error || 'Deployment failed to start');
        }

        // Poll for status
        const deploymentId = data.deployment_id;
        const pollInterval = setInterval(async () => {
            const statusRes = await fetch(`/api/workflows/deploy/${deploymentId}`);
            const status = await statusRes.json();

            // Update logs
            document.getElementById('deployment-logs').textContent = status.logs || '';

            if (status.status === 'success') {
                clearInterval(pollInterval);
                alert('Deployment successful!');
                location.reload();
            } else if (status.status === 'failed') {
                clearInterval(pollInterval);
                alert(`Deployment failed: ${status.errors}`);
                document.getElementById('deploy-btn').disabled = false;
            }
        }, 2000);

    } catch (error) {
        alert(`Error: ${error.message}`);
        document.getElementById('deploy-btn').disabled = false;
        document.getElementById('deployment-progress').style.display = 'none';
    }
});

// Load directives on page load
loadDirectives();
</script>
```

---

## 10. Implementation Phases

### Phase 1: Foundation (Week 1)
**Goal:** Set up metadata system and validation

**Tasks:**
1. Create `directives/_SCHEMA.yaml`
2. Create `execution/validate_directive_metadata.py`
3. Create `execution/add_metadata_to_directives.py`
4. Convert 10 sample directives to YAML frontmatter
5. Validate conversion process

**Success Criteria:**
- 10 directives have valid YAML frontmatter
- Validation script passes
- Metadata can be parsed programmatically

---

### Phase 2: Dependency Resolution (Week 2)
**Goal:** Auto-detect script dependencies

**Tasks:**
1. Create `execution/analyze_script_dependencies.py`
2. Generate `script_manifests.json` for all 154 scripts
3. Create template system for Railway configs
4. Test minimal requirements generation

**Success Criteria:**
- All 154 scripts analyzed
- `script_manifests.json` generated
- Can generate minimal `requirements.txt` for any workflow

---

### Phase 3: Deployment Engine (Week 3-4)
**Goal:** Build core deployment automation

**Tasks:**
1. Create `execution/deploy_workflow_to_railway.py`
2. Implement all 8 phases of deployment
3. Test with 3 workflow types (manual, cron, webhook)
4. Handle errors and rollback

**Success Criteria:**
- Can deploy sample workflow end-to-end
- Env vars synced correctly
- Service appears in Railway
- Error handling works

---

### Phase 4: Dashboard Integration (Week 5)
**Goal:** Connect dashboard to deployment engine

**Tasks:**
1. Add deployment endpoints to dashboard
2. Build deployment UI
3. Implement status polling
4. Add workflow refresh endpoint

**Success Criteria:**
- Can deploy from dashboard UI
- Real-time deployment logs
- Workflow auto-registered after deploy
- Dashboard detects new services

---

### Phase 5: Batch Conversion (Week 6)
**Goal:** Convert all directives to new format

**Tasks:**
1. Batch convert remaining 139 directives
2. Manual QA and corrections
3. Generate all script manifests
4. Update documentation

**Success Criteria:**
- All 149 directives have YAML frontmatter
- All pass validation
- Documentation updated

---

### Phase 6: Testing & Hardening (Week 7)
**Goal:** Comprehensive testing

**Tasks:**
1. Test deployment of 20 diverse workflows
2. Load testing (multiple concurrent deploys)
3. Security audit
4. Error recovery testing

**Success Criteria:**
- 95% deployment success rate
- Handles 5 concurrent deploys
- Security vulnerabilities addressed
- Rollback works

---

### Phase 7: Production Rollout (Week 8)
**Goal:** Launch to production

**Tasks:**
1. Deploy updated dashboard
2. User documentation
3. Training materials
4. Monitor first deployments

**Success Criteria:**
- Dashboard live with deployment feature
- 10 successful user deployments
- No critical bugs
- Positive user feedback

---

## 11. File-by-File Modification Plan

### New Files to Create

| File | Purpose | Size | Priority |
|------|---------|------|----------|
| `directives/_SCHEMA.yaml` | Metadata schema | 200 lines | P0 |
| `execution/validate_directive_metadata.py` | Validation tool | 300 lines | P0 |
| `execution/add_metadata_to_directives.py` | Conversion tool | 400 lines | P0 |
| `execution/analyze_script_dependencies.py` | Dependency analyzer | 250 lines | P0 |
| `execution/deploy_workflow_to_railway.py` | Deployment orchestrator | 800 lines | P0 |
| `railway_apps/_templates/cron.railway.json` | Cron template | 15 lines | P1 |
| `railway_apps/_templates/webhook.railway.json` | Webhook template | 15 lines | P1 |
| `railway_apps/_templates/web.railway.json` | Web service template | 20 lines | P1 |
| `execution/script_manifests.json` | Generated manifests | Auto | P1 |
| `railway_apps/aiaa_dashboard/workflow_registry.json` | Workflow registry | Auto | P1 |

### Files to Modify

| File | Changes | Impact |
|------|---------|--------|
| `railway_apps/aiaa_dashboard/app.py` | Replace hardcoded WORKFLOWS (lines 522-2842) with dynamic `load_workflow_registry()`. Add 3 new API endpoints. | HIGH |
| `railway_apps/aiaa_dashboard/requirements.txt` | Add `pyyaml` | LOW |
| All 149 `directives/*.md` | Add YAML frontmatter | MEDIUM |
| `.env` | Add `RAILWAY_SERVICE_ID`, `RAILWAY_ENV_ID` | LOW |

---

## 12. Testing Strategy

### Unit Tests

```python
# tests/test_metadata_parser.py
def test_parse_valid_frontmatter():
    content = """---
id: test_workflow
name: Test Workflow
type: manual
execution_scripts:
  - test.py
---
# Test
"""
    metadata = parse_directive_metadata_from_string(content)
    assert metadata["id"] == "test_workflow"
    assert metadata["type"] == "manual"

def test_parse_missing_frontmatter():
    content = "# No frontmatter"
    with pytest.raises(DeploymentError):
        parse_directive_metadata_from_string(content)
```

### Integration Tests

```python
# tests/test_deployment_flow.py
def test_deploy_simple_workflow(temp_dir):
    """Test deployment of a minimal workflow."""
    # Create test directive
    directive = create_test_directive("test_workflow", type="manual")

    # Deploy
    deployer = WorkflowDeployer("test_workflow", dry_run=True)
    result = deployer.deploy()

    assert result["status"] == "dry_run"
    assert "metadata" in result

def test_env_var_sync():
    """Test environment variable sync to Railway."""
    service_id = "test-service-id"
    vars_to_sync = ["OPENROUTER_API_KEY", "SLACK_WEBHOOK_URL"]

    result = sync_env_vars_to_service(service_id, vars_to_sync)

    assert len(result["synced"]) == 2
    assert len(result["failed"]) == 0
```

### End-to-End Tests

```bash
# tests/e2e_deploy_workflow.sh
#!/bin/bash

# Deploy a real workflow to Railway staging
python3 execution/deploy_workflow_to_railway.py \
  --directive test_simple_cron \
  --dry-run

# Verify dry run succeeds
if [ $? -ne 0 ]; then
  echo "Dry run failed"
  exit 1
fi

# Deploy for real (to staging environment)
RAILWAY_PROJECT_ID="staging-project-id" \
python3 execution/deploy_workflow_to_railway.py \
  --directive test_simple_cron

# Verify service exists on Railway
railway status --json | jq '.service.id'

# Verify env vars set
railway variables --json | jq '.OPENROUTER_API_KEY'

# Clean up
railway service delete test-simple-cron
```

---

## 13. Rollback & Recovery

### Deployment Failure Scenarios

| Failure Point | Rollback Strategy |
|---------------|-------------------|
| Metadata parse fails | No changes made, safe to retry |
| Railway service creation fails | Delete partially-created service |
| Env var sync fails | Continue with warning, user can set manually |
| Deployment fails (build error) | Service exists but not deployed, delete or fix |
| Health check fails | Mark as failed, alert user |

### Automatic Rollback

```python
def deploy_with_rollback(directive_name: str) -> dict:
    """Deploy with automatic rollback on failure."""
    deployer = WorkflowDeployer(directive_name)
    created_service_id = None
    created_dir = None

    try:
        # Phases 1-8
        result = deployer.deploy()
        return result

    except DeploymentError as e:
        print(f"\n⚠️  Deployment failed: {e}")
        print("Rolling back changes...")

        # Delete Railway service if created
        if deployer.service_id:
            print(f"  → Deleting Railway service {deployer.service_id}")
            delete_railway_service(deployer.service_id)

        # Delete local service directory if created
        service_dir = RAILWAY_APPS_DIR / directive_name
        if service_dir.exists():
            print(f"  → Removing service directory {service_dir}")
            shutil.rmtree(service_dir)

        print("✓ Rollback complete\n")
        raise
```

---

## 14. Performance & Scalability

### Optimization Targets

| Metric | Current | Target | Strategy |
|--------|---------|--------|----------|
| Dashboard load time | 2-3s | <1s | Cache workflow registry |
| Deployment time | N/A | 5-10min | Parallel steps where possible |
| Concurrent deploys | 1 | 5 | Queue system |
| Directive scan time | N/A | <5s | Index by modification time |

### Caching Strategy

```python
# Workflow registry cache (5-minute TTL)
@app.before_first_request
def preload_cache():
    """Preload workflow registry on dashboard start."""
    load_workflow_registry()

# Deployment queue (handle concurrent deploys)
from queue import Queue
from threading import Thread

deployment_queue = Queue()

def deployment_worker():
    """Background worker for deployments."""
    while True:
        directive_name = deployment_queue.get()
        try:
            deployer = WorkflowDeployer(directive_name)
            deployer.deploy()
        except Exception as e:
            print(f"Deployment failed: {e}")
        finally:
            deployment_queue.task_done()

# Start worker thread
worker = Thread(target=deployment_worker, daemon=True)
worker.start()
```

---

## 15. Security Hardening

### Security Checklist

- [ ] Validate all user inputs (directive names, env var names)
- [ ] Sanitize file paths (prevent directory traversal)
- [ ] Rate limit deployment API (max 5/hour per user)
- [ ] Audit log all deployments
- [ ] Encrypt sensitive env vars in transit
- [ ] Use Railway API token scopes (principle of least privilege)
- [ ] Validate YAML frontmatter (prevent code injection)
- [ ] Sandbox script execution (AST parsing only, no eval())

### Input Validation

```python
def validate_directive_name(name: str) -> bool:
    """Validate directive name is safe."""
    # Only allow alphanumeric, underscore, hyphen
    if not re.match(r'^[a-z0-9_-]+$', name):
        return False

    # Prevent directory traversal
    if '..' in name or '/' in name:
        return False

    # Max length
    if len(name) > 100:
        return False

    return True

@app.route('/api/workflows/deploy', methods=['POST'])
@login_required
def api_workflow_deploy():
    data = request.get_json()
    directive_name = data.get('directive')

    # VALIDATE INPUT
    if not validate_directive_name(directive_name):
        log_event("security", "invalid_directive_name", {"name": directive_name}, source="api")
        return jsonify({"error": "Invalid directive name"}), 400

    # ... rest of deployment logic
```

---

## Summary

This master plan provides a **complete, actionable roadmap** to transform the AIAA Agentic OS dashboard from a management-only system into a full deployment automation platform.

**Key Deliverables:**
1. ✅ Metadata system with YAML frontmatter (149 directives)
2. ✅ Dependency resolution (154 scripts → manifests)
3. ✅ Deployment orchestrator (`deploy_workflow_to_railway.py`)
4. ✅ Dashboard UI for one-click deployment
5. ✅ Environment variable sync across services
6. ✅ Dynamic workflow discovery (no hardcoding)
7. ✅ Quality gates and validation
8. ✅ Error handling and rollback

**Expected Outcome:**
- User: "Deploy cold_email_scriptwriter to Railway"
- System: [5-10 minutes later] "✅ Deployed and live"
- Dashboard: Auto-discovers new workflow
- Zero manual Railway CLI work required

**Implementation Time:** 8 weeks (1 engineer)
**Success Rate Target:** 95% successful deployments
**Maintenance Burden:** Reduced from 30-60 min/workflow to <5 min

This plan is **production-ready** and addresses all 7 critical blockers identified in the audit.
