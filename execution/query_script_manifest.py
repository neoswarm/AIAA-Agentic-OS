#!/usr/bin/env python3
"""
Query Script Manifests - Look up dependencies and env vars for any script.

Usage:
    python3 execution/query_script_manifest.py write_cold_emails
    python3 execution/query_script_manifest.py calendly_meeting_prep --check-env
    python3 execution/query_script_manifest.py --list-packages
    python3 execution/query_script_manifest.py --list-env-vars
"""

import argparse
import json
import os
import sys
from pathlib import Path


def load_manifests():
    """Load script manifests from JSON file."""
    manifest_path = Path(__file__).parent / 'script_manifests.json'

    if not manifest_path.exists():
        print(f"❌ Error: Manifest file not found at {manifest_path}")
        print("   Run: python3 execution/analyze_script_dependencies.py")
        sys.exit(1)

    with open(manifest_path, 'r') as f:
        return json.load(f)


def load_requirements():
    """Load requirements.txt for version mapping."""
    requirements_path = Path(__file__).parent.parent / 'requirements.txt'
    version_map = {}

    if not requirements_path.exists():
        return version_map

    with open(requirements_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            if '>=' in line:
                pkg, ver = line.split('>=', 1)
                version_map[pkg.strip()] = f">={ver.strip()}"
            elif '==' in line:
                pkg, ver = line.split('==', 1)
                version_map[pkg.strip()] = f"=={ver.strip()}"
            else:
                version_map[line.strip()] = ""

    return version_map


def show_script_info(script_name, manifests, version_map, check_env=False):
    """Display dependency info for a specific script."""
    # Remove .py extension if provided
    script_key = script_name.replace('.py', '')

    if script_key not in manifests:
        print(f"❌ Script not found: {script_name}")
        print(f"\nAvailable scripts ({len(manifests)}):")
        for key in sorted(manifests.keys())[:10]:
            print(f"  - {key}")
        print(f"  ... and {len(manifests) - 10} more")
        sys.exit(1)

    manifest = manifests[script_key]

    print(f"\n{'='*70}")
    print(f"📄 Script: {manifest['script']}")
    print(f"{'='*70}")

    # Packages
    print(f"\n📦 Required Packages ({len(manifest['packages'])}):")
    if manifest['packages']:
        for pkg in manifest['packages']:
            version = version_map.get(pkg, "❓ no version")
            print(f"  - {pkg:30s} {version}")
    else:
        print("  ✅ Stdlib only - no external packages required!")

    # Environment Variables
    print(f"\n🔑 Required Environment Variables ({len(manifest['env_vars'])}):")
    if manifest['env_vars']:
        for var in manifest['env_vars']:
            if check_env:
                value = os.getenv(var)
                status = "✅ SET" if value else "❌ MISSING"
                print(f"  {status}  {var}")
            else:
                print(f"  - {var}")

        if check_env:
            missing = [var for var in manifest['env_vars'] if not os.getenv(var)]
            if missing:
                print(f"\n⚠️  Missing {len(missing)} required environment variable(s):")
                for var in missing:
                    print(f"     {var}")
            else:
                print(f"\n✅ All environment variables are set!")
    else:
        print("  ✅ No environment variables required!")

    # All imports
    print(f"\n📚 All Imports ({len(manifest['imports'])}):")
    stdlib = [imp for imp in manifest['imports'] if imp not in [p.replace('-', '_') for p in manifest['packages']]]
    print(f"  Stdlib: {', '.join(stdlib)}")
    print(f"  External: {', '.join(manifest['packages'])}")

    print()


def list_all_packages(manifests, version_map):
    """List all unique packages and their usage count."""
    package_counts = {}

    for manifest in manifests.values():
        for pkg in manifest['packages']:
            package_counts[pkg] = package_counts.get(pkg, 0) + 1

    print(f"\n{'='*70}")
    print(f"📦 All Packages ({len(package_counts)} unique)")
    print(f"{'='*70}\n")

    for pkg, count in sorted(package_counts.items(), key=lambda x: x[1], reverse=True):
        version = version_map.get(pkg, "❓ no version")
        print(f"  {count:3d} scripts use {pkg:30s} {version}")

    print()


def list_all_env_vars(manifests):
    """List all unique environment variables and their usage count."""
    env_counts = {}

    for manifest in manifests.values():
        for var in manifest['env_vars']:
            env_counts[var] = env_counts.get(var, 0) + 1

    print(f"\n{'='*70}")
    print(f"🔑 All Environment Variables ({len(env_counts)} unique)")
    print(f"{'='*70}\n")

    for var, count in sorted(env_counts.items(), key=lambda x: x[1], reverse=True):
        value = os.getenv(var)
        status = "✅" if value else "❌"
        print(f"  {status} {count:3d} scripts use {var}")

    print()


def generate_requirements(script_name, manifests, version_map):
    """Generate requirements.txt content for a specific script."""
    script_key = script_name.replace('.py', '')

    if script_key not in manifests:
        print(f"❌ Script not found: {script_name}")
        sys.exit(1)

    manifest = manifests[script_key]

    print(f"# Requirements for {manifest['script']}")
    print(f"# Generated by query_script_manifest.py\n")

    for pkg in sorted(manifest['packages']):
        version = version_map.get(pkg, "")
        print(f"{pkg}{version}")


def main():
    parser = argparse.ArgumentParser(description='Query script dependency manifests')
    parser.add_argument('script', nargs='?', help='Script name to query (without .py)')
    parser.add_argument('--check-env', action='store_true', help='Check if env vars are set')
    parser.add_argument('--list-packages', action='store_true', help='List all unique packages')
    parser.add_argument('--list-env-vars', action='store_true', help='List all env vars')
    parser.add_argument('--generate-requirements', action='store_true', help='Generate requirements.txt for script')
    args = parser.parse_args()

    manifests = load_manifests()
    version_map = load_requirements()

    if args.list_packages:
        list_all_packages(manifests, version_map)
    elif args.list_env_vars:
        list_all_env_vars(manifests)
    elif args.generate_requirements:
        if not args.script:
            print("❌ Error: --generate-requirements requires a script name")
            sys.exit(1)
        generate_requirements(args.script, manifests, version_map)
    elif args.script:
        show_script_info(args.script, manifests, version_map, check_env=args.check_env)
    else:
        print("Usage:")
        print("  python3 execution/query_script_manifest.py <script_name>")
        print("  python3 execution/query_script_manifest.py --list-packages")
        print("  python3 execution/query_script_manifest.py --list-env-vars")
        print("\nExamples:")
        print("  python3 execution/query_script_manifest.py write_cold_emails")
        print("  python3 execution/query_script_manifest.py calendly_meeting_prep --check-env")
        print("  python3 execution/query_script_manifest.py write_cold_emails --generate-requirements")


if __name__ == '__main__':
    main()
