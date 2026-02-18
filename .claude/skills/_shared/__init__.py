"""
AIAA Shared Utilities
Importable by all skills for common functionality.

Usage in skills:
    from _shared import error_reporter, validation
    from _shared.skill_validator import SkillValidator
"""
import os
import sys
from pathlib import Path

# Add parent directory to path so skills can import from _shared
_shared_dir = Path(__file__).parent
_skills_dir = _shared_dir.parent

if str(_skills_dir) not in sys.path:
    sys.path.insert(0, str(_skills_dir))

# Version info
__version__ = "1.0.0"
__author__ = "AIAA Agentic OS"

# Common utilities that skills might need
def get_project_root() -> Path:
    """Get the project root directory."""
    return _skills_dir.parent.parent

def get_tmp_dir() -> Path:
    """Get the .tmp directory for outputs."""
    tmp_dir = get_project_root() / ".tmp"
    tmp_dir.mkdir(exist_ok=True)
    return tmp_dir

def load_env():
    """Load environment variables from .env file."""
    try:
        from dotenv import load_dotenv
        env_file = get_project_root() / ".env"
        if env_file.exists():
            load_dotenv(env_file)
    except ImportError:
        pass  # dotenv not installed
