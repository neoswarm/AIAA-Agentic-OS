"""
Shared health endpoint helpers.
"""

import os


_CHAT_PROVIDER_ENV_VARS = {
    "openrouter": "OPENROUTER_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "perplexity": "PERPLEXITY_API_KEY",
}
_DEFAULT_CHAT_BACKEND = "provider"
_GATEWAY_REQUIRED_ENV_VARS = ("GATEWAY_BASE_URL", "GATEWAY_API_KEY")


def get_chat_subsystem_readiness() -> dict:
    """Return chat subsystem readiness based on configured provider keys."""
    chat_backend = (
        os.getenv("CHAT_BACKEND", _DEFAULT_CHAT_BACKEND) or _DEFAULT_CHAT_BACKEND
    ).strip().lower()

    if chat_backend == "gateway":
        missing_env_vars = [
            env_var for env_var in _GATEWAY_REQUIRED_ENV_VARS if not os.getenv(env_var)
        ]
        ready = len(missing_env_vars) == 0
        return {
            "ready": ready,
            "status": "ready" if ready else "not_ready",
            "backend": chat_backend,
            "providers": ["gateway"] if ready else [],
            "missing_providers": [] if ready else ["gateway"],
            "missing_env_vars": missing_env_vars,
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
    }
