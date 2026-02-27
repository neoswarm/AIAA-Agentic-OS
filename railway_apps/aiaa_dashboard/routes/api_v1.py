#!/usr/bin/env python3
"""AIAA Dashboard API v1 routes."""

from __future__ import annotations

import os
import re
from functools import wraps

from flask import Blueprint, jsonify, request, session

import models
from services.profile_service import ProfileServiceError, upsert_profile
from services.gateway_runtime_canary import run_gateway_runtime_canary


api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/v1")

_PROFILE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,99}$")


def _validation_error(errors: dict[str, str]):
    return (
        jsonify(
            {
                "status": "error",
                "message": "Validation failed",
                "errors": errors,
            }
        ),
        400,
    )


def _token_setting_key(profile_id: str) -> str:
    normalized = profile_id.strip().lower()
    if normalized == "default":
        return "claude_setup_token"
    return f"{normalized}.claude_setup_token"


def login_required(f):
    """Require session login or API key auth for v1 API endpoints."""

    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("logged_in"):
            return f(*args, **kwargs)
        api_key = request.headers.get("X-API-Key")
        if api_key and api_key == os.getenv("DASHBOARD_API_KEY"):
            return f(*args, **kwargs)
        return jsonify({"status": "error", "message": "Authentication required"}), 401

    return decorated


@api_v1_bp.route("/profiles/upsert", methods=["POST"])
@login_required
def api_upsert_profile():
    """Create or update a client profile."""
    data = request.get_json(silent=True)
    if data is None:
        data = {}
    if not isinstance(data, dict):
        return _validation_error({"body": "Request body must be a JSON object"})

    try:
        result = upsert_profile(data)
        status_code = 201 if result.get("action") == "created" else 200
        payload = {"status": "ok"}
        payload.update(result)
        return jsonify(payload), status_code
    except ProfileServiceError as exc:
        payload = {"status": "error", "message": exc.message}
        if exc.errors:
            payload["errors"] = exc.errors
        return jsonify(payload), exc.status_code
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@api_v1_bp.route("/profiles/validate", methods=["POST"])
@login_required
def api_validate_profile():
    """Validate a setup-token profile by running a gateway runtime canary."""
    payload = request.get_json(silent=True)
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        return _validation_error({"body": "Request body must be a JSON object"})

    profile_id = str(payload.get("profile_id") or "").strip().lower()
    token = str(payload.get("token") or "").strip()
    errors: dict[str, str] = {}

    if not profile_id:
        errors["profile_id"] = "profile_id is required"
    elif not _PROFILE_ID_PATTERN.fullmatch(profile_id):
        errors["profile_id"] = (
            "profile_id must use lowercase letters, numbers, and hyphens only"
        )

    setting_key = ""
    if profile_id:
        setting_key = _token_setting_key(profile_id)
        if not token:
            token = (models.get_setting(setting_key) or "").strip()
        if not token:
            errors["token"] = f"No token configured for profile: {profile_id}"

    if errors:
        return _validation_error(errors)

    validation = run_gateway_runtime_canary(token)
    validation_status = str(validation.get("status") or "invalid")
    last_error = (
        str(validation.get("error") or "").strip()
        or str(validation.get("message") or "").strip()
    )
    if validation_status == "valid":
        last_error = None

    try:
        models.update_setting_metadata(
            setting_key,
            validation_status=validation_status,
            last_error=last_error,
        )
    except Exception:
        # Validation response should still be returned even if metadata update fails.
        pass

    response_payload = {
        "status": "ok",
        "profile_id": profile_id,
        "validation": validation_status,
        "validation_detail": validation,
    }

    if validation_status in {"runtime_unavailable", "runtime_error"}:
        response_payload["status"] = "error"
        response_payload["message"] = "Gateway runtime canary failed"
        return jsonify(response_payload), 502

    return jsonify(response_payload), 200
