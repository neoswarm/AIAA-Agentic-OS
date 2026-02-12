#!/usr/bin/env python3
"""
Script Dependency Analyzer - AST-based dependency extraction for all execution scripts.

Generates a manifest file mapping each script to:
- All imported modules
- Required pip packages (excluding stdlib)
- Required environment variables
- Whether script uses only stdlib

Usage:
    python3 execution/analyze_script_dependencies.py

Output:
    execution/script_manifests.json
"""

import argparse
import ast
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Python standard library modules (3.10+)
STDLIB_MODULES = {
    '__future__', '_thread', 'abc', 'aifc', 'argparse', 'array', 'ast', 'asynchat', 'asyncio',
    'asyncore', 'atexit', 'audioop', 'base64', 'bdb', 'binascii', 'bisect', 'builtins', 'bz2',
    'calendar', 'cgi', 'cgitb', 'chunk', 'cmath', 'cmd', 'code', 'codecs', 'codeop',
    'collections', 'colorsys', 'compileall', 'concurrent', 'configparser', 'contextlib',
    'contextvars', 'copy', 'copyreg', 'cProfile', 'crypt', 'csv', 'ctypes', 'curses',
    'dataclasses', 'datetime', 'dbm', 'decimal', 'difflib', 'dis', 'distutils', 'doctest',
    'email', 'encodings', 'enum', 'errno', 'faulthandler', 'fcntl', 'filecmp', 'fileinput',
    'fnmatch', 'fractions', 'ftplib', 'functools', 'gc', 'getopt', 'getpass', 'gettext', 'glob',
    'graphlib', 'grp', 'gzip', 'hashlib', 'heapq', 'hmac', 'html', 'http', 'idlelib', 'imaplib',
    'imghdr', 'imp', 'importlib', 'inspect', 'io', 'ipaddress', 'itertools', 'json', 'keyword',
    'lib2to3', 'linecache', 'locale', 'logging', 'lzma', 'mailbox', 'mailcap', 'marshal', 'math',
    'mimetypes', 'mmap', 'modulefinder', 'multiprocessing', 'netrc', 'nis', 'nntplib', 'numbers',
    'operator', 'optparse', 'os', 'ossaudiodev', 'pathlib', 'pdb', 'pickle', 'pickletools',
    'pipes', 'pkgutil', 'platform', 'plistlib', 'poplib', 'posix', 'posixpath', 'pprint', 'profile',
    'pstats', 'pty', 'pwd', 'py_compile', 'pyclbr', 'pydoc', 'queue', 'quopri', 'random', 're',
    'readline', 'reprlib', 'resource', 'rlcompleter', 'runpy', 'sched', 'secrets', 'select',
    'selectors', 'shelve', 'shlex', 'shutil', 'signal', 'site', 'smtpd', 'smtplib', 'sndhdr',
    'socket', 'socketserver', 'spwd', 'sqlite3', 'ssl', 'stat', 'statistics', 'string', 'stringprep',
    'struct', 'subprocess', 'sunau', 'symtable', 'sys', 'sysconfig', 'syslog', 'tabnanny', 'tarfile',
    'telnetlib', 'tempfile', 'termios', 'test', 'textwrap', 'threading', 'time', 'timeit', 'tkinter',
    'token', 'tokenize', 'tomllib', 'trace', 'traceback', 'tracemalloc', 'tty', 'turtle', 'turtledemo',
    'types', 'typing', 'typing_extensions', 'unicodedata', 'unittest', 'urllib', 'uu', 'uuid',
    'venv', 'warnings', 'wave', 'weakref', 'webbrowser', 'winreg', 'winsound', 'wsgiref', 'xdrlib',
    'xml', 'xmlrpc', 'zipapp', 'zipfile', 'zipimport', 'zlib', 'zoneinfo'
}

# Common import name -> pip package mappings
IMPORT_TO_PACKAGE = {
    'PIL': 'Pillow',
    'cv2': 'opencv-python',
    'yaml': 'PyYAML',
    'dotenv': 'python-dotenv',
    'bs4': 'beautifulsoup4',
    'sklearn': 'scikit-learn',
    'google': 'google-auth',  # Default google import
    'google_auth_oauthlib': 'google-auth-oauthlib',
    'googleapiclient': 'google-api-python-client',
    'openai': 'openai',
    'anthropic': 'anthropic',
    'requests': 'requests',
    'pandas': 'pandas',
    'numpy': 'numpy',
    'modal': 'modal',
    'pinecone': 'pinecone-client',
    'playwright': 'playwright',
    'httpx': 'httpx',
    'gspread': 'gspread',
    'cohere': 'cohere',
    'apify_client': 'apify-client',
    'html2text': 'html2text',
    'mediapipe': 'mediapipe',
    'fastapi': 'fastapi',
    'stripe': 'stripe',
}


