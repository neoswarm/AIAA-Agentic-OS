FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    GATEWAY_WORKSPACE_ROOT=/app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        gnupg \
        nodejs \
        npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy full repo so gateway runtime can access skills/rules/hooks/context.
COPY . /app

RUN set -eux; \
    if [ -f "/app/railway_apps/aiaa_gateway/requirements.txt" ]; then \
        pip install -r /app/railway_apps/aiaa_gateway/requirements.txt; \
    else \
        pip install -r /app/requirements.txt; \
    fi; \
    npm install -g @anthropic-ai/claude-code

RUN useradd --create-home --shell /bin/bash appuser \
    && mkdir -p /app/.tmp \
    && chown -R appuser:appuser /app

USER appuser
