#!/usr/bin/env python3
"""
AIAA Dashboard API Routes
REST API endpoints for workflow deployment and management.
"""
import os
import json
from datetime import datetime
from functools import wraps
from pathlib import Path
from flask import Blueprint, request, jsonify, session
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from services.deployment_service import DeploymentService, check_required_env_vars


api_bp = Blueprint('api', __name__, url_prefix='/api')


# =============================================================================
# Authentication Decorators
# =============================================================================

def require_auth(permission='read'):
    """
    Require authentication for API endpoints.
    Supports both session auth and API key auth.
    
    Args:
        permission: 'read', 'write', or 'deploy'
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check session auth
            if session.get('authenticated'):
                return f(*args, **kwargs)
            
            # Check API key auth
            api_key = request.headers.get('X-API-Key')
            if api_key and api_key == os.getenv('DASHBOARD_API_KEY'):
                return f(*args, **kwargs)
            
            return jsonify({
                "status": "error",
                "message": "Authentication required"
            }), 401
        
        return decorated_function
    return decorator


def log_event(event_type: str, status: str, details: dict):
    """Log an event to the events log."""
    # This would integrate with the main app's event logging
    # For now, just a placeholder
    pass


def log_deployment(workflow_name: str, result: dict):
    """Log a deployment to the deployment history."""
    # This would integrate with the main app's deployment tracking
    # For now, just a placeholder
    pass


# =============================================================================
# Deployment Endpoints
# =============================================================================

@api_bp.route('/workflows/deploy', methods=['POST'])
@require_auth('deploy')
def api_deploy_workflow():
    """
    One-click deploy endpoint.
    
    Request body:
    {
        "workflow_name": "cold-email-campaign",
        "workflow_type": "cron",  # or "webhook", "web"
        "config": {
            "name": "Cold Email Automation",
            "description": "Daily cold email campaign execution",
            "schedule": "0 9 * * *",  # for cron
            "slug": "cold-email",  # for webhook
            "env_vars": {"CUSTOM_VAR": "value"}
        }
    }
    
    Response:
    {
        "status": "success",
        "service_id": "...",
        "service_url": "...",
        "deployment_id": "...",
        "message": "..."
    }
    """
    data = request.get_json()
    
    # Validate input
    workflow_name = data.get('workflow_name')
    if not workflow_name:
        return jsonify({
            "status": "error",
            "message": "workflow_name is required"
        }), 400
    
    workflow_type = data.get('workflow_type', 'cron')
    if workflow_type not in ('cron', 'webhook', 'web'):
        return jsonify({
            "status": "error",
            "message": "workflow_type must be 'cron', 'webhook', or 'web'"
        }), 400
    
    config = data.get('config', {})
    
    # Check required env vars
    missing = check_required_env_vars(workflow_name)
    if missing:
        return jsonify({
            "status": "error",
            "message": f"Missing required environment variables: {', '.join(missing)}",
            "missing_vars": missing
        }), 400
    
    # Check Railway credentials
    railway_token = os.getenv('RAILWAY_API_TOKEN')
    project_id = os.getenv('RAILWAY_PROJECT_ID')
    env_id = os.getenv('RAILWAY_ENV_ID', 'production')
    
    if not railway_token or not project_id:
        return jsonify({
            "status": "error",
            "message": "Railway credentials not configured. Set RAILWAY_API_TOKEN and RAILWAY_PROJECT_ID."
        }), 500
    
    # Deploy
    try:
        service = DeploymentService(
            railway_api_token=railway_token,
            project_id=project_id,
            environment_id=env_id
        )
        result = service.deploy_workflow(workflow_name, workflow_type, config)
        
        # Log to database
        if result['status'] == 'success':
            log_deployment(workflow_name, result)
            log_event('deploy', 'success', {'workflow': workflow_name})
        else:
            log_event('deploy', 'error', {
                'workflow': workflow_name,
                'error': result.get('message')
            })
        
        status_code = 200 if result['status'] == 'success' else 500
        return jsonify(result), status_code
    
    except Exception as e:
        log_event('deploy', 'error', {'workflow': workflow_name, 'error': str(e)})
        return jsonify({
            "status": "error",
            "message": f"Deployment failed: {str(e)}"
        }), 500


@api_bp.route('/workflows/deployable', methods=['GET'])
@require_auth('read')
def api_list_deployable_workflows():
    """
    List all skills that can be deployed.
    
    Response:
    {
        "total": 133,
        "workflows": [
            {
                "name": "cold-email-campaign",
                "display_name": "Cold Email Campaign",
                "description": "...",
                "has_script": true,
                "required_env_vars": ["OPENROUTER_API_KEY", "PERPLEXITY_API_KEY"],
                "missing_env_vars": [],
                "deployable": true
            },
            ...
        ]
    }
    """
    try:
        # Find all skills
        project_root = Path(os.getenv("PROJECT_ROOT", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        skills_dir = project_root / ".claude" / "skills"
        
        workflows = []
        
        for skill_dir in sorted(skills_dir.iterdir()):
            if not skill_dir.is_dir() or skill_dir.name.startswith('_'):
                continue
            
            skill_md = skill_dir / "SKILL.md"
            py_files = list(skill_dir.glob("*.py"))
            
            if not skill_md.exists() or not py_files:
                continue
            
            # Parse SKILL.md frontmatter
            try:
                content = skill_md.read_text()
                lines = content.split('\n')
                
                # Extract frontmatter
                name = skill_dir.name
                description = ""
                
                if lines[0] == '---':
                    for line in lines[1:]:
                        if line == '---':
                            break
                        if line.startswith('name:'):
                            name = line.split(':', 1)[1].strip()
                        elif line.startswith('description:'):
                            description = line.split(':', 1)[1].strip()
                
                # Check required env vars
                required_vars = check_required_env_vars(skill_dir.name)
                missing_vars = [var for var in required_vars if not os.getenv(var)]
                
                workflows.append({
                    "name": skill_dir.name,
                    "display_name": name,
                    "description": description,
                    "has_script": len(py_files) > 0,
                    "script_count": len(py_files),
                    "required_env_vars": required_vars,
                    "missing_env_vars": missing_vars,
                    "deployable": len(missing_vars) == 0
                })
            
            except Exception as e:
                continue
        
        return jsonify({
            "total": len(workflows),
            "workflows": workflows
        })
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@api_bp.route('/workflows/<workflow_name>/requirements', methods=['GET'])
@require_auth('read')
def api_workflow_requirements(workflow_name):
    """
    Get required environment variables for a specific workflow.
    
    Response:
    {
        "workflow": "cold-email-campaign",
        "required_env_vars": ["OPENROUTER_API_KEY", "PERPLEXITY_API_KEY"],
        "missing_env_vars": ["PERPLEXITY_API_KEY"],
        "configured": false
    }
    """
    try:
        required_vars = check_required_env_vars(workflow_name)
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        return jsonify({
            "workflow": workflow_name,
            "required_env_vars": required_vars,
            "missing_env_vars": missing_vars,
            "configured": len(missing_vars) == 0
        })
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@api_bp.route('/workflows/<workflow_name>/rollback', methods=['POST'])
@require_auth('deploy')
def api_rollback_workflow(workflow_name):
    """
    Rollback a workflow to its previous deployment.
    
    Request body:
    {
        "service_id": "abc123"  # Railway service ID
    }
    
    Response:
    {
        "status": "success",
        "deployment_id": "...",
        "message": "Rollback initiated"
    }
    """
    data = request.get_json()
    service_id = data.get('service_id')
    
    if not service_id:
        return jsonify({
            "status": "error",
            "message": "service_id is required"
        }), 400
    
    try:
        railway_token = os.getenv('RAILWAY_API_TOKEN')
        project_id = os.getenv('RAILWAY_PROJECT_ID')
        env_id = os.getenv('RAILWAY_ENV_ID', 'production')
        
        service = DeploymentService(
            railway_api_token=railway_token,
            project_id=project_id,
            environment_id=env_id
        )
        
        result = service.rollback_service(service_id)
        
        if result['status'] == 'success':
            log_event('rollback', 'success', {'workflow': workflow_name, 'service_id': service_id})
        else:
            log_event('rollback', 'error', {'workflow': workflow_name, 'error': result.get('message')})
        
        status_code = 200 if result['status'] == 'success' else 500
        return jsonify(result), status_code
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Rollback failed: {str(e)}"
        }), 500


@api_bp.route('/workflows/<service_id>/health', methods=['GET'])
@require_auth('read')
def api_workflow_health(service_id):
    """
    Check health of a deployed workflow.
    
    Response:
    {
        "status": "healthy",
        "deployment_status": "SUCCESS",
        "last_deployed": "2026-02-18T10:30:00Z"
    }
    """
    try:
        railway_token = os.getenv('RAILWAY_API_TOKEN')
        project_id = os.getenv('RAILWAY_PROJECT_ID')
        env_id = os.getenv('RAILWAY_ENV_ID', 'production')
        
        service = DeploymentService(
            railway_api_token=railway_token,
            project_id=project_id,
            environment_id=env_id
        )
        
        health = service.get_service_health(service_id)
        return jsonify(health)
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@api_bp.route('/deployments', methods=['GET'])
@require_auth('read')
def api_list_deployments():
    """
    List deployment history.
    
    Query params:
    - limit: Max number of deployments to return (default: 50)
    - workflow: Filter by workflow name
    
    Response:
    {
        "total": 25,
        "deployments": [
            {
                "id": "dep_123",
                "workflow": "cold-email-campaign",
                "status": "success",
                "deployed_at": "2026-02-18T10:30:00Z",
                "deployed_by": "admin"
            },
            ...
        ]
    }
    """
    # This would query from a database
    # For now, return a placeholder response
    limit = request.args.get('limit', 50, type=int)
    workflow_filter = request.args.get('workflow')
    
    return jsonify({
        "total": 0,
        "deployments": [],
        "message": "Deployment history tracking not yet implemented"
    })


@api_bp.route('/favorites/toggle', methods=['POST'])
@require_auth('write')
def api_toggle_favorite():
    """
    Toggle favorite status for a workflow.
    
    Request body:
    {
        "workflow_name": "cold-email-campaign"
    }
    
    Response:
    {
        "status": "success",
        "workflow": "cold-email-campaign",
        "is_favorite": true
    }
    """
    data = request.get_json()
    workflow_name = data.get('workflow_name')
    
    if not workflow_name:
        return jsonify({
            "status": "error",
            "message": "workflow_name is required"
        }), 400
    
    # This would save to a database or user preferences file
    # For now, return a placeholder
    return jsonify({
        "status": "success",
        "workflow": workflow_name,
        "is_favorite": True,
        "message": "Favorites feature not yet implemented"
    })


# =============================================================================
# Health Check
# =============================================================================

@api_bp.route('/health', methods=['GET'])
def api_health():
    """Public health check endpoint (no auth required)."""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "aiaa-dashboard-api"
    })


# =============================================================================
# Error Handlers
# =============================================================================

@api_bp.errorhandler(404)
def api_not_found(e):
    return jsonify({
        "status": "error",
        "message": "Endpoint not found"
    }), 404


@api_bp.errorhandler(500)
def api_internal_error(e):
    return jsonify({
        "status": "error",
        "message": "Internal server error"
    }), 500
