#!/usr/bin/env python3
"""
d100_app_builder.py — D100 v3.0 Health Assessment App Injector
Injects app_config JSON into the master template (0 LLM tokens).

Usage:
  python3 d100_app_builder.py \
    --config /tmp/pwc_phase2_output.json \
    --output /path/to/output/health_assessment.html

  python3 d100_app_builder.py \
    --config-json '{"practiceName": "...", ...}' \
    --output /path/to/output/health_assessment.html
"""

import argparse
import json
import os
import sys

# ── Template location (relative to this script) ──────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TEMPLATE = os.path.join(SCRIPT_DIR, "..", "skills", "templates", "health_assessment_template.html")

# ── Token map: template placeholder → app_config key ─────────────────────────
TOKEN_MAP = {
    "{{PRACTICE_NAME}}":       "practiceName",
    "{{PRACTICE_SHORT_NAME}}": "practiceShortName",
    "{{TAGLINE}}":             "tagline",
    "{{PRIMARY_COLOR}}":       "primaryColor",
    "{{PRIMARY_DARK}}":        "primaryDark",
    "{{PRIMARY_LIGHT}}":       "primaryLight",
    "{{PRIMARY_XLIGHT}}":      "primaryXLight",
    "{{BG_COLOR}}":            "backgroundColor",
    "{{BOOKING_URL}}":         "bookingUrl",
    "{{PHONE}}":               "phone",
    "{{PROVIDER_NAME}}":       "providerName",
    "{{PROVIDER_TITLE}}":      "providerTitle",
}

JSON_TOKEN_MAP = {
    "{{CONCERNS_JSON}}":    "concerns",
    "{{SYMPTOMS_JSON}}":    "symptoms",
    "{{CARE_MODELS_JSON}}": "careModels",
}

REQUIRED_KEYS = list(TOKEN_MAP.values()) + list(JSON_TOKEN_MAP.values())


def validate_config(config: dict) -> list[str]:
    """Returns list of missing required keys."""
    missing = []
    for key in REQUIRED_KEYS:
        if key not in config:
            missing.append(key)
    return missing


def derive_missing_colors(config: dict) -> dict:
    """Auto-derive light/xlight from primary if not provided."""
    def hex_to_rgb(h):
        h = h.lstrip('#')
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    def rgb_to_hex(r, g, b):
        return f"#{r:02X}{g:02X}{b:02X}"

    def lighten(hex_color, factor):
        r, g, b = hex_to_rgb(hex_color)
        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))
        return rgb_to_hex(r, g, b)

    def darken(hex_color, factor):
        r, g, b = hex_to_rgb(hex_color)
        r = max(0, int(r * (1 - factor)))
        g = max(0, int(g * (1 - factor)))
        b = max(0, int(b * (1 - factor)))
        return rgb_to_hex(r, g, b)

    primary = config.get("primaryColor", "#4A90D9")
    if "primaryDark" not in config:
        config["primaryDark"] = darken(primary, 0.25)
    if "primaryLight" not in config:
        config["primaryLight"] = lighten(primary, 0.55)
    if "primaryXLight" not in config:
        config["primaryXLight"] = lighten(primary, 0.85)
    if "backgroundColor" not in config:
        config["backgroundColor"] = "#F8F8F8"
    return config


def inject_config(template_path: str, config: dict, output_path: str) -> None:
    """Read template, replace all tokens, write to output_path."""
    with open(template_path, encoding="utf-8") as f:
        html = f.read()

    # String replacements for scalar values
    for token, key in TOKEN_MAP.items():
        value = str(config.get(key, ""))
        html = html.replace(token, value)

    # JSON replacements for array values (no quotes around them in template)
    for token, key in JSON_TOKEN_MAP.items():
        value = json.dumps(config.get(key, []), ensure_ascii=False)
        html = html.replace(token, value)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)


def extract_app_config(phase2_json: dict) -> dict:
    """Extract app_config from full Phase 2 GPT-4o output JSON."""
    return phase2_json.get("app_config", phase2_json)


def main():
    parser = argparse.ArgumentParser(description="Inject app_config into health assessment template")
    parser.add_argument("--config", help="Path to JSON file (Phase 2 output or app_config directly)")
    parser.add_argument("--config-json", help="Raw JSON string for app_config")
    parser.add_argument("--output", required=True, help="Output HTML file path")
    parser.add_argument("--template", default=DEFAULT_TEMPLATE, help="Override template path")
    parser.add_argument("--validate-only", action="store_true", help="Only validate config, don't write")
    args = parser.parse_args()

    # ── Load config ────────────────────────────────────────────────────────────
    if args.config_json:
        raw = json.loads(args.config_json)
    elif args.config:
        if not os.path.exists(args.config):
            print(f"ERROR: Config file not found: {args.config}", file=sys.stderr)
            sys.exit(1)
        with open(args.config, encoding="utf-8") as f:
            raw = json.load(f)
    else:
        print("ERROR: Provide --config or --config-json", file=sys.stderr)
        sys.exit(1)

    # Support both full Phase 2 output and bare app_config
    config = extract_app_config(raw)
    config = derive_missing_colors(config)

    # ── Validate ───────────────────────────────────────────────────────────────
    missing = validate_config(config)
    if missing:
        print(f"WARNING: Missing {len(missing)} config keys: {missing}", file=sys.stderr)
        # Fill defaults so template doesn't have raw tokens
        for key in missing:
            config[key] = f"[{key}]"

    if args.validate_only:
        if missing:
            print(f"VALIDATION FAILED — missing: {missing}")
            sys.exit(1)
        print("VALIDATION PASSED")
        return

    # ── Check template ─────────────────────────────────────────────────────────
    if not os.path.exists(args.template):
        print(f"ERROR: Template not found: {args.template}", file=sys.stderr)
        print(f"Expected at: {DEFAULT_TEMPLATE}", file=sys.stderr)
        sys.exit(1)

    # ── Inject & write ─────────────────────────────────────────────────────────
    inject_config(args.template, config, args.output)
    print(f"✅ App written: {args.output}")
    print(f"   Practice: {config.get('practiceName', '?')}")
    print(f"   Provider: {config.get('providerName', '?')} — {config.get('providerTitle', '?')}")
    print(f"   Primary color: {config.get('primaryColor', '?')} / Dark: {config.get('primaryDark', '?')}")
    print(f"   Concerns: {len(config.get('concerns', []))} | Symptoms: {len(config.get('symptoms', []))} | Programs: {len(config.get('careModels', []))}")


if __name__ == "__main__":
    main()
