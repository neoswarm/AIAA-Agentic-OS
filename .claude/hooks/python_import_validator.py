#!/usr/bin/env python3
"""
Hook 31: Python Import Validator (PreToolUse on Bash)

Before running python3 execution/*.py:
- Quick-read the first 30 lines of the script looking for import statements
- Check if non-standard imports exist
- For each non-standard import, check if installed via importlib.util.find_spec()
- If missing packages found: WARN via stderr with pip install command. Exit 0 always.
"""

import json
import sys
import os
import re
import importlib.util
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = PROJECT_ROOT / ".tmp" / "hooks"
STATE_FILE = STATE_DIR / "import_validation_log.json"

# Standard library modules (Python 3.8+) - comprehensive list
STDLIB_MODULES = {
    "abc", "aifc", "argparse", "array", "ast", "asynchat", "asyncio",
    "asyncore", "atexit", "audioop", "base64", "bdb", "binascii",
    "binhex", "bisect", "builtins", "bz2", "calendar", "cgi", "cgitb",
    "chunk", "cmath", "cmd", "code", "codecs", "codeop", "collections",
    "colorsys", "compileall", "concurrent", "configparser", "contextlib",
    "contextvars", "copy", "copyreg", "cProfile", "crypt", "csv",
    "ctypes", "curses", "dataclasses", "datetime", "dbm", "decimal",
    "difflib", "dis", "distutils", "doctest", "email", "encodings",
    "enum", "errno", "faulthandler", "fcntl", "filecmp", "fileinput",
    "fnmatch", "formatter", "fractions", "ftplib", "functools", "gc",
    "getopt", "getpass", "gettext", "glob", "grp", "gzip", "hashlib",
    "heapq", "hmac", "html", "http", "idlelib", "imaplib", "imghdr",
    "imp", "importlib", "inspect", "io", "ipaddress", "itertools",
    "json", "keyword", "lib2to3", "linecache", "locale", "logging",
    "lzma", "mailbox", "mailcap", "marshal", "math", "mimetypes",
    "mmap", "modulefinder", "multiprocessing", "netrc", "nis", "nntplib",
    "numbers", "operator", "optparse", "os", "ossaudiodev", "parser",
    "pathlib", "pdb", "pickle", "pickletools", "pipes", "pkgutil",
    "platform", "plistlib", "poplib", "posix", "posixpath", "pprint",
    "profile", "pstats", "pty", "pwd", "py_compile", "pyclbr",
    "pydoc", "queue", "quopri", "random", "re", "readline", "reprlib",
    "resource", "rlcompleter", "runpy", "sched", "secrets", "select",
    "selectors", "shelve", "shlex", "shutil", "signal", "site",
    "smtpd", "smtplib", "sndhdr", "socket", "socketserver", "spwd",
    "sqlite3", "sre_compile", "sre_constants", "sre_parse", "ssl",
    "stat", "statistics", "string", "stringprep", "struct", "subprocess",
    "sunau", "symtable", "sys", "sysconfig", "syslog", "tabnanny",
    "tarfile", "telnetlib", "tempfile", "termios", "test", "textwrap",
    "threading", "time", "timeit", "tkinter", "token", "tokenize",
    "trace", "traceback", "tracemalloc", "tty", "turtle", "turtledemo",
    "types", "typing", "unicodedata", "unittest", "urllib", "uu",
    "uuid", "venv", "warnings", "wave", "weakref", "webbrowser",
    "winreg", "winsound", "wsgiref", "xdrlib", "xml", "xmlrpc",
    "zipapp", "zipfile", "zipimport", "zlib", "_thread", "__future__",
    "typing_extensions",
}

