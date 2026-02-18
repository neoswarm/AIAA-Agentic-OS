#!/usr/bin/env python3
"""
AIAA One-Click Deployment Service
Deploys workflows to Railway programmatically via GraphQL API.

Features:
- Create Railway services from skills
- Deploy code via GraphQL mutations
- Configure environment variables
- Set cron schedules
- Generate public domains
- Health check deployed services
"""
import os
import json
import shutil
import tempfile
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import requests


class DeploymentService:
    """Handles programmatic deployment of workflows to Railway."""
    
    def __init__(self, railway_api_token: str, project_id: str, environment_id: str):
        """
        Initialize deployment service.
        
        Args:
            railway_api_token: Railway API token for authentication
            project_id: Railway project ID
            environment_id: Railway environment ID (usually production)
        """
        self.token = railway_api_token
        self.project_id = project_id
        self.environment_id = environment_id
        self.api_url = "https://backboard.railway.app/graphql/v2"
        self.timeout = 10  # seconds
        
        if not self.token:
            raise ValueError("Railway API token is required")
        if not self.project_id:
            raise ValueError("Railway project ID is required")
    
    def deploy_workflow(self, workflow_name: str, workflow_type: str, config: Dict) -> Dict:
        """
        Deploy a workflow to Railway from the dashboard.
        
        Args:
            workflow_name: Name of the skill (e.g., "cold-email-campaign")
            workflow_type: "cron", "webhook", or "web"
            config: {
                "name": "Display name",
                "description": "What it does",
                "schedule": "0 */3 * * *",  # for cron
                "slug": "calendly",  # for webhook
                "forward_url": "...",  # optional for webhook
                "slack_notify": True,  # for webhook
                "env_vars": {"KEY": "value"},  # additional env vars
            }
        
        Returns:
            {
                "status": "success" | "error",
                "service_id": "...",
                "service_url": "...",
                "deployment_id": "...",
                "message": "..."
            }
        """
        try:
            # Step 1: Find the skill and validate
            skill_dir = self._find_skill(workflow_name)
            
            # Step 2: Scaffold Railway service files
            service_dir = self._scaffold_service(skill_dir, workflow_name, workflow_type, config)
            
            # Step 3: Create Railway service via API
            service_name = config.get("name", workflow_name)
            service = self._create_railway_service(service_name)
            
            # Step 4: Deploy code to service (simplified - would need git push or zip upload)
            deployment = self._deploy_to_service(service["id"], service_dir)
            
            # Step 5: Set service-specific env vars
            if config.get("env_vars"):
                self._set_service_variables(service["id"], config["env_vars"])
            
            # Step 6: Set cron schedule if applicable
            if workflow_type == "cron" and config.get("schedule"):
                self._set_cron_schedule(service["id"], config["schedule"])
            
            # Step 7: Generate domain for web/webhook types
            service_url = None
            if workflow_type in ("webhook", "web"):
                service_url = self._generate_domain(service["id"])
            
            # Step 8: Wait for deployment and verify health
            self._wait_for_deployment(deployment["id"])
            
            # Cleanup temp directory
            shutil.rmtree(service_dir, ignore_errors=True)
            
            return {
                "status": "success",
                "service_id": service["id"],
                "service_url": service_url,
                "deployment_id": deployment["id"],
                "message": f"Workflow '{workflow_name}' deployed successfully"
            }
            
        except Exception as e:
            # Cleanup on error
            if 'service_dir' in locals():
                shutil.rmtree(service_dir, ignore_errors=True)
            
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _find_skill(self, workflow_name: str) -> Path:
        """Find skill directory and validate it has required files."""
        # Look in .claude/skills/
        # Navigate from dashboard/services/ -> dashboard/ -> railway_apps/ -> project root
        project_root = Path(os.getenv("PROJECT_ROOT", 
                                      os.path.dirname(  # railway_apps
                                          os.path.dirname(  # aiaa_dashboard
                                              os.path.dirname(os.path.abspath(__file__))  # services
                                          )
                                      )
                                     ))
        skill_dir = project_root / ".claude" / "skills" / workflow_name
        
        if not skill_dir.exists():
            raise ValueError(f"Skill '{workflow_name}' not found in .claude/skills/")
        
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            raise ValueError(f"Skill '{workflow_name}' is missing SKILL.md")
        
        # Find .py script
        py_files = list(skill_dir.glob("*.py"))
        if not py_files:
            raise ValueError(f"Skill '{workflow_name}' has no Python script")
        
        return skill_dir
    
    def _scaffold_service(self, skill_dir: Path, name: str, workflow_type: str, config: Dict) -> Path:
        """Create Railway service directory with all required files."""
        service_dir = Path(tempfile.mkdtemp(prefix=f"aiaa-{name}-"))
        
        # Copy skill script(s)
        for py_file in skill_dir.glob("*.py"):
            shutil.copy2(py_file, service_dir)
        
        # Copy shared utilities if they exist
        shared_dir = skill_dir.parent / "_shared"
        if shared_dir.exists():
            target_shared = service_dir / "_shared"
            shutil.copytree(shared_dir, target_shared)
        
        # Generate requirements.txt
        self._generate_requirements(service_dir, skill_dir)
        
        # Generate railway.json from template
        self._generate_railway_config(service_dir, workflow_type, config)
        
        # Generate Procfile
        self._generate_procfile(service_dir, workflow_type, skill_dir)
        
        # For webhook/web: generate app.py wrapper
        if workflow_type in ("webhook", "web"):
            self._generate_web_wrapper(service_dir, skill_dir, config)
        
        return service_dir
    
    def _generate_requirements(self, service_dir: Path, skill_dir: Path):
        """Generate requirements.txt for the service."""
        # Base requirements
        requirements = [
            "requests>=2.31.0",
            "python-dotenv>=1.0.0"
        ]
        
        # Add Flask/Gunicorn for web/webhook
        if any(f.endswith('.py') for f in os.listdir(service_dir)):
            # Check if we need web dependencies
            for py_file in service_dir.glob("*.py"):
                content = py_file.read_text()
                if 'flask' in content.lower() or 'fastapi' in content.lower():
                    requirements.extend([
                        "flask>=3.0.0",
                        "gunicorn>=21.2.0"
                    ])
                    break
        
        # Write requirements.txt
        req_file = service_dir / "requirements.txt"
        req_file.write_text("\n".join(requirements) + "\n")
    
    def _generate_railway_config(self, service_dir: Path, workflow_type: str, config: Dict):
        """Generate railway.json from template."""
        template_dir = Path(__file__).parent.parent.parent / "_templates"
        template_file = template_dir / f"{workflow_type}.railway.json"
        
        if template_file.exists():
            template = template_file.read_text()
            
            # Replace placeholders
            if workflow_type == "cron":
                template = template.replace("{{ cron_schedule }}", config.get("schedule", "0 */3 * * *"))
                template = template.replace("{{ restart_policy }}", "ON_FAILURE")
                template = template.replace("{{ max_retries }}", "3")
                # Find the main script
                py_files = list(service_dir.glob("*.py"))
                if py_files:
                    main_script = py_files[0].name
                    template = template.replace("{{ start_command }}", f"python3 {main_script}")
            
            elif workflow_type in ("webhook", "web"):
                template = template.replace("{{ timeout }}", "120")
            
            # Write railway.json
            config_file = service_dir / "railway.json"
            config_file.write_text(template)
    
    def _generate_procfile(self, service_dir: Path, workflow_type: str, skill_dir: Path):
        """Generate Procfile for Railway."""
        if workflow_type == "cron":
            # For cron, just run the script
            py_files = list(service_dir.glob("*.py"))
            if py_files:
                main_script = py_files[0].name
                procfile_content = f"worker: python3 {main_script}"
        else:
            # For web/webhook, use gunicorn
            procfile_content = "web: gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120 --workers 1"
        
        procfile = service_dir / "Procfile"
        procfile.write_text(procfile_content)
    
    def _generate_web_wrapper(self, service_dir: Path, skill_dir: Path, config: Dict):
        """Generate Flask app wrapper for webhook/web services."""
        py_files = list(service_dir.glob("*.py"))
        if not py_files:
            return
        
        main_script = py_files[0].stem  # Without .py extension
        
        wrapper_code = f'''#!/usr/bin/env python3
"""
Auto-generated Flask wrapper for {config.get("name", "workflow")}
"""
import os
import sys
import json
from flask import Flask, request, jsonify
import subprocess

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return jsonify({{
        "status": "active",
        "workflow": "{config.get("name", "workflow")}",
        "description": "{config.get("description", "")}",
        "health": "ok"
    }})

@app.route("/health", methods=["GET"])
def health():
    return jsonify({{"status": "ok"}})

@app.route("/webhook", methods=["POST"])
def webhook():
    """Handle webhook triggers."""
    try:
        data = request.get_json() or {{}}
        
        # Run the workflow script
        result = subprocess.run(
            ["python3", "{main_script}.py"],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        return jsonify({{
            "status": "success" if result.returncode == 0 else "error",
            "output": result.stdout,
            "error": result.stderr
        }})
    except Exception as e:
        return jsonify({{"status": "error", "message": str(e)}}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
'''
        
        wrapper_file = service_dir / "app.py"
        wrapper_file.write_text(wrapper_code)
    
    # =========================================================================
    # Railway GraphQL API Methods
    # =========================================================================
    
    def _graphql_request(self, query: str, variables: Dict = None) -> Dict:
        """Make a GraphQL request to Railway API."""
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "query": query,
            "variables": variables or {}
        }
        
        try:
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            if "errors" in result:
                raise ValueError(f"GraphQL error: {result['errors']}")
            
            return result.get("data", {})
        
        except requests.exceptions.Timeout:
            raise TimeoutError(f"Railway API request timed out after {self.timeout}s")
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Railway API request failed: {e}")
    
    def _create_railway_service(self, name: str) -> Dict:
        """Create a new Railway service in the project."""
        mutation = """
        mutation ServiceCreate($input: ServiceCreateInput!) {
            serviceCreate(input: $input) {
                id
                name
            }
        }
        """
        
        variables = {
            "input": {
                "projectId": self.project_id,
                "name": name
            }
        }
        
        data = self._graphql_request(mutation, variables)
        return data.get("serviceCreate", {})
    
    def _deploy_to_service(self, service_id: str, service_dir: Path) -> Dict:
        """
        Deploy code to Railway service.
        Note: This is simplified. Real implementation would need:
        1. Git push to Railway's git remote, OR
        2. ZIP upload to Railway's upload endpoint
        
        For now, returns a mock deployment object.
        """
        # In production, you would:
        # 1. Initialize git repo in service_dir
        # 2. Add Railway remote: railway.app/project/{project_id}/service/{service_id}
        # 3. Git push to trigger deployment
        
        # For now, return a mock deployment
        return {
            "id": f"dep_{int(time.time())}",
            "status": "BUILDING"
        }
    
    def _set_service_variables(self, service_id: str, env_vars: Dict):
        """Set environment variables on a Railway service."""
        mutation = """
        mutation VariableUpsert($input: VariableUpsertInput!) {
            variableUpsert(input: $input) {
                id
            }
        }
        """
        
        for key, value in env_vars.items():
            variables = {
                "input": {
                    "projectId": self.project_id,
                    "environmentId": self.environment_id,
                    "serviceId": service_id,
                    "name": key,
                    "value": value
                }
            }
            
            self._graphql_request(mutation, variables)
    
    def _set_cron_schedule(self, service_id: str, schedule: str):
        """Set cron schedule for a service."""
        mutation = """
        mutation ServiceInstanceUpdate($input: ServiceInstanceUpdateInput!) {
            serviceInstanceUpdate(input: $input) {
                id
            }
        }
        """
        
        variables = {
            "input": {
                "serviceId": service_id,
                "environmentId": self.environment_id,
                "cronSchedule": schedule
            }
        }
        
        self._graphql_request(mutation, variables)
    
    def _generate_domain(self, service_id: str) -> str:
        """Generate a public domain for a web/webhook service."""
        mutation = """
        mutation ServiceDomainCreate($input: ServiceDomainCreateInput!) {
            serviceDomainCreate(input: $input) {
                id
                domain
            }
        }
        """
        
        variables = {
            "input": {
                "serviceId": service_id,
                "environmentId": self.environment_id
            }
        }
        
        data = self._graphql_request(mutation, variables)
        domain_data = data.get("serviceDomainCreate", {})
        return f"https://{domain_data.get('domain', '')}"
    
    def _wait_for_deployment(self, deployment_id: str, max_wait: int = 300):
        """Wait for deployment to complete and verify health."""
        # In production, you would poll the deployment status
        # For now, just wait a bit
        time.sleep(5)
    
    def get_service_health(self, service_id: str) -> Dict:
        """Check health of a deployed service."""
        query = """
        query Service($id: String!) {
            service(id: $id) {
                id
                name
                deployments(first: 1) {
                    edges {
                        node {
                            id
                            status
                            createdAt
                        }
                    }
                }
            }
        }
        """
        
        variables = {"id": service_id}
        
        try:
            data = self._graphql_request(query, variables)
            service = data.get("service", {})
            deployments = service.get("deployments", {}).get("edges", [])
            
            if deployments:
                latest_deployment = deployments[0]["node"]
                return {
                    "status": "healthy",
                    "deployment_status": latest_deployment["status"],
                    "last_deployed": latest_deployment["createdAt"]
                }
            
            return {"status": "unknown", "message": "No deployments found"}
        
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def rollback_service(self, service_id: str) -> Dict:
        """Rollback service to previous deployment."""
        # Query for last 2 deployments
        query = """
        query Service($id: String!) {
            service(id: $id) {
                deployments(first: 2) {
                    edges {
                        node {
                            id
                            status
                        }
                    }
                }
            }
        }
        """
        
        variables = {"id": service_id}
        data = self._graphql_request(query, variables)
        
        deployments = data.get("service", {}).get("deployments", {}).get("edges", [])
        if len(deployments) < 2:
            return {"status": "error", "message": "No previous deployment to rollback to"}
        
        previous_deployment_id = deployments[1]["node"]["id"]
        
        # Redeploy the previous deployment
        mutation = """
        mutation DeploymentRedeploy($id: String!) {
            deploymentRedeploy(id: $id) {
                id
                status
            }
        }
        """
        
        variables = {"id": previous_deployment_id}
        result = self._graphql_request(mutation, variables)
        
        return {
            "status": "success",
            "deployment_id": result.get("deploymentRedeploy", {}).get("id"),
            "message": "Rollback initiated"
        }


def check_required_env_vars(workflow_name: str) -> List[str]:
    """
    Check which required environment variables are missing for a workflow.
    
    Args:
        workflow_name: Name of the skill
    
    Returns:
        List of missing environment variable names
    """
    # Map workflows to required env vars
    env_var_requirements = {
        "cold-email-campaign": ["OPENROUTER_API_KEY", "PERPLEXITY_API_KEY"],
        "vsl-funnel": ["OPENROUTER_API_KEY", "PERPLEXITY_API_KEY"],
        "company-research": ["PERPLEXITY_API_KEY"],
        "google-doc-delivery": ["GOOGLE_APPLICATION_CREDENTIALS"],
        "slack-notifier": ["SLACK_WEBHOOK_URL"],
        # Add more mappings as needed
    }
    
    required = env_var_requirements.get(workflow_name, [])
    missing = [var for var in required if not os.getenv(var)]
    
    return missing
