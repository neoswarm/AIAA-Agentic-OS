"""Client profile upsert service for v1 API endpoints."""

from __future__ import annotations

import re
from typing import Any, Dict

import models


_SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,99}$")
_URL_PATTERN = re.compile(r"^https?://.+\..+")
_TEXT_FIELDS = (
    "name",
    "industry",
    "website",
    "description",
    "target_audience",
    "goals",
    "competitors",
    "brand_voice",
)
_DICT_OR_STR_FIELDS = ("rules", "preferences")
_MISSING = object()


class ProfileServiceError(Exception):
    """Structured service-layer error with status code and field details."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 400,
        errors: Dict[str, str] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.errors = errors or {}


def _slugify(value: str) -> str:
    slug = value.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


def _text_field(payload: Dict[str, Any], key: str):
    if key not in payload:
        return _MISSING
    value = payload.get(key)
    if value is None:
        return None
    return str(value).strip()


def _dict_or_str_field(payload: Dict[str, Any], key: str, errors: Dict[str, str]):
    if key not in payload:
        return _MISSING

    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        return {"raw": value.strip()}

    errors[key] = "Must be an object, string, or null"
    return _MISSING


def _parse_integrity_error(exc: Exception) -> ProfileServiceError | None:
    message = str(exc)
    lowered = message.lower()
    if "client_profiles.slug" in lowered:
        return ProfileServiceError(
            "Profile slug already exists",
            status_code=409,
            errors={"slug": "Already exists"},
        )
    if "client_profiles.name" in lowered:
        return ProfileServiceError(
            "Profile name already exists",
            status_code=409,
            errors={"name": "Already exists"},
        )
    return None


def upsert_profile(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create or update a client profile by slug (or name-derived slug)."""
    if not isinstance(payload, dict):
        raise ProfileServiceError(
            "Request body must be a JSON object",
            errors={"body": "Must be a JSON object"},
        )

    errors: Dict[str, str] = {}

    raw_name = _text_field(payload, "name")
    raw_slug = _text_field(payload, "slug")

    if raw_name is _MISSING:
        name = ""
    else:
        name = raw_name or ""

    if raw_slug is _MISSING:
        slug = _slugify(name) if name else ""
    else:
        slug = _slugify(raw_slug or "")

    if not slug:
        if not name:
            errors["name"] = "Profile name is required when slug is not provided"
        errors["slug"] = "Profile slug is required"
    elif not _SLUG_PATTERN.fullmatch(slug):
        errors["slug"] = (
            "Profile slug must use lowercase letters, numbers, and hyphens only"
        )

    if raw_name is not _MISSING:
        if not name:
            errors["name"] = "Profile name cannot be empty"
        elif len(name) < 2 or len(name) > 100:
            errors["name"] = "Profile name must be between 2 and 100 characters"

    website = _text_field(payload, "website")
    if website is not _MISSING and website:
        if not _URL_PATTERN.match(website):
            errors["website"] = "Website must be a valid URL (e.g. https://example.com)"

    industry = _text_field(payload, "industry")
    if industry is not _MISSING and industry and len(industry) > 100:
        errors["industry"] = "Industry must be 100 characters or fewer"

    parsed_fields: Dict[str, Any] = {}
    for key in _TEXT_FIELDS:
        parsed_fields[key] = _text_field(payload, key)
    for key in _DICT_OR_STR_FIELDS:
        parsed_fields[key] = _dict_or_str_field(payload, key, errors)

    if errors:
        raise ProfileServiceError("Validation failed", errors=errors)

    existing = models.get_client_profile(slug)
    existing_by_name = models.get_client_profile_by_name(name) if name else None

    if existing_by_name and existing_by_name.get("slug") != slug:
        raise ProfileServiceError(
            "Profile name already belongs to another profile",
            status_code=409,
            errors={"name": "Already used by another profile"},
        )

    if existing is None and existing_by_name is not None:
        existing = existing_by_name
        slug = str(existing_by_name["slug"])

    update_data = {
        key: value for key, value in parsed_fields.items() if value is not _MISSING
    }

    if existing is not None:
        try:
            if update_data:
                models.update_client_profile(slug, **update_data)
            profile = models.get_client_profile(slug) or existing
            return {"action": "updated", "slug": slug, "profile": profile}
        except Exception as exc:
            parsed_error = _parse_integrity_error(exc)
            if parsed_error is not None:
                raise parsed_error from exc
            raise

    if not name:
        raise ProfileServiceError(
            "Profile name is required to create a new profile",
            errors={"name": "Required"},
        )

    try:
        client_id = models.create_client_profile(
            name=name,
            slug=slug,
            industry=(
                None
                if parsed_fields["industry"] is _MISSING
                else parsed_fields["industry"]
            ),
            website=(
                None
                if parsed_fields["website"] is _MISSING
                else parsed_fields["website"]
            ),
            description=(
                None
                if parsed_fields["description"] is _MISSING
                else parsed_fields["description"]
            ),
            target_audience=(
                None
                if parsed_fields["target_audience"] is _MISSING
                else parsed_fields["target_audience"]
            ),
            goals=(
                None if parsed_fields["goals"] is _MISSING else parsed_fields["goals"]
            ),
            competitors=(
                None
                if parsed_fields["competitors"] is _MISSING
                else parsed_fields["competitors"]
            ),
            brand_voice=(
                None
                if parsed_fields["brand_voice"] is _MISSING
                else parsed_fields["brand_voice"]
            ),
            rules=(
                None if parsed_fields["rules"] is _MISSING else parsed_fields["rules"]
            ),
            preferences=(
                None
                if parsed_fields["preferences"] is _MISSING
                else parsed_fields["preferences"]
            ),
        )
        profile = models.get_client_profile(slug)
        return {
            "action": "created",
            "slug": slug,
            "client_id": client_id,
            "profile": profile,
        }
    except Exception as exc:
        parsed_error = _parse_integrity_error(exc)
        if parsed_error is not None:
            raise parsed_error from exc
        raise
