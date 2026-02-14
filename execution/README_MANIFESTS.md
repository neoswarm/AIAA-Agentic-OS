# Script Dependency Manifests

**Purpose:** Automated dependency analysis for all execution scripts to enable minimal Docker images, automated deployment, and environment validation.

**Generated:** 2026-02-11
**Coverage:** 152/152 scripts (100%)
**Success Rate:** 152/152 (0 failures)

---

## Quick Start

### Query a Script's Dependencies

```bash
# Show all info for a script
python3 execution/query_script_manifest.py write_cold_emails

# Check if env vars are set
python3 execution/query_script_manifest.py calendly_meeting_prep --check-env

# Generate minimal requirements.txt
python3 execution/query_script_manifest.py write_cold_emails --generate-requirements > requirements_cold_emails.txt
```

### List All Packages/Env Vars

```bash
# All packages across all scripts
python3 execution/query_script_manifest.py --list-packages

# All environment variables
python3 execution/query_script_manifest.py --list-env-vars
```

### Re-analyze Scripts

```bash
# Re-run analyzer (takes ~5 seconds)
python3 execution/analyze_script_dependencies.py

# Output: execution/script_manifests.json (updated)
```

---

## Files

| File | Purpose |
|------|---------|
| `analyze_script_dependencies.py` | AST-based analyzer that extracts imports and env vars |
| `query_script_manifest.py` | Query utility for looking up dependencies |
| `script_manifests.json` | Generated manifest data (152 scripts) |
| `DEPENDENCY_ANALYSIS_REPORT.md` | Full analysis report with validation |
| `README_MANIFESTS.md` | This file - usage guide |

---

## Manifest Format

Each script has a manifest entry:

```json
{
  "write_cold_emails": {
    "script": "write_cold_emails.py",
    "imports": ["argparse", "csv", "openai", "requests", ...],
    "packages": ["openai", "python-dotenv", "requests"],
    "env_vars": ["OPENAI_API_KEY", "OPENROUTER_API_KEY"],
    "stdlib_only": false
  }
}
```

### Fields

- **script**: Filename with .py extension
- **imports**: All imported modules (stdlib + external)
- **packages**: Only external pip packages (stdlib excluded)
- **env_vars**: Environment variables accessed via `os.getenv()` or `os.environ.get()`
- **stdlib_only**: True if no external packages required

---

## Use Cases

### 1. Minimal Docker Images

Generate a requirements.txt with only the packages a script needs:

```bash
# Create minimal requirements for a script
python3 execution/query_script_manifest.py write_cold_emails --generate-requirements > /tmp/requirements.txt

# Use in Dockerfile
FROM python:3.11-slim
COPY /tmp/requirements.txt .
RUN pip install -r requirements.txt
COPY execution/write_cold_emails.py .
CMD ["python", "write_cold_emails.py"]
```

**Benefits:**
- Faster builds (fewer packages to install)
- Smaller images (100MB vs 2GB for full install)
- Better security (reduced attack surface)

### 2. Automated Railway Deployment

Use manifests to generate Railway service configs:

```python
import json

with open('execution/script_manifests.json') as f:
    manifests = json.load(f)

manifest = manifests['write_cold_emails']

# Generate Railway config
railway_config = {
    "build": {
        "builder": "NIXPACKS",
        "buildCommand": f"pip install {' '.join(manifest['packages'])}"
    },
    "deploy": {
        "startCommand": f"python execution/{manifest['script']}"
    }
}

# Set required env vars in Railway
for var in manifest['env_vars']:
    print(f"railway variables set {var}=<value>")
```

### 3. Environment Validation

Check if all required env vars are set before running a script:

```bash
# Check specific script
python3 execution/query_script_manifest.py calendly_meeting_prep --check-env

# Output shows which vars are missing:
# ❌ MISSING  CALENDLY_API_KEY
# ❌ MISSING  PERPLEXITY_API_KEY
# ✅ SET      OPENROUTER_API_KEY
```

Or programmatically:

```python
import json
import os

with open('execution/script_manifests.json') as f:
    manifests = json.load(f)

manifest = manifests['calendly_meeting_prep']

# Check all required env vars
missing = [var for var in manifest['env_vars'] if not os.getenv(var)]

if missing:
    print(f"Missing required env vars: {', '.join(missing)}")
    exit(1)
else:
    # All good - proceed with execution
    pass
```

### 4. Documentation Generation

Auto-generate prerequisite sections for directives:

```python
manifest = manifests['write_cold_emails']

print("## Prerequisites")
print("\n**Required Packages:**")
for pkg in manifest['packages']:
    print(f"- `{pkg}`")

print("\n**Required Environment Variables:**")
for var in manifest['env_vars']:
    print(f"- `{var}`")

print("\n**Installation:**")
print("```bash")
print(f"pip install {' '.join(manifest['packages'])}")
print("```")
```

### 5. Dependency Auditing

Find all scripts using a specific package:

```bash
cat execution/script_manifests.json | jq -r '
  to_entries |
  map(select(.value.packages | contains(["anthropic"]))) |
  map(.key) |
  .[]
