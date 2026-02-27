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

RUN pip install -r railway_apps/aiaa_gateway/requirements.txt \
    && npm install -g @anthropic-ai/claude-code

RUN mkdir -p /app/.tmp
