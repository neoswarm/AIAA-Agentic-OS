"""
Shared health endpoint helpers.
"""

import os

from services.gateway_client import (
    GatewayClient,
    GatewayClientError,
    GatewayHTTPError,
    RetryConfig,
)


_CHAT_PROVIDER_ENV_VARS = {
    "openrouter": "OPENROUTER_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "perplexity": "PERPLEXITY_API_KEY",
}
_DEFAULT_CHAT_BACKEND = "provider"
_GATEWAY_REQUIRED_ENV_VARS = ("GATEWAY_BASE_URL", "GATEWAY_API_KEY")
_GATEWAY_HEALTH_PATH = "/health"
_GATEWAY_CONNECTIVITY_TIMEOUT_SECONDS = 3.0


def _check_gateway_connectivity(base_url: str, api_key: str) -> dict:
    """Return gateway connectivity metadata for readiness health payloads."""
    try:
        GatewayClient(
            base_url,
            api_key=api_key,
            timeout_seconds=_GATEWAY_CONNECTIVITY_TIMEOUT_SECONDS,
            retry_config=RetryConfig(max_attempts=1),
        ).get_json(_GATEWAY_HEALTH_PATH)
    except GatewayHTTPError as exc:
        return {
            "connected": False,
            "status": "unreachable",
            "http_status": exc.status_code,
            "error": f"Gateway health check returned HTTP {exc.status_code}",
        }
    except GatewayClientError as exc:
        return {
            "connected": False,
            "status": "unreachable",
            "http_status": None,
            "error": str(exc),
        }
    except Exception as exc:  # pragma: no cover - defensive fallback
        return {
            "connected": False,
            "status": "unreachable",
            "http_status": None,
            "error": str(exc),
        }

    return {
        "connected": True,
        "status": "connected",
        "http_status": 200,
        "error": None,
    }


def get_chat_subsystem_readiness() -> dict:
    """Return chat subsystem readiness based on configured provider keys."""
    chat_backend = (
        (os.getenv("CHAT_BACKEND", _DEFAULT_CHAT_BACKEND) or _DEFAULT_CHAT_BACKEND)
        .strip()
        .lower()
    )

    if chat_backend == "gateway":
        missing_env_vars = [
            env_var for env_var in _GATEWAY_REQUIRED_ENV_VARS if not os.getenv(env_var)
        ]
        gateway_connectivity = {
            "connected": False,
            "status": "not_checked",
            "http_status": None,
            "error": "Gateway connectivity check skipped: missing required env vars",
        }
        if not missing_env_vars:
            gateway_connectivity = _check_gateway_connectivity(
                str(os.getenv("GATEWAY_BASE_URL", "")),
                str(os.getenv("GATEWAY_API_KEY", "")),
            )
        ready = len(missing_env_vars) == 0 and gateway_connectivity["connected"]
        return {
            "ready": ready,
            "status": "ready" if ready else "not_ready",
            "backend": chat_backend,
            "providers": ["gateway"] if ready else [],
            "missing_providers": [] if ready else ["gateway"],
            "missing_env_vars": missing_env_vars,
            "gateway_connectivity": gateway_connectivity,
        }

    providers = []
    missing_providers = []

    for provider, env_var in _CHAT_PROVIDER_ENV_VARS.items():
        if os.getenv(env_var):
            providers.append(provider)
        else:
            missing_providers.append(provider)

    ready = bool(providers)
    return {
        "ready": ready,
        "status": "ready" if ready else "not_ready",
        "backend": chat_backend,
        "providers": providers,
        "missing_providers": missing_providers,
        "missing_env_vars": [],
        "gateway_connectivity": {
            "connected": None,
            "status": "not_applicable",
            "http_status": None,
            "error": None,
        },
    }
