#!/usr/bin/env python3
"""
Validate Directive Metadata

Validates all directive YAML frontmatter against the schema defined in
directives/_SCHEMA.yaml. Ensures all directives have correct structure
before deployment automation can use them.

Usage:
    python3 execution/validate_directive_metadata.py
    python3 execution/validate_directive_metadata.py --directive cold_email_scriptwriter
    python3 execution/validate_directive_metadata.py --strict
    python3 execution/validate_directive_metadata.py --fix
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
SCHEMA_PATH = PROJECT_ROOT / "directives" / "_SCHEMA.yaml"
DIRECTIVES_PATH = PROJECT_ROOT / "directives"
EXECUTION_PATH = PROJECT_ROOT / "execution"

# Color codes for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def load_schema() -> Dict[str, Any]:
    """Load validation schema from _SCHEMA.yaml."""
    if not SCHEMA_PATH.exists():
        print(f"{Colors.RED}✗ Schema file not found: {SCHEMA_PATH}{Colors.RESET}")
        sys.exit(1)

    with open(SCHEMA_PATH) as f:
        return yaml.safe_load(f)

def parse_directive_frontmatter(filepath: Path) -> Optional[Dict[str, Any]]:
    """Extract YAML frontmatter from directive markdown."""
    content = filepath.read_text(encoding='utf-8')

    # Check for YAML frontmatter
    if not content.startswith("---"):
        return None

    parts = content.split("---", 2)
    if len(parts) < 3:
        return None

    try:
        metadata = yaml.safe_load(parts[1])
        return metadata if isinstance(metadata, dict) else None
    except yaml.YAMLError as e:
        return {"_yaml_error": str(e)}

def validate_field(field_name: str, value: Any, schema: Dict[str, Any], strict: bool = False) -> List[str]:
    """Validate a single field against schema rules."""
    errors = []
    field_schema = schema.get(field_name, {})

    # Required check
    if field_schema.get("required") and value is None:
        errors.append(f"Missing required field: {field_name}")
        return errors

    # If field is optional and not provided, skip validation
    if value is None:
        return errors

    # Type validation
    field_type = field_schema.get("type", "string")

    if field_type == "string":
        if not isinstance(value, str):
            errors.append(f"{field_name}: Expected string, got {type(value).__name__}")
        else:
            # Pattern validation
            if "pattern" in field_schema:
                if not re.match(field_schema["pattern"], value):
                    errors.append(f"{field_name}: Value '{value}' does not match pattern {field_schema['pattern']}")

            # Length validation
            if "max_length" in field_schema and len(value) > field_schema["max_length"]:
                errors.append(f"{field_name}: Exceeds max length {field_schema['max_length']} (current: {len(value)})")

    elif field_type == "integer":
        if not isinstance(value, int):
            errors.append(f"{field_name}: Expected integer, got {type(value).__name__}")
        else:
            # Range validation
            if "min" in field_schema and value < field_schema["min"]:
                errors.append(f"{field_name}: Value {value} below minimum {field_schema['min']}")
            if "max" in field_schema and value > field_schema["max"]:
                errors.append(f"{field_name}: Value {value} exceeds maximum {field_schema['max']}")

    elif field_type.startswith("array"):
        if not isinstance(value, list):
            errors.append(f"{field_name}: Expected array, got {type(value).__name__}")
        else:
            # Min items validation
            if "min_items" in field_schema and len(value) < field_schema["min_items"]:
                errors.append(f"{field_name}: Requires at least {field_schema['min_items']} items (current: {len(value)})")

            # Allowed values validation (for enum arrays)
            if "allowed_values" in field_schema:
                invalid = [v for v in value if v not in field_schema["allowed_values"]]
                if invalid:
                    errors.append(f"{field_name}: Invalid values {invalid}, must be from allowed list")

    elif field_type == "enum":
        allowed = field_schema.get("values", [])
        if value not in allowed:
            errors.append(f"{field_name}: Invalid value '{value}', must be one of {allowed}")

    elif field_type == "object":
        if not isinstance(value, dict):
            errors.append(f"{field_name}: Expected object, got {type(value).__name__}")
        elif strict and "properties" in field_schema:
            # Validate nested properties in strict mode
            for prop_name, prop_schema in field_schema["properties"].items():
                prop_value = value.get(prop_name)
                prop_errors = validate_field(f"{field_name}.{prop_name}", prop_value, {prop_name: prop_schema}, strict)
                errors.extend(prop_errors)

    return errors

def validate_directive(filepath: Path, schema: Dict[str, Any], strict: bool = False) -> Dict[str, Any]:
    """Validate a directive file against schema."""
    result = {
        "filepath": str(filepath),
        "valid": True,
        "errors": [],
        "warnings": []
    }

    # Check if file is excluded
    if filepath.name.startswith("_"):
        result["warnings"].append("Excluded file (starts with _)")
        return result

    # Parse frontmatter
    metadata = parse_directive_frontmatter(filepath)

    if metadata is None:
        result["valid"] = False
        result["errors"].append("Missing YAML frontmatter (must start with ---)")
        return result

    if "_yaml_error" in metadata:
        result["valid"] = False
        result["errors"].append(f"Invalid YAML: {metadata['_yaml_error']}")
        return result

    # Validate ID matches filename
    if "id" in metadata:
        expected_id = filepath.stem
        if metadata["id"] != expected_id:
            result["warnings"].append(f"ID '{metadata['id']}' doesn't match filename '{expected_id}'")

    # Validate each field
    for field_name, field_schema in schema.items():
        field_value = metadata.get(field_name)
        field_errors = validate_field(field_name, field_value, schema, strict)
        result["errors"].extend(field_errors)

    # Check for execution scripts existence
    if "execution_scripts" in metadata:
        for script_name in metadata["execution_scripts"]:
            script_path = EXECUTION_PATH / script_name
            if not script_path.exists():
                result["warnings"].append(f"Execution script not found: {script_name}")

    # Check for skill bibles existence
    if "dependencies" in metadata and "skill_bibles" in metadata["dependencies"]:
        skill_bibles_path = PROJECT_ROOT / "skills"
        for bible_name in metadata["dependencies"]["skill_bibles"]:
            bible_path = skill_bibles_path / bible_name
            if not bible_path.exists():
                result["warnings"].append(f"Skill bible not found: {bible_name}")

    # Mark as invalid if errors found
    if result["errors"]:
        result["valid"] = False

    return result

def print_validation_result(result: Dict[str, Any], verbose: bool = False):
    """Print validation result with color coding."""
    filepath = Path(result["filepath"]).name

    if result["valid"] and not result["warnings"]:
        print(f"{Colors.GREEN}✓{Colors.RESET} {filepath}")
    elif result["valid"] and result["warnings"]:
        print(f"{Colors.YELLOW}⚠{Colors.RESET} {filepath}")
        if verbose:
            for warning in result["warnings"]:
                print(f"  {Colors.YELLOW}│{Colors.RESET} {warning}")
    else:
        print(f"{Colors.RED}✗{Colors.RESET} {filepath}")
        for error in result["errors"]:
            print(f"  {Colors.RED}│{Colors.RESET} {error}")
        if verbose and result["warnings"]:
            for warning in result["warnings"]:
                print(f"  {Colors.YELLOW}│{Colors.RESET} {warning}")

def main():
    parser = argparse.ArgumentParser(description="Validate directive metadata")
    parser.add_argument("--directive", help="Validate single directive (name without .md)")
    parser.add_argument("--strict", action="store_true", help="Strict validation (check nested properties)")
    parser.add_argument("--fix", action="store_true", help="Auto-fix common issues (not implemented yet)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show warnings and details")
    args = parser.parse_args()

    # Load schema
    schema = load_schema()

    # Get files to validate
    if args.directive:
        files = [DIRECTIVES_PATH / f"{args.directive}.md"]
        if not files[0].exists():
            print(f"{Colors.RED}✗ Directive not found: {files[0]}{Colors.RESET}")
            return 1
    else:
        files = sorted(DIRECTIVES_PATH.glob("*.md"))

    # Validate
    print(f"\n{Colors.BOLD}Validating {len(files)} directive(s)...{Colors.RESET}\n")

    results = []
    for filepath in files:
        result = validate_directive(filepath, schema, strict=args.strict)
        results.append(result)
        print_validation_result(result, verbose=args.verbose)

    # Summary
    total_files = len(results)
    valid_files = sum(1 for r in results if r["valid"])
    invalid_files = total_files - valid_files
    files_with_warnings = sum(1 for r in results if r["warnings"])
    total_errors = sum(len(r["errors"]) for r in results)
    total_warnings = sum(len(r["warnings"]) for r in results)

    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}Summary{Colors.RESET}")
    print(f"{'='*60}")
    print(f"Total files:       {total_files}")
    print(f"{Colors.GREEN}Valid:{Colors.RESET}             {valid_files}")
    print(f"{Colors.RED}Invalid:{Colors.RESET}           {invalid_files}")
    print(f"{Colors.YELLOW}Warnings:{Colors.RESET}         {files_with_warnings} files, {total_warnings} total")
    print(f"{Colors.RED}Errors:{Colors.RESET}           {total_errors}")
    print(f"{'='*60}\n")

    if invalid_files > 0:
        print(f"{Colors.RED}Validation FAILED{Colors.RESET}\n")
        return 1
    elif files_with_warnings > 0:
        print(f"{Colors.YELLOW}Validation PASSED (with warnings){Colors.RESET}\n")
        return 0
    else:
        print(f"{Colors.GREEN}Validation PASSED{Colors.RESET}\n")
        return 0

if __name__ == "__main__":
    sys.exit(main())