class DependencyExtractor(ast.NodeVisitor):
    """AST visitor to extract imports and environment variable accesses."""

    def __init__(self):
        self.imports: Set[str] = set()
        self.env_vars: Set[str] = set()

    def visit_Import(self, node: ast.Import):
        """Handle 'import module' statements."""
        for alias in node.names:
            # Get top-level module name (e.g., 'os' from 'os.path')
            module = alias.name.split('.')[0]
            self.imports.add(module)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Handle 'from module import ...' statements."""
        if node.module:
            # Get top-level module name
            module = node.module.split('.')[0]
            self.imports.add(module)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        """Extract environment variable accesses from os.getenv() and os.environ.get()."""
        # Check for os.getenv("VAR_NAME")
        if isinstance(node.func, ast.Attribute):
            if (isinstance(node.func.value, ast.Name) and
                node.func.value.id == 'os' and
                node.func.attr in ('getenv', 'environ')):
                # Handle os.getenv("VAR")
                if node.args and isinstance(node.args[0], ast.Constant):
                    self.env_vars.add(node.args[0].value)

            # Handle os.environ.get("VAR")
            elif (isinstance(node.func.value, ast.Attribute) and
                  isinstance(node.func.value.value, ast.Name) and
                  node.func.value.value.id == 'os' and
                  node.func.value.attr == 'environ' and
                  node.func.attr == 'get'):
                if node.args and isinstance(node.args[0], ast.Constant):
                    self.env_vars.add(node.args[0].value)

        self.generic_visit(node)


def map_import_to_package(import_name: str) -> str:
    """Map import name to pip package name."""
    # Skip local execution imports (not pip packages)
    # These are scripts from the execution/ directory
    local_prefixes = [
        'create_', 'generate_', 'send_', 'scrape_', 'write_', 'analyze_',
        'calculate_', 'classify_', 'convert_', 'deploy_', 'enrich_',
        'extract_', 'fetch_', 'find_', 'handle_', 'insert_', 'jump_cut_',
        'monitor_', 'parse_', 'personalize_', 'read_', 'recreate_',
        'remind_', 'repurpose_', 'research_', 'schedule_', 'score_',
        'summarize_', 'track_', 'transcribe_', 'translate_', 'triage_',
        'update_', 'upload_', 'upwork_', 'validate_', 'welcome_',
        'youtube_', 'x_keyword_', 'alert_', 'append_', 'assign_',
        'automate_', 'calendly_', 'casualize_', 'cold_', 'collect_',
        'dedupe_', 'deep_', 'fast_', 'full_', 'gmaps_', 'instantly_',
        'modal_', 'onboard_', 'pan_', 'simple_', 'stripe_', 'add_'
    ]

    if any(import_name.startswith(prefix) for prefix in local_prefixes):
        return None

    # Check direct mapping
    if import_name in IMPORT_TO_PACKAGE:
        return IMPORT_TO_PACKAGE[import_name]

    # Check for nested imports (e.g., google.auth)
    for key, value in IMPORT_TO_PACKAGE.items():
        if import_name.startswith(key + '.'):
            return value

    # Default: assume import name == package name
    return import_name


def analyze_script(script_path: Path) -> Dict:
    """Analyze a single Python script for dependencies and env vars."""
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=str(script_path))

        extractor = DependencyExtractor()
        extractor.visit(tree)

        # Separate stdlib from third-party imports
        stdlib_imports = sorted(extractor.imports & STDLIB_MODULES)
        third_party_imports = sorted(extractor.imports - STDLIB_MODULES)

        # Map imports to pip packages (filter out None for local imports)
        packages = sorted(set(
            pkg for pkg in (map_import_to_package(imp) for imp in third_party_imports)
            if pkg is not None
        ))

        # All imports combined
        all_imports = sorted(extractor.imports)

        return {
            'script': script_path.name,
            'imports': all_imports,
            'packages': packages,
            'env_vars': sorted(extractor.env_vars),
            'stdlib_only': len(packages) == 0
        }

    except SyntaxError as e:
        print(f"  ⚠️  Syntax error in {script_path.name}: {e}")
        return None
    except Exception as e:
        print(f"  ⚠️  Error parsing {script_path.name}: {e}")
        return None


def read_version_mapping(requirements_path: Path) -> Dict[str, str]:
    """Parse requirements.txt to create package -> version mapping."""
    version_map = {}

    if not requirements_path.exists():
        return version_map

    with open(requirements_path, 'r') as f:
        for line in f:
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue

            # Parse package>=version or package==version
            if '>=' in line:
                package, version = line.split('>=', 1)
                version_map[package.strip()] = f">={version.strip()}"
            elif '==' in line:
                package, version = line.split('==', 1)
                version_map[package.strip()] = f"=={version.strip()}"
            else:
                # No version specified
                version_map[line.strip()] = ""

    return version_map


def main():
    parser = argparse.ArgumentParser(description='Analyze script dependencies')
    parser.add_argument('--execution-dir',
                       default='/Users/lucasnolan/Agentic OS/execution',
                       help='Path to execution directory')
    parser.add_argument('--output',
                       default='/Users/lucasnolan/Agentic OS/execution/script_manifests.json',
                       help='Output JSON file path')
    parser.add_argument('--requirements',
                       default='/Users/lucasnolan/Agentic OS/requirements.txt',
                       help='Path to requirements.txt for version mapping')
    args = parser.parse_args()

    execution_dir = Path(args.execution_dir)
    output_path = Path(args.output)
    requirements_path = Path(args.requirements)

    if not execution_dir.exists():
        print(f"Error: Execution directory not found: {execution_dir}")
        sys.exit(1)

    print(f"\n🔍 Analyzing scripts in {execution_dir}")
    print(f"📦 Reading versions from {requirements_path}")
    print("=" * 70)

    # Read version mapping
    version_map = read_version_mapping(requirements_path)
    print(f"✓ Loaded {len(version_map)} package versions from requirements.txt\n")

    # Find all Python scripts
    scripts = sorted(execution_dir.glob('*.py'))
    print(f"Found {len(scripts)} Python scripts\n")

    # Analyze each script
    manifests = {}
    errors = []

    for i, script_path in enumerate(scripts, 1):
        print(f"[{i:3d}/{len(scripts)}] {script_path.name}...", end=' ')

        result = analyze_script(script_path)

        if result:
            manifests[script_path.stem] = result
            print(f"✓ {len(result['packages'])} packages, {len(result['env_vars'])} env vars")
        else:
            errors.append(script_path.name)
            print("✗ FAILED")

    # Save manifests
    print("\n" + "=" * 70)
    print(f"💾 Writing manifests to {output_path}")

    with open(output_path, 'w') as f:
        json.dump(manifests, f, indent=2)

    # Statistics
    all_packages = set()
    all_env_vars = set()
    stdlib_only_count = 0

    for manifest in manifests.values():
        all_packages.update(manifest['packages'])
        all_env_vars.update(manifest['env_vars'])
        if manifest['stdlib_only']:
            stdlib_only_count += 1

    print("\n" + "=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)
    print(f"Total scripts analyzed:      {len(manifests)}")
    print(f"Failed to parse:             {len(errors)}")
    print(f"Stdlib-only scripts:         {stdlib_only_count}")
    print(f"Unique packages required:    {len(all_packages)}")
    print(f"Unique env vars required:    {len(all_env_vars)}")

    if errors:
        print(f"\n⚠️  Failed scripts:")
        for err in errors:
            print(f"  - {err}")

    print(f"\n📦 Top 10 Most Common Packages:")
    package_counts = {}
    for manifest in manifests.values():
        for pkg in manifest['packages']:
            package_counts[pkg] = package_counts.get(pkg, 0) + 1

    for pkg, count in sorted(package_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        version = version_map.get(pkg, "❓ no version")
        print(f"  {count:3d} scripts use {pkg:30s} {version}")

    print(f"\n🔑 Top 10 Most Common Env Vars:")
    env_counts = {}
    for manifest in manifests.values():
        for var in manifest['env_vars']:
            env_counts[var] = env_counts.get(var, 0) + 1

    for var, count in sorted(env_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {count:3d} scripts use {var}")

    print(f"\n✅ Complete! Manifests saved to: {output_path}")
    print(f"📄 Run 'cat {output_path} | jq' to view formatted output\n")


if __name__ == '__main__':
    main()
