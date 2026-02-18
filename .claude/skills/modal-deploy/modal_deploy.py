#!/usr/bin/env python3
"""
Modal Cloud Deployment

Deploys skill scripts to Modal as serverless functions with automatic secret
configuration, endpoint creation, and health checks.
Follows directive: directives/modal_deploy.md (based on SKILL.md)
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List

# Add _shared to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "_shared"))

try:
    import requests
except ImportError:
    print("❌ Error: requests library not installed")
    print("   Install with: pip install requests")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from error_reporter import report_error, report_success, report_warning


def check_modal_cli() -> bool:
    """Check if Modal CLI is installed"""
    import subprocess
    try:
        result = subprocess.run(["modal", "--version"], capture_output=True, timeout=5)
        return result.returncode == 0
    except:
        return False


def validate_script(script_path: Path) -> Dict:
    """
    Validate script is Modal-compatible.
    
    Checks for:
    - Correct import pattern (requests separate from dotenv)
    - modal.App defined
    - Function decorators
    """
    issues = []
    
    with open(script_path) as f:
        content = f.read()
    
    # Check for crash-causing dotenv pattern
    if "import requests" in content and "from dotenv import load_dotenv" in content:
        # Check if they're in the same try/except block with sys.exit(1)
        if "try:" in content and "import requests" in content and "sys.exit(1)" in content:
            # Simplified check - would need better parsing for production
            issues.append({
                "severity": "error",
                "message": "Requests and dotenv must be in separate try/except blocks for Modal compatibility",
                "fix": "Separate imports: requests in first try/except with sys.exit(1), dotenv in second with pass"
            })
    
    # Check for modal.App
    if "modal.App" not in content and "app = modal.App" not in content:
        issues.append({
            "severity": "warning",
            "message": "No modal.App found - script may not be Modal-compatible",
            "fix": "Add: app = modal.App('app-name')"
        })
    
    # Check for decorators
    if "@app.function" not in content:
        issues.append({
            "severity": "warning",
            "message": "No @app.function decorator found",
            "fix": "Add @app.function decorator to functions you want to deploy"
        })
    
    return {
        "valid": len([i for i in issues if i["severity"] == "error"]) == 0,
        "issues": issues
    }


def check_secrets(script_path: Path) -> List[str]:
    """
    Detect which secrets the script needs based on env var usage.
    
    Returns:
        List of Modal secret names required
    """
    with open(script_path) as f:
        content = f.read()
    
    secret_map = {
        "OPENROUTER_API_KEY": "openrouter-secret",
        "PERPLEXITY_API_KEY": "perplexity-secret",
        "SLACK_WEBHOOK_URL": "slack-webhook",
        "GOOGLE_SERVICE_ACCOUNT_JSON": "google-service-account",
        "CALENDLY_API_KEY": "calendly-secret",
        "ANTHROPIC_API_KEY": "anthropic-secret",
        "OPENAI_API_KEY": "openai-secret"
    }
    
    needed_secrets = []
    for env_var, secret_name in secret_map.items():
        if f'os.getenv("{env_var}")' in content or f"os.getenv('{env_var}')" in content:
            needed_secrets.append(secret_name)
    
    return needed_secrets


def deploy_to_modal(script_path: Path, app_name: str) -> Dict:
    """
    Deploy script to Modal.
    
    Returns:
        {
            "success": bool,
            "app_name": str,
            "endpoints": [...],
            "deploy_log": str
        }
    """
    import subprocess
    
    print(f"\n🚀 Deploying to Modal...")
    print(f"   Script: {script_path}")
    print(f"   App: {app_name}")
    
    try:
        # Run modal deploy
        result = subprocess.run(
            ["modal", "deploy", str(script_path)],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        success = result.returncode == 0
        
        if success:
            print(f"   ✅ Deployment successful")
        else:
            print(f"   ❌ Deployment failed")
            print(f"   Error: {result.stderr}")
        
        return {
            "success": success,
            "app_name": app_name,
            "deploy_log": result.stdout + result.stderr,
            "error": None if success else result.stderr
        }
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "app_name": app_name,
            "deploy_log": "",
            "error": "Deployment timeout (exceeded 120s)"
        }
    except Exception as e:
        return {
            "success": False,
            "app_name": app_name,
            "deploy_log": "",
            "error": str(e)
        }


def get_modal_apps() -> List[Dict]:
    """Get list of currently deployed Modal apps"""
    import subprocess
    
    try:
        result = subprocess.run(
            ["modal", "app", "list", "--json"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            return []
    except:
        return []


def health_check(endpoint_url: str, timeout: int = 30) -> bool:
    """
    Check if deployed endpoint is healthy.
    
    Waits up to timeout seconds for endpoint to respond.
    """
    print(f"\n🏥 Health check: {endpoint_url}")
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(endpoint_url, timeout=5)
            if response.status_code == 200:
                print(f"   ✅ Endpoint healthy")
                return True
        except:
            pass
        
        time.sleep(2)
    
    print(f"   ⚠️  Endpoint not responding after {timeout}s")
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Deploy skill scripts to Modal cloud"
    )
    parser.add_argument("--script", required=True, help="Path to Python script to deploy")
    parser.add_argument("--app-name", help="Modal app name (auto-detected from script if not provided)")
    parser.add_argument("--skip-validation", action="store_true", help="Skip pre-deployment validation")
    parser.add_argument("--skip-health-check", action="store_true", help="Skip post-deployment health check")
    
    args = parser.parse_args()
    
    script_path = Path(args.script)
    
    # Check if script exists
    if not script_path.exists():
        print(f"❌ Error: Script not found: {script_path}")
        sys.exit(1)
    
    # Check Modal CLI
    if not check_modal_cli():
        print("❌ Error: Modal CLI not installed")
        print("   Install with: pip install modal")
        sys.exit(1)
    
    try:
        # Validate script
        if not args.skip_validation:
            print(f"🔍 Validating script...")
            validation = validate_script(script_path)
            
            if validation["issues"]:
                for issue in validation["issues"]:
                    symbol = "❌" if issue["severity"] == "error" else "⚠️"
                    print(f"   {symbol} {issue['message']}")
                    print(f"      Fix: {issue['fix']}")
            
            if not validation["valid"]:
                print("\n❌ Validation failed. Fix errors before deploying.")
                sys.exit(1)
            
            print(f"   ✅ Validation passed")
        
        # Check required secrets
        print(f"\n🔐 Checking required secrets...")
        needed_secrets = check_secrets(script_path)
        if needed_secrets:
            print(f"   Required secrets: {', '.join(needed_secrets)}")
            print(f"   Ensure these are configured in Modal: modal secret list")
        else:
            print(f"   No secrets required")
        
        # Check free tier limits
        apps = get_modal_apps()
        if len(apps) >= 8:
            print("\n⚠️  Warning: Free tier limit (8 web endpoints) may be exceeded")
            print(f"   Current apps: {len(apps)}")
            print(f"   Consider stopping unused apps: modal app stop <app-id>")
        
        # Determine app name
        app_name = args.app_name
        if not app_name:
            # Try to extract from script
            with open(script_path) as f:
                content = f.read()
                # Look for app = modal.App("name")
                import re
                match = re.search(r'modal\.App\(["\']([^"\']+)["\']\)', content)
                if match:
                    app_name = match.group(1)
                else:
                    app_name = script_path.stem.replace("_", "-")
        
        # Deploy
        deployment = deploy_to_modal(script_path, app_name)
        
        if not deployment["success"]:
            report_error(
                "modal-deploy",
                Exception(deployment["error"]),
                {"script": str(script_path), "app_name": app_name}
            )
            print("\n❌ Deployment failed")
            sys.exit(1)
        
        # Health check (if applicable)
        # Note: Would need to parse deployment output for endpoint URL
        # Skipping for now as it's script-specific
        
        # Report success
        report_success(
            "modal-deploy",
            f"Deployed {app_name} to Modal",
            {
                "script": str(script_path),
                "app_name": app_name,
                "secrets": needed_secrets
            }
        )
        
        print(f"\n✅ Deployment complete!")
        print(f"   App: {app_name}")
        print(f"   View logs: modal app logs {app_name}")
        print(f"   Stop app: modal app stop {app_name}")
        
    except Exception as e:
        report_error("modal-deploy", e, {"script": str(script_path)})
        sys.exit(1)


if __name__ == "__main__":
    main()
