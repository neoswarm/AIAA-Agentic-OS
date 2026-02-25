"""
AIAA Dashboard - Services Module
Business logic layer for external integrations and workflow management.
"""

# Deployment Service
from .deployment_service import DeploymentService, check_required_env_vars

# Chat Store
try:
    from .chat_store import (
        ChatStore,
        InMemoryChatStore,
        RedisChatStore,
    )

    _has_chat_store = True
except ImportError:
    _has_chat_store = False

# Chat Store
try:
    from .chat_store import (
        ChatStore,
        RedisChatStore,
    )
    _has_chat_store = True
except ImportError:
    _has_chat_store = False

# Railway API (existing from other agent)
try:
    from .railway_api import (
        railway_api_call,
        get_project_env_ids,
        get_shared_variables,
        set_shared_variables,
        get_active_workflows_from_railway,
        trigger_workflow_execution,
        delete_railway_service,
        update_workflow_cron,
        toggle_cron_schedule,
        get_cron_status,
    )

    _has_railway_api = True
except ImportError:
    _has_railway_api = False

# Webhook Service
try:
    from .webhook_service import (
        forward_webhook,
        process_webhook,
        get_webhook_config,
        register_webhook,
        unregister_webhook,
        toggle_webhook,
        test_webhook,
        load_webhook_config,
        get_webhook_statistics,
        get_webhook_recent_logs,
    )

    _has_webhook_service = True
except ImportError as e:
    print(f"⚠️  Webhook service import failed: {e}")
    _has_webhook_service = False

# Build __all__ dynamically based on what's available
__all__ = [
    # Deployment Service
    "DeploymentService",
    "check_required_env_vars",
]

if _has_chat_store:
    __all__.extend(
        [
            "ChatStore",
            "InMemoryChatStore",
            "RedisChatStore",
        ]
    )

if _has_railway_api:
    __all__.extend(
        [
            "railway_api_call",
            "get_project_env_ids",
            "get_shared_variables",
            "set_shared_variables",
            "get_active_workflows_from_railway",
            "trigger_workflow_execution",
            "delete_railway_service",
            "update_workflow_cron",
            "toggle_cron_schedule",
            "get_cron_status",
        ]
    )

if _has_webhook_service:
    __all__.extend(
        [
            "forward_webhook",
            "process_webhook",
            "get_webhook_config",
            "register_webhook",
            "unregister_webhook",
            "toggle_webhook",
            "test_webhook",
            "load_webhook_config",
            "get_webhook_statistics",
            "get_webhook_recent_logs",
        ]
    )