'
```

Find scripts requiring specific env vars:

```bash
cat execution/script_manifests.json | jq -r '
  to_entries |
  map(select(.value.env_vars | contains(["PERPLEXITY_API_KEY"]))) |
  map(.key) |
  .[]
'
```

---

## Statistics

### Overall

- **Total scripts analyzed:** 152
- **Unique packages required:** 27
- **Unique env vars required:** 54
- **Stdlib-only scripts:** 15 (no external dependencies)

### Top Packages

| Scripts | Package | Purpose |
|---------|---------|---------|
| 122 | `python-dotenv` | Load .env files |
| 68 | `openai` | OpenAI/OpenRouter API |
| 52 | `requests` | HTTP requests |
| 23 | `google-auth` | Google API authentication |
| 16 | `google-auth-oauthlib` | Google OAuth |
| 15 | `google-api-python-client` | Google Docs/Sheets/Drive |
| 13 | `anthropic` | Claude API |
| 12 | `gspread` | Google Sheets wrapper |
| 10 | `apify-client` | Web scraping |

### Top Environment Variables

| Scripts | Variable | Purpose |
|---------|----------|---------|
| 78 | `OPENROUTER_API_KEY` | Multi-LLM access via OpenRouter |
| 67 | `OPENAI_API_KEY` | Direct OpenAI API access |
| 23 | `PERPLEXITY_API_KEY` | Perplexity research API |
| 12 | `APIFY_API_TOKEN` | Apify web scraping |
| 12 | `ANTHROPIC_API_KEY` | Direct Claude API access |
| 10 | `GOOGLE_APPLICATION_CREDENTIALS` | Google service account |
| 7 | `SLACK_WEBHOOK_URL` | Slack notifications |

### Complexity Distribution

**Most Complex (packages + env vars):**
1. `stripe_client_onboarding.py` - 7 packages, 12 env vars
2. `modal_webhook.py` - 9 packages, 7 env vars
3. `generate_product_photoshoot.py` - 6 packages, 7 env vars

**Simplest (stdlib only, no env vars):**
- `alert_churn_risk.py`
- `calculate_client_health.py`
- `convert_n8n_to_directive.py`
- `dedupe_leads.py`
- `generate_ab_test_analysis.py`
- `generate_invoice.py`
- `generate_utm.py`

---

## How the Analyzer Works

### AST-Based Static Analysis

The analyzer uses Python's `ast` module to parse scripts without executing them:

1. **Parse Python file** → AST (Abstract Syntax Tree)
2. **Visit all import nodes** → Extract module names
3. **Visit all function calls** → Find `os.getenv("VAR")` and `os.environ.get("VAR")`
4. **Map imports to packages** → Handle special cases (PIL→Pillow, cv2→opencv-python)
5. **Filter stdlib** → Remove standard library modules
6. **Filter local imports** → Remove execution script cross-imports
7. **Generate manifest** → JSON with packages, env vars, imports

### Import Name Mapping

Some imports don't match their pip package name:

| Import | Pip Package |
|--------|-------------|
| `PIL` | `Pillow` |
| `cv2` | `opencv-python` |
| `yaml` | `PyYAML` |
| `dotenv` | `python-dotenv` |
| `bs4` | `beautifulsoup4` |
| `google` | `google-auth` |
| `googleapiclient` | `google-api-python-client` |
| `google_auth_oauthlib` | `google-auth-oauthlib` |

All mappings are handled automatically.

### Local Import Filtering

The analyzer filters out local execution script imports:

```python
# This is NOT a pip package (it's a local script)
from create_google_doc import create_doc

# This IS a pip package
from google.oauth2 import service_account
```

Scripts starting with common prefixes are excluded:
- `create_*`, `generate_*`, `send_*`, `scrape_*`, `write_*`, etc.

### Stdlib Detection

Python standard library modules are detected and excluded from the packages list:

```python
import os        # Stdlib - excluded
import json      # Stdlib - excluded
import requests  # External - included
```

The analyzer includes 200+ stdlib modules in its detection list.

---

## Limitations

### What's Detected

✅ **Detected:**
- `import module`
- `from module import something`
- `os.getenv("VAR_NAME")`
- `os.environ.get("VAR_NAME")`
- Conditional imports (try/except blocks)
- Imports inside functions

### What's NOT Detected

❌ **Not Detected:**
- `os.environ["VAR_NAME"]` (dict access without get)
- `importlib.import_module(variable)` (dynamic imports)
- `exec(f"import {variable}")` (string execution)
- Environment variables loaded from config files
- Variables set only in deployment configs
- Transitive dependencies (packages required by your packages)

For production deployment, always review the actual script and test in a clean environment.

---

## Version Mapping

Package versions are read from `/Users/lucasnolan/Agentic OS/requirements.txt`:

```python
# From requirements.txt
anthropic>=0.40.0
requests>=2.32.0
python-dotenv>=1.0.0

