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


def get_chat_subsystem_readiness() -> dict:
    """Return chat subsystem readiness based on configured provider keys."""
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
        "providers": providers,
        "missing_providers": missing_providers,
    }
