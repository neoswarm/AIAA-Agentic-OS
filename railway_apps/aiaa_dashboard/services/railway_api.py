"""
AIAA Dashboard - Railway API Service
Handles all Railway GraphQL API interactions for workflow management.
"""

import os
import time
import threading
from typing import Dict, List, Optional, Any, Tuple
import requests
from config import Config


# Railway API configuration
RAILWAY_API_URL = Config.RAILWAY_API_URL
RAILWAY_API_TOKEN = Config.RAILWAY_API_TOKEN

# Workflow cache
_workflow_cache = {"data": None, "timestamp": 0}
_workflow_cache_lock = threading.Lock()


def get_project_env_ids() -> Tuple[str, str]:
    """Get project and environment IDs from config."""
    return Config.RAILWAY_PROJECT_ID, Config.RAILWAY_ENVIRONMENT_ID


def railway_api_call(query: str, variables: Dict = None, timeout: int = 30) -> Dict:
    """Make a GraphQL call to Railway API."""
    if not RAILWAY_API_TOKEN:
        return {"error": "RAILWAY_API_TOKEN not configured"}
    
    headers = {
        "Authorization": f"Bearer {RAILWAY_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    
    try:
        response = requests.post(
            RAILWAY_API_URL,
            json=payload,
            headers=headers,
            timeout=timeout
        )
        return response.json()
    except Exception as e:
        return {"error": f"Railway API request failed: {str(e)}"}


def get_shared_variables() -> Dict[str, str]:
    """Fetch project-level shared variables (no serviceId = shared)."""
    if not RAILWAY_API_TOKEN:
        return {}
    
    project_id, env_id = get_project_env_ids()
    
    query = """query variables($projectId: String!, $environmentId: String!, $serviceId: String) {
        variables(projectId: $projectId, environmentId: $environmentId, serviceId: $serviceId)
    }"""
    
    result = railway_api_call(query, {
        "projectId": project_id,
        "environmentId": env_id,
        "serviceId": None
    })
    
    if "error" in result:
        return {}
    
    data = result.get("data", {})
    if data is None:
        return {}
    
    return data.get("variables", {})


def set_shared_variables(variables: Dict[str, str]) -> Dict:
    """Set project-level shared variables via Railway GraphQL API."""
    if not RAILWAY_API_TOKEN:
        return {"error": "RAILWAY_API_TOKEN not configured"}
    
    project_id, env_id = get_project_env_ids()
    
    query = """mutation variableCollectionUpsert($input: VariableCollectionUpsertInput!) {
        variableCollectionUpsert(input: $input)
    }"""
    
    result = railway_api_call(query, {
        "input": {
            "projectId": project_id,
            "environmentId": env_id,
            "variables": variables,
        }
    })
    
    return result


def get_active_workflows_from_railway(force_refresh: bool = False) -> List[Dict[str, Any]]:
    """Fetch active workflows (cron services) from Railway API with caching."""
    cache_ttl = Config.WORKFLOW_CACHE_TTL_SECONDS
    
    with _workflow_cache_lock:
        # Check cache
        if not force_refresh and _workflow_cache["data"] is not None:
            age = time.time() - _workflow_cache["timestamp"]
            if age < cache_ttl:
                return _workflow_cache["data"]
    
    if not RAILWAY_API_TOKEN:
        return []
    
    project_id = Config.RAILWAY_PROJECT_ID
    
    query = """
    query($projectId: String!) {
        project(id: $projectId) {
            id
            name
            services {
                edges {
                    node {
                        id
                        name
                        serviceInstances {
                            edges {
                                node {
                                    id
                                    cronSchedule
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    """
    
    try:
        response = railway_api_call(query, {"projectId": project_id})
        
        if "errors" in response or not response.get("data", {}).get("project"):
            return []
        
        services = response["data"]["project"]["services"]["edges"]
        active_workflows = []
        
        for service_edge in services:
            service = service_edge["node"]
            service_id = service["id"]
            service_name = service["name"]
            
            # Get cron schedule from service instance
            instances = service.get("serviceInstances", {}).get("edges", [])
            cron_schedule = None
            for inst in instances:
                cron_schedule = inst["node"].get("cronSchedule")
                if cron_schedule:
                    break
            
            # Skip services without cron schedule
            if not cron_schedule:
                continue
            
            # Parse cron to human-readable
            cron_readable = parse_cron_to_readable(cron_schedule)
            
            active_workflows.append({
                "name": service_name,
                "description": f"Railway cron service: {service_name}",
                "schedule": cron_readable,
                "cron": cron_schedule,
                "status": "active",
                "platform": "Railway Cron",
                "last_run": "Scheduled",
                "project_id": project_id,
                "project_url": f"https://railway.com/project/{project_id}",
                "service_id": service_id
            })
        
        # Update cache
        with _workflow_cache_lock:
            _workflow_cache["data"] = active_workflows
            _workflow_cache["timestamp"] = time.time()
        
        return active_workflows
        
    except Exception as e:
        print(f"Error fetching workflows from Railway: {e}")
        return []


def invalidate_workflow_cache():
    """Invalidate the workflow cache (call after deploying new workflow)."""
    with _workflow_cache_lock:
        _workflow_cache["data"] = None
        _workflow_cache["timestamp"] = 0


def parse_cron_to_readable(cron: str) -> str:
    """Convert cron expression to human-readable string."""
    if not cron:
        return "Not scheduled"
    
    parts = cron.split()
    if len(parts) < 5:
        return cron
    
    minute, hour, day, month, weekday = parts[:5]
    
    # Common patterns
    if minute == "0" and hour.startswith("*/"):
        hours = hour[2:]
        return f"Every {hours} hours"
    if minute.startswith("*/"):
        mins = minute[2:]
        return f"Every {mins} minutes"
    if minute == "0" and hour == "*":
        return "Every hour"
    if minute == "0" and hour == "0":
        return "Daily at midnight"
    
    return f"Cron: {cron}"


def trigger_workflow_execution(service_id: str, workflow_name: str) -> Dict[str, Any]:
    """Trigger an immediate execution of a Railway cron service."""
    # Get the service instance ID
    instance_query = """
    query service($id: String!) {
        service(id: $id) {
            serviceInstances {
                edges {
                    node {
                        id
                    }
                }
            }
        }
    }
    """
    
    instance_result = railway_api_call(instance_query, {"id": service_id})
    
    if "error" in instance_result:
        return {"error": instance_result.get("error"), "status": "failed"}
    
    service_instance_id = None
    try:
        edges = instance_result.get("data", {}).get("service", {}).get("serviceInstances", {}).get("edges", [])
        if edges:
            service_instance_id = edges[0]["node"]["id"]
    except (KeyError, IndexError, TypeError):
        pass
    
    if not service_instance_id:
        return {"error": "No service instance found - service may not be deployed", "status": "failed"}
    
    # Trigger immediate execution
    execute_mutation = """
    mutation deploymentInstanceExecutionCreate($input: DeploymentInstanceExecutionCreateInput!) {
        deploymentInstanceExecutionCreate(input: $input)
    }
    """
    
    result = railway_api_call(execute_mutation, {
        "input": {"serviceInstanceId": service_instance_id}
    })
    
    if "error" in result or result.get("errors"):
        error_msg = result.get("error") or result.get("errors", [{}])[0].get("message", "Unknown error")
        return {"error": error_msg, "status": "failed"}
    
    return {
        "status": "success",
        "service_id": service_id,
        "name": workflow_name,
        "message": f"{workflow_name} triggered for immediate execution"
    }


def delete_railway_service(service_id: str, workflow_name: str) -> Dict[str, Any]:
    """Delete a Railway service (workflow deployment)."""
    # First verify the service exists
    verify_query = """
    query service($id: String!) {
        service(id: $id) {
            id
            name
        }
    }
    """
    
    verify_result = railway_api_call(verify_query, {"id": service_id})
    
    if verify_result.get("errors") or not verify_result.get("data", {}).get("service"):
        error_msg = "Service not found or already deleted"
        if verify_result.get("errors"):
            error_msg = verify_result["errors"][0].get("message", error_msg)
        return {"error": error_msg, "status": "failed"}
    
    # Delete the service
    delete_mutation = """
    mutation serviceDelete($id: String!) {
        serviceDelete(id: $id)
    }
    """
    
    result = railway_api_call(delete_mutation, {"id": service_id})
    
    if "error" in result or result.get("errors"):
        error_msg = result.get("error") or result.get("errors", [{}])[0].get("message", "Unknown error")
        return {"error": error_msg, "status": "failed"}
    
    # Invalidate cache
    invalidate_workflow_cache()
    
    return {
        "status": "success",
        "service_id": service_id,
        "name": workflow_name,
        "message": f"{workflow_name} has been deleted from Railway"
    }


def update_workflow_cron(service_id: str, workflow_name: str, new_cron: str) -> Dict[str, Any]:
    """Update the cron schedule for a workflow."""
    # Get environment ID for the service
    service_query = """
    query service($id: String!) {
        service(id: $id) {
            id
            projectId
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
    
    service_result = railway_api_call(service_query, {"id": service_id})
    
    environment_id = None
    try:
        edges = service_result.get("data", {}).get("service", {}).get("serviceInstances", {}).get("edges", [])
        if edges:
            environment_id = edges[0]["node"]["environmentId"]
    except (KeyError, TypeError, IndexError):
        pass
    
    if not environment_id:
        return {"error": "Could not find environment for service", "status": "failed"}
    
    # Update cron schedule
    update_mutation = """
    mutation serviceInstanceUpdate($serviceId: String!, $environmentId: String, $input: ServiceInstanceUpdateInput!) {
        serviceInstanceUpdate(serviceId: $serviceId, environmentId: $environmentId, input: $input)
    }
    """
    
    update_result = railway_api_call(update_mutation, {
        "serviceId": service_id,
        "environmentId": environment_id,
        "input": {"cronSchedule": new_cron}
    })
    
    if update_result.get("errors"):
        error_msg = update_result["errors"][0].get("message", "Unknown error")
        return {"error": error_msg, "status": "failed"}
    
    return {
        "status": "success",
        "service_id": service_id,
        "name": workflow_name,
        "cron": new_cron,
        "message": f"Schedule updated to {new_cron}"
    }


def toggle_cron_schedule(service_id: str, workflow_name: str, activate: bool, original_cron: str = None) -> Dict[str, Any]:
    """Activate or deactivate a cron schedule."""
    # Get environment ID
    service_query = """
    query service($id: String!) {
        service(id: $id) {
            id
            projectId
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
    
    service_result = railway_api_call(service_query, {"id": service_id})
    
    environment_id = None
    project_id = None
    try:
        service_data = service_result.get("data", {}).get("service", {})
        project_id = service_data.get("projectId")
        edges = service_data.get("serviceInstances", {}).get("edges", [])
        if edges:
            environment_id = edges[0]["node"]["environmentId"]
    except (KeyError, TypeError, IndexError):
        pass
    
    # If no environment from service instances, try getting from project
    if not environment_id and project_id:
        project_query = """
        query project($id: String!) {
            project(id: $id) {
                environments {
                    edges {
                        node {
                            id
                            name
                        }
                    }
                }
            }
        }
        """
        project_result = railway_api_call(project_query, {"id": project_id})
        try:
            env_edges = project_result.get("data", {}).get("project", {}).get("environments", {}).get("edges", [])
            for edge in env_edges:
                if edge["node"]["name"].lower() == "production":
                    environment_id = edge["node"]["id"]
                    break
            if not environment_id and env_edges:
                environment_id = env_edges[0]["node"]["id"]
        except (KeyError, TypeError, IndexError):
            pass
    
    if not environment_id:
        return {"error": "Could not find environment for service", "status": "failed"}
    
    # Update cron schedule (None to deactivate, original_cron to activate)
    update_mutation = """
    mutation serviceInstanceUpdate($serviceId: String!, $environmentId: String, $input: ServiceInstanceUpdateInput!) {
        serviceInstanceUpdate(serviceId: $serviceId, environmentId: $environmentId, input: $input)
    }
    """
    
    cron_value = original_cron if activate else None
    
    update_result = railway_api_call(update_mutation, {
        "serviceId": service_id,
        "environmentId": environment_id,
        "input": {"cronSchedule": cron_value}
    })
    
    if update_result.get("errors"):
        error_msg = update_result["errors"][0].get("message", "Unknown error")
        return {"error": error_msg, "status": "failed"}
    
    action = "activated" if activate else "deactivated"
    message = f"Cron schedule {action}"
    if activate and original_cron:
        message += f" ({original_cron})"
    
    return {
        "status": "success",
        "service_id": service_id,
        "name": workflow_name,
        "active": activate,
        "message": message
    }


def get_cron_status(service_id: str) -> Dict[str, Any]:
    """Get current cron status by checking if service has an active cron schedule."""
    query = """
    query service($id: String!) {
        service(id: $id) {
            serviceInstances {
                edges {
                    node {
                        cronSchedule
                    }
                }
            }
            deployments(first: 1) {
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
    
    result = railway_api_call(query, {"id": service_id})
    
    try:
        service_data = result.get("data", {}).get("service", {})
        
        # Check cron schedule
        instance_edges = service_data.get("serviceInstances", {}).get("edges", [])
        cron_schedule = None
        if instance_edges:
            cron_schedule = instance_edges[0]["node"].get("cronSchedule")
        
        # Check deployment status
        deployment_edges = service_data.get("deployments", {}).get("edges", [])
        deployment_status = "NO_DEPLOYMENT"
        if deployment_edges:
            deployment_status = deployment_edges[0]["node"]["status"]
        
        # Cron is active if schedule is set (not empty/null)
        is_active = bool(cron_schedule and cron_schedule.strip())
        
        return {
            "service_id": service_id,
            "active": is_active,
            "cron_schedule": cron_schedule or "",
            "deployment_status": deployment_status,
            "status": "success"
        }
    except (KeyError, TypeError) as e:
        return {
            "service_id": service_id,
            "active": True,
            "deployment_status": "UNKNOWN",
            "status": "error",
            "error": str(e)
        }