# Mapped to packages in manifests
manifest['packages'] = ['anthropic', 'requests', 'python-dotenv']
```

Packages **not** in requirements.txt show as "❓ no version" in query output.

### Missing Versions

These packages are used but not in `requirements.txt`:

```
PyYAML
bcrypt
fastapi
faster_whisper
markdown
rapidfuzz
regex
stripe
torch
whisper
```

**Recommendation:** Add to requirements.txt with version pins.

---

## Integration Examples

### CI/CD Pipeline

```yaml
# .github/workflows/validate-dependencies.yml
name: Validate Dependencies

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'

      - name: Analyze dependencies
        run: python3 execution/analyze_script_dependencies.py

      - name: Check for new packages
        run: |
          python3 -c "
          import json
          with open('execution/script_manifests.json') as f:
              manifests = json.load(f)
          packages = set()
          for m in manifests.values():
              packages.update(m['packages'])
          print(f'Total unique packages: {len(packages)}')
          "
```

### Pre-Deployment Validation

```python
#!/usr/bin/env python3
"""Validate script can run before deploying."""

import json
import os
import sys

script_name = sys.argv[1]

with open('execution/script_manifests.json') as f:
    manifests = json.load(f)

if script_name not in manifests:
    print(f"❌ Script not found: {script_name}")
    sys.exit(1)

manifest = manifests[script_name]

# Check env vars
missing = [var for var in manifest['env_vars'] if not os.getenv(var)]

if missing:
    print(f"❌ Missing environment variables:")
    for var in missing:
        print(f"   - {var}")
    sys.exit(1)

print(f"✅ All {len(manifest['env_vars'])} env vars set")
print(f"✅ Requires {len(manifest['packages'])} packages")
print(f"✅ Ready to deploy!")
```

### Modal Deployment

```python
import modal
import json

# Load manifest
with open('execution/script_manifests.json') as f:
    manifests = json.load(f)

manifest = manifests['calendly_meeting_prep']

# Create Modal image with exact dependencies
app = modal.App("calendly-webhook")
image = modal.Image.debian_slim().pip_install(*manifest['packages'])

# Create secrets from env vars
secrets = [modal.Secret.from_name(var.lower()) for var in manifest['env_vars']]

@app.function(image=image, secrets=secrets)
def handler(event):
    import sys
    sys.path.append('/app')
    from calendly_meeting_prep import main
    return main(event)
```

---

## Updating the Manifests

### When to Re-analyze

Run `analyze_script_dependencies.py` when:

1. **New script added** to execution/
2. **Script modified** - imports or env vars changed
3. **requirements.txt updated** - version pins changed
4. **Regular maintenance** - weekly/monthly

### Re-analysis Process

```bash
# 1. Re-analyze all scripts
python3 execution/analyze_script_dependencies.py

# 2. Review changes
git diff execution/script_manifests.json

# 3. Commit if valid
git add execution/script_manifests.json
git commit -m "Update script dependency manifests"
```

### Automated Re-analysis

Add to git pre-commit hook:

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Check if any execution scripts changed
if git diff --cached --name-only | grep -q "^execution/.*\.py$"; then
    echo "Re-analyzing script dependencies..."
    python3 execution/analyze_script_dependencies.py

    # Stage updated manifest if changed
    if git diff --name-only | grep -q "script_manifests.json"; then
        git add execution/script_manifests.json
        echo "✅ Updated script_manifests.json"
    fi
fi
```

---

## Troubleshooting

### "Script not found" error

```bash
# Make sure you're using the script name without .py
python3 execution/query_script_manifest.py write_cold_emails  # ✅ Correct
python3 execution/query_script_manifest.py write_cold_emails.py  # ✅ Also works
```

### "Manifest file not found"

```bash
# Generate the manifest file first
python3 execution/analyze_script_dependencies.py
```

### Package version shows "❓ no version"

The package is used by scripts but not in `requirements.txt`. Either:

1. Add to requirements.txt with version pin
2. The script is wrong and shouldn't import it

### Script shows wrong dependencies

The analyzer uses static analysis. If a script has dynamic imports or complex logic, manually verify:

```bash
# Read the actual script
cat execution/script_name.py | grep -i "import\|getenv"

# Compare to manifest
python3 execution/query_script_manifest.py script_name
```

---

## Future Enhancements

Potential improvements:

1. **Transitive dependency detection** - Find packages required by packages
2. **Version conflict detection** - Check if scripts require incompatible versions
3. **Dockerfile generation** - Auto-generate optimized Dockerfiles per script
4. **Railway config generation** - Auto-generate Railway service configs
5. **Dependency graph visualization** - See which scripts share dependencies
6. **Cost estimation** - Estimate deployment cost based on dependencies
7. **Security scanning** - Check for vulnerable package versions

---

## Support

For issues or questions:

1. Check this README
2. Read `DEPENDENCY_ANALYSIS_REPORT.md` for detailed analysis
3. Review the analyzer source: `analyze_script_dependencies.py`
4. Check the query tool: `query_script_manifest.py`

---

**Last Updated:** 2026-02-11
**Maintainer:** Agentic OS Team
**License:** Internal use only