# Known third-party packages with pip install names
PACKAGE_INSTALL_NAMES = {
    "dotenv": "python-dotenv",
    "openai": "openai",
    "anthropic": "anthropic",
    "requests": "requests",
    "google": "google-api-python-client",
    "googleapiclient": "google-api-python-client",
    "google_auth_oauthlib": "google-auth-oauthlib",
    "flask": "flask",
    "slack_sdk": "slack_sdk",
    "apify_client": "apify-client",
    "fal_client": "fal-client",
    "pandas": "pandas",
    "numpy": "numpy",
    "bs4": "beautifulsoup4",
    "beautifulsoup4": "beautifulsoup4",
    "lxml": "lxml",
    "PIL": "Pillow",
    "yaml": "pyyaml",
    "aiohttp": "aiohttp",
    "httpx": "httpx",
    "pydantic": "pydantic",
    "jinja2": "Jinja2",
    "markdown": "markdown",
    "rich": "rich",
    "click": "click",
    "tqdm": "tqdm",
    "boto3": "boto3",
    "stripe": "stripe",
    "twilio": "twilio",
    "sendgrid": "sendgrid",
    "mailchimp3": "mailchimp3",
    "selenium": "selenium",
    "playwright": "playwright",
    "scrapy": "scrapy",
}


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"checks": [], "missing_packages": {}}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def extract_imports(script_path, max_lines=30):
    """Extract import statements from the first N lines of a script."""
    imports = set()
    try:
        with open(script_path, "r") as f:
            for i, line in enumerate(f):
                if i >= max_lines:
                    break
                line = line.strip()
                # import module
                match = re.match(r'^import\s+(\w+)', line)
                if match:
                    imports.add(match.group(1))
                # from module import ...
                match = re.match(r'^from\s+(\w+)', line)
                if match:
                    imports.add(match.group(1))
    except OSError:
        pass
    return imports


def check_import_available(module_name):
    """Check if a module is importable."""
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ModuleNotFoundError, ValueError):
        return False


def is_stdlib(module_name):
    """Check if a module is part of the standard library."""
    return module_name in STDLIB_MODULES


def get_pip_name(module_name):
    """Get the pip install name for a module."""
    return PACKAGE_INSTALL_NAMES.get(module_name, module_name)


def handle_status():
    state = load_state()
    print("=== Python Import Validator Status ===")
    print(f"State file: {STATE_FILE}")
    print(f"File exists: {STATE_FILE.exists()}")

    missing = state.get("missing_packages", {})
    if missing:
        print(f"\nScripts with missing packages:")
        for script, packages in missing.items():
            print(f"  {script}: {', '.join(packages)}")
    else:
        print("\nNo missing packages detected.")

    checks = state.get("checks", [])
    if checks:
        print(f"\nRecent checks ({len(checks)}):")
        for c in checks[-10:]:
            status = "WARN" if c.get("missing") else "OK"
            print(f"  [{status}] {c.get('script', '?')}")
            if c.get("missing"):
                print(f"    Missing: {', '.join(c['missing'])}")


def handle_reset():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        print("Python import validator state reset.")
    else:
        print("No state file to reset.")


def main():
    if "--status" in sys.argv:
        handle_status()
        return
    if "--reset" in sys.argv:
        handle_reset()
        return

    # PreToolUse mode
    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except (json.JSONDecodeError, Exception):
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool_name != "Bash":
        sys.exit(0)

    command = tool_input.get("command", "")

    # Check if running a Python execution script
    match = re.search(r'python3?\s+(?:execution/)?(\w+\.py)', command)
    if not match:
        sys.exit(0)

    script_name = match.group(1)

    # Find the script file
    script_path = PROJECT_ROOT / "execution" / script_name
    if not script_path.exists():
        sys.exit(0)

    # Extract imports
    imports = extract_imports(script_path)

    # Check non-stdlib imports
    missing = []
    for module_name in imports:
        if not is_stdlib(module_name) and not check_import_available(module_name):
            missing.append(module_name)

    if missing:
        state = load_state()
        pip_names = [get_pip_name(m) for m in missing]
        state["missing_packages"][script_name] = pip_names
        state["checks"].append({
            "script": script_name,
            "missing": pip_names,
            "timestamp": datetime.now().isoformat(),
        })
        state["checks"] = state["checks"][-50:]
        save_state(state)

        pip_cmd = "pip install " + " ".join(pip_names)
        sys.stderr.write(
            f"[IMPORT VALIDATOR] {script_name} requires packages not found: "
            f"{', '.join(missing)}. Install with: {pip_cmd}\n"
        )
    else:
        state = load_state()
        state["checks"].append({
            "script": script_name,
            "missing": [],
            "timestamp": datetime.now().isoformat(),
        })
        state["checks"] = state["checks"][-50:]
        save_state(state)

    sys.exit(0)


if __name__ == "__main__":
    main()
