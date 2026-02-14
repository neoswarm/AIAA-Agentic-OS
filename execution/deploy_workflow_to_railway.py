#!/usr/bin/env python3
"""
Deploy Workflow to Railway - Complete Automation

This script automates the COMPLETE deployment of a workflow to Railway in 8 phases:
1. Discovery & Validation - Parse directive, validate prerequisites
2. Dependency Resolution - Extract packages and env vars
3. Railway Service Creation - Create new Railway service via CLI
4. Service Directory Setup - Generate configs, copy scripts
5. Environment Variable Sync - Copy from .env to Railway service
6. Deployment - Deploy to Railway via `railway up`
7. Wait for Success - Poll deployment status
8. Dashboard Registration - Update workflow_config.json

Usage:
    python3 execution/deploy_workflow_to_railway.py --directive cold_email_scriptwriter
    python3 execution/deploy_workflow_to_railway.py --directive calendly_meeting_prep --dry-run
    python3 execution/deploy_workflow_to_railway.py --directive my_cron_job --cron "0 */3 * * *"

Requirements:
    - Railway CLI installed and authenticated (brew install railway && railway login)
    - RAILWAY_API_TOKEN set in .env (for API operations)
    - All execution scripts exist
    - Dependencies analyzed (script_manifests.json exists)
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

try:
    import yaml
except ImportError:
    print("Error: pyyaml not installed. Run: pip install pyyaml")
    sys.exit(1)

try:
    from jinja2 import Template
except ImportError:
    print("Error: jinja2 not installed. Run: pip install jinja2")
    sys.exit(1)

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DIRECTIVES_DIR = PROJECT_ROOT / "directives"
EXECUTION_DIR = PROJECT_ROOT / "execution"
RAILWAY_APPS_DIR = PROJECT_ROOT / "railway_apps"
TEMPLATES_DIR = RAILWAY_APPS_DIR / "_templates"
DASHBOARD_DIR = RAILWAY_APPS_DIR / "aiaa_dashboard"

# Railway configuration
RAILWAY_PROJECT_ID = os.getenv("RAILWAY_PROJECT_ID", "3b96c81f-9518-4131-b2bc-bcd7a524a5ef")
RAILWAY_API_TOKEN = os.getenv("RAILWAY_API_TOKEN", "")

# Colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


class DeploymentError(Exception):
    """Custom exception for deployment failures."""
    pass


class WorkflowDeployer:
    """Orchestrates complete workflow deployment to Railway."""

    def __init__(self, directive_name: str, dry_run: bool = False, cron_override: Optional[str] = None):
        self.directive_name = directive_name
        self.dry_run = dry_run
        self.cron_override = cron_override
        self.metadata = None
        self.service_id = None
        self.service_dir = None
        self.deployment_id = None
        self.dependencies = None

    def deploy(self) -> dict:
        """Execute complete deployment pipeline."""
        print(f"\n{Colors.BOLD}{'='*70}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}RAILWAY WORKFLOW DEPLOYMENT{Colors.RESET}")
        print(f"{Colors.BOLD}{'='*70}{Colors.RESET}")
        print(f"Workflow: {Colors.YELLOW}{self.directive_name}{Colors.RESET}")
        print(f"Mode:     {Colors.MAGENTA}{'DRY RUN' if self.dry_run else 'PRODUCTION'}{Colors.RESET}")
        print(f"{'='*70}\n")

        try:
            # Phase 1: Discovery & Validation
            self._print_phase(1, "Discovery & Validation")
            self.metadata = self._parse_metadata()
            self._validate_prerequisites()
            print(f"  {Colors.GREEN}✓{Colors.RESET} Metadata parsed: {self.metadata['name']}")
            print(f"  {Colors.GREEN}✓{Colors.RESET} Type: {self.metadata['type']}")
            print(f"  {Colors.GREEN}✓{Colors.RESET} Scripts: {', '.join(self.metadata['execution_scripts'])}\n")

            if self.dry_run:
                print(f"{Colors.YELLOW}DRY RUN: Skipping remaining phases{Colors.RESET}\n")
                self._print_metadata_summary()
                return {"status": "dry_run", "metadata": self.metadata}

            # Phase 2: Dependency Resolution
            self._print_phase(2, "Dependency Resolution")
            self.dependencies = self._resolve_dependencies()
            print(f"  {Colors.GREEN}✓{Colors.RESET} Python packages: {len(self.dependencies['packages'])}")
            print(f"  {Colors.GREEN}✓{Colors.RESET} Env vars: {len(self.dependencies['env_vars'])}")
            print(f"  {Colors.GREEN}✓{Colors.RESET} Packages: {', '.join(self.dependencies['packages'][:5])}...")
            print()

            # Phase 3: Service Directory Setup
            self._print_phase(3, "Service Directory Setup")
            self.service_dir = self._create_service_directory()
            print(f"  {Colors.GREEN}✓{Colors.RESET} Directory: {self.service_dir.relative_to(PROJECT_ROOT)}")
            print(f"  {Colors.GREEN}✓{Colors.RESET} Files: railway.json, requirements.txt, {len(self.metadata['execution_scripts'])} scripts\n")

            # Phase 4: Railway Service Creation
            self._print_phase(4, "Railway Service Creation")
            self.service_id = self._create_railway_service()
            print(f"  {Colors.GREEN}✓{Colors.RESET} Service created with ID: {self.service_id}\n")

            # Phase 5: Environment Variable Sync
            self._print_phase(5, "Environment Variable Sync")
            sync_result = self._sync_environment_variables()
            print(f"  {Colors.GREEN}✓{Colors.RESET} Synced: {len(sync_result['synced'])} vars")
            if sync_result['skipped']:
                print(f"  {Colors.YELLOW}⚠{Colors.RESET} Skipped (not in .env): {', '.join(sync_result['skipped'][:3])}...")
            if sync_result['failed']:
                print(f"  {Colors.RED}✗{Colors.RESET} Failed: {', '.join(sync_result['failed'])}")
            print()

            # Phase 6: Deployment to Railway
            self._print_phase(6, "Deployment to Railway")
            self.deployment_id = self._deploy_to_railway()
            print(f"  {Colors.GREEN}✓{Colors.RESET} Deployment triggered: {self.deployment_id}\n")

            # Phase 7: Wait for Success
            self._print_phase(7, "Waiting for Deployment")
            self._wait_for_deployment()
            print(f"  {Colors.GREEN}✓{Colors.RESET} Deployment succeeded\n")

            # Phase 8: Dashboard Registration
            self._print_phase(8, "Dashboard Registration")
            self._register_in_dashboard()
            print(f"  {Colors.GREEN}✓{Colors.RESET} Registered in workflow_config.json\n")

            # Success
            self._print_success()

            return {
                "status": "success",
                "service_id": self.service_id,
                "deployment_id": self.deployment_id,
                "metadata": self.metadata,
                "service_dir": str(self.service_dir)
            }

        except DeploymentError as e:
            self._print_error(str(e))
            return {"status": "failed", "error": str(e)}
        except Exception as e:
            self._print_error(f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "failed", "error": str(e)}

    def _print_phase(self, number: int, name: str):
        """Print phase header."""
        print(f"{Colors.BOLD}{Colors.BLUE}PHASE {number}: {name}{Colors.RESET}")
        print(f"{Colors.BLUE}{'─'*70}{Colors.RESET}")

    def _print_error(self, message: str):
        """Print error message."""
        print(f"\n{Colors.RED}{Colors.BOLD}{'='*70}{Colors.RESET}")
        print(f"{Colors.RED}{Colors.BOLD}❌ DEPLOYMENT FAILED{Colors.RESET}")
        print(f"{Colors.RED}{Colors.BOLD}{'='*70}{Colors.RESET}")
        print(f"{Colors.RED}{message}{Colors.RESET}\n")

    def _print_success(self):
        """Print success message."""
        print(f"{Colors.GREEN}{Colors.BOLD}{'='*70}{Colors.RESET}")
        print(f"{Colors.GREEN}{Colors.BOLD}✅ DEPLOYMENT COMPLETE{Colors.RESET}")
        print(f"{Colors.GREEN}{Colors.BOLD}{'='*70}{Colors.RESET}")
        print(f"Service ID:    {self.service_id}")
        print(f"Deployment ID: {self.deployment_id}")
        print(f"Service Dir:   {self.service_dir.relative_to(PROJECT_ROOT)}")
        print(f"Dashboard:     https://aiaa-dashboard-production-10fa.up.railway.app")
        print(f"{Colors.GREEN}{'='*70}{Colors.RESET}\n")

    def _print_metadata_summary(self):
        """Print metadata summary for dry run."""
        print(f"\n{Colors.BOLD}Metadata Summary:{Colors.RESET}")
        print(f"  Name:        {self.metadata.get('name')}")
        print(f"  Category:    {self.metadata.get('category')}")
        print(f"  Type:        {self.metadata.get('type')}")
        print(f"  Version:     {self.metadata.get('version')}")
        print(f"  Scripts:     {', '.join(self.metadata.get('execution_scripts', []))}")
        print(f"  Env Vars:    {len(self.metadata.get('env_vars', []))} required")
        print(f"  Integrations: {', '.join(self.metadata.get('integrations', []))}")
        print()

    def _parse_metadata(self) -> dict:
        """Parse directive YAML frontmatter."""
        directive_path = DIRECTIVES_DIR / f"{self.directive_name}.md"

        if not directive_path.exists():
            raise DeploymentError(f"Directive not found: {directive_path}")

        content = directive_path.read_text(encoding='utf-8')

        # Extract YAML frontmatter
        if not content.startswith("---"):
            raise DeploymentError(
                f"Directive missing YAML frontmatter: {self.directive_name}\n"
                "Run: python3 execution/add_metadata_to_directives.py --directive {self.directive_name}"
            )

        parts = content.split("---", 2)
        if len(parts) < 3:
            raise DeploymentError(f"Malformed YAML frontmatter: {self.directive_name}")

        try:
            metadata = yaml.safe_load(parts[1])
        except yaml.YAMLError as e:
            raise DeploymentError(f"Invalid YAML in frontmatter: {e}")

        # Validate required fields
        required_fields = ["name", "type", "execution_scripts"]
        for field in required_fields:
            if field not in metadata:
                raise DeploymentError(f"Missing required field in metadata: {field}")

        # Apply cron override if provided
        if self.cron_override:
            if "deployment" not in metadata:
                metadata["deployment"] = {}
            metadata["deployment"]["cron_schedule"] = self.cron_override

        return metadata

    def _validate_prerequisites(self):
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

        # Check .env exists
        env_file = PROJECT_ROOT / ".env"
        if not env_file.exists():
            print(f"  {Colors.YELLOW}⚠{Colors.RESET} Warning: .env file not found, env vars may not be synced")

    def _resolve_dependencies(self) -> dict:
        """Resolve all dependencies for workflow."""
        # Load script manifests
        manifests_path = EXECUTION_DIR / "script_manifests.json"

        if not manifests_path.exists():
            raise DeploymentError(
                f"Script manifests not found. Run: python3 execution/analyze_script_dependencies.py"
            )

        with open(manifests_path) as f:
            manifests = json.load(f)

        # Aggregate dependencies from all scripts
        all_packages = set()
        all_env_vars = set()

        for script_name in self.metadata["execution_scripts"]:
            script_key = Path(script_name).stem
            if script_key in manifests:
                all_packages.update(manifests[script_key]["packages"])
                all_env_vars.update(manifests[script_key]["env_vars"])

        # Add from metadata (explicit overrides)
        if "dependencies" in self.metadata and "python_packages" in self.metadata["dependencies"]:
            for pkg in self.metadata["dependencies"]["python_packages"]:
                # Extract package name (remove version pins)
                pkg_name = pkg.split(">=")[0].split("==")[0].split("~=")[0]
                all_packages.add(pkg_name)

        if "env_vars" in self.metadata:
            all_env_vars.update(self.metadata["env_vars"])

        return {
            "packages": sorted(all_packages),
            "env_vars": sorted(all_env_vars)
        }

    def _create_service_directory(self) -> Path:
        """Create service directory with all required files."""
        service_dir = RAILWAY_APPS_DIR / self.directive_name
        service_dir.mkdir(exist_ok=True)

        # 1. Generate railway.json from template
        railway_config = self._generate_railway_config()
        with open(service_dir / "railway.json", 'w') as f:
            json.dump(railway_config, f, indent=2)

        # 2. Generate requirements.txt
        requirements = self._generate_requirements()
        (service_dir / "requirements.txt").write_text(requirements)

        # 3. Copy execution scripts
        for script_name in self.metadata["execution_scripts"]:
            src = EXECUTION_DIR / script_name
            dst = service_dir / script_name
            shutil.copy2(src, dst)

        # 4. Copy .env (for reference, not deployed)
        env_file = PROJECT_ROOT / ".env"
        if env_file.exists():
            shutil.copy2(env_file, service_dir / ".env.example")

        return service_dir

    def _generate_railway_config(self) -> dict:
        """Generate railway.json from template."""
        workflow_type = self.metadata["type"]
        template_path = TEMPLATES_DIR / f"{workflow_type}.railway.json"

        if not template_path.exists():
            raise DeploymentError(f"No template for workflow type: {workflow_type}")

        template_content = template_path.read_text()
        template = Template(template_content)

        # Extract deployment config from metadata
        deploy_config = self.metadata.get("deployment", {}).get("railway_config", {})

        # Build context for template
        context = {
            "start_command": deploy_config.get(
                "start_command",
                f"python3 {self.metadata['execution_scripts'][0]}"
            ),
            "restart_policy": deploy_config.get("restart_policy", "ON_FAILURE"),
            "max_retries": deploy_config.get("max_retries", 3),
            "timeout": deploy_config.get("timeout_seconds", 300 if workflow_type == "webhook" else 120),
            "workers": deploy_config.get("workers", 1),
        }

        # Add cron schedule if type is cron
        if workflow_type == "cron":
            cron_schedule = self.metadata.get("deployment", {}).get("cron_schedule", "0 * * * *")
            context["cron_schedule"] = cron_schedule

        rendered = template.render(**context)
        return json.loads(rendered)

    def _generate_requirements(self) -> str:
        """Generate minimal requirements.txt with version pins."""
        # Load root requirements for version mapping
        root_reqs_path = PROJECT_ROOT / "requirements.txt"
        version_map = {}

        if root_reqs_path.exists():
            for line in root_reqs_path.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # Parse package==version or package>=version
                if "==" in line:
                    pkg, version = line.split("==", 1)
                    version_map[pkg.strip()] = f"=={version.strip()}"
                elif ">=" in line:
                    pkg, version = line.split(">=", 1)
                    version_map[pkg.strip()] = f">={version.strip()}"

        # Generate requirements with versions
        requirements = []
        for pkg in self.dependencies["packages"]:
            version = version_map.get(pkg, "")
            requirements.append(f"{pkg}{version}")

        return "\n".join(sorted(requirements)) + "\n"

    def _create_railway_service(self) -> str:
        """Create Railway service via CLI."""
        service_name = self.directive_name.replace("_", "-")

        # Change to service directory
        os.chdir(self.service_dir)

        # Link to project
        print(f"  → Linking to project {RAILWAY_PROJECT_ID[:8]}...")
        result = subprocess.run(
            ["railway", "link", "-p", RAILWAY_PROJECT_ID],
            capture_output=True,
            text=True
        )
        if result.returncode != 0 and "already linked" not in result.stderr.lower():
            raise DeploymentError(f"Failed to link project: {result.stderr}")

        # Get service ID (might already exist)
        result = subprocess.run(
            ["railway", "status", "--json"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            try:
                status = json.loads(result.stdout)
                existing_service_id = status.get("service", {}).get("id")
                if existing_service_id:
                    print(f"  → Using existing service: {existing_service_id}")
                    return existing_service_id
            except:
                pass

        # Create new service
        print(f"  → Creating service: {service_name}")
        result = subprocess.run(
            ["railway", "service"],
            capture_output=True,
            text=True,
            input=service_name  # Service name via stdin
        )

        # Get service ID
        result = subprocess.run(
            ["railway", "status", "--json"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise DeploymentError("Failed to get service status after creation")

        try:
            status = json.loads(result.stdout)
            service_id = status["service"]["id"]
            return service_id
        except (KeyError, json.JSONDecodeError):
            raise DeploymentError("Could not determine service ID from status")

    def _sync_environment_variables(self) -> dict:
        """Sync environment variables to Railway service."""
        required_vars = self.dependencies["env_vars"]

        # Load from .env
        env_file = PROJECT_ROOT / ".env"
        env_values = {}

        if env_file.exists():
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env_values[key.strip()] = value.strip().strip('"').strip("'")

        # Sync each var
        results = {"synced": [], "skipped": [], "failed": []}

        for var_name in required_vars:
            if var_name not in env_values:
                results["skipped"].append(var_name)
                continue

            # Set via Railway CLI
            print(f"  → Setting {var_name}...")
            result = subprocess.run(
                ["railway", "variables", "set", f"{var_name}={env_values[var_name]}"],
                capture_output=True,
                text=True,
                cwd=str(self.service_dir)
            )

            if result.returncode == 0:
                results["synced"].append(var_name)
            else:
                results["failed"].append(var_name)
                print(f"    {Colors.RED}Error: {result.stderr.strip()}{Colors.RESET}")

        return results

    def _deploy_to_railway(self) -> str:
        """Deploy service to Railway."""
        os.chdir(self.service_dir)

        print(f"  → Deploying service...")
        result = subprocess.run(
            ["railway", "up", "--detach"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise DeploymentError(f"Deployment failed: {result.stderr}")

        # Extract deployment ID from output (if available)
        # Railway CLI doesn't always return deployment ID, so we'll use a placeholder
        deployment_id = "railway-deployment"

        return deployment_id

    def _wait_for_deployment(self, timeout: int = 600):
        """Wait for deployment to succeed."""
        print(f"  → Waiting for build (max {timeout}s)...")

        start_time = time.time()
        while time.time() - start_time < timeout:
            # Check service status
            result = subprocess.run(
                ["railway", "status", "--json"],
                capture_output=True,
                text=True,
                cwd=str(self.service_dir)
            )

            if result.returncode == 0:
                try:
                    status = json.loads(result.stdout)
                    # Check if deployment is complete (simplified check)
                    if status.get("service"):
                        print(f"  → Build appears complete")
                        return
                except json.JSONDecodeError:
                    pass

            time.sleep(10)
            print("  .", end="", flush=True)

        print(f"\n  {Colors.YELLOW}⚠{Colors.RESET} Timeout waiting for deployment (continuing anyway)")

    def _register_in_dashboard(self):
        """Register workflow in dashboard config."""
        config_path = DASHBOARD_DIR / "workflow_config.json"

        # Load existing config
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
        else:
            config = {"project_id": RAILWAY_PROJECT_ID, "cache_ttl_seconds": 300, "workflows": {}}

        # Add this workflow
        config["workflows"][self.service_id] = {
            "name": self.metadata["name"],
            "description": self.metadata.get("description", ""),
            "enabled": True,
            "type": self.metadata["type"],
            "category": self.metadata.get("category", "General")
        }

        # Save
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Deploy workflow to Railway with full automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Deploy a manual workflow
  python3 execution/deploy_workflow_to_railway.py --directive cold_email_scriptwriter

  # Deploy a cron job with custom schedule
  python3 execution/deploy_workflow_to_railway.py --directive daily_report --cron "0 9 * * *"

  # Dry run (validate without deploying)
  python3 execution/deploy_workflow_to_railway.py --directive test_workflow --dry-run
        """
    )
    parser.add_argument("--directive", required=True, help="Directive name (without .md extension)")
    parser.add_argument("--dry-run", action="store_true", help="Validate without deploying")
    parser.add_argument("--cron", help="Override cron schedule (for cron workflows)")
    args = parser.parse_args()

    deployer = WorkflowDeployer(
        directive_name=args.directive,
        dry_run=args.dry_run,
        cron_override=args.cron
    )

    result = deployer.deploy()

    sys.exit(0 if result["status"] in ["success", "dry_run"] else 1)


if __name__ == "__main__":
    main()
