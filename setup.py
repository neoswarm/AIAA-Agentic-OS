#!/usr/bin/env python3
"""
AIAA Agentic OS Setup Wizard
Interactive configuration for non-technical users.
"""

import os
import sys
import hashlib
import secrets
import getpass
import webbrowser
import signal
import re
import shutil
import subprocess
from pathlib import Path

# ═══════════════════════════════════════════════════════════
# ANSI Color Constants
# ═══════════════════════════════════════════════════════════

# Detect if terminal supports colors
COLORS_ENABLED = sys.stdout.isatty()

if COLORS_ENABLED:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"
else:
    GREEN = YELLOW = RED = CYAN = BOLD = RESET = ""


# ═══════════════════════════════════════════════════════════
# Helper Functions
# ═══════════════════════════════════════════════════════════

def print_banner(text):
    """Print a styled banner."""
    width = 60
    print(f"\n{BOLD}{CYAN}{'═' * width}")
    print(f"{text:^{width}}")
    print(f"{'═' * width}{RESET}\n")


def print_step(step, total, title):
    """Print a step header."""
    print(f"\n{BOLD}{CYAN}[{step}/{total}] {title}{RESET}")
    print(f"{CYAN}{'─' * 60}{RESET}\n")


def print_success(message):
    """Print a success message."""
    print(f"{GREEN}✓ {message}{RESET}")


def print_error(message):
    """Print an error message."""
    print(f"{RED}✗ {message}{RESET}")


def print_info(message):
    """Print an info message."""
    print(f"{CYAN}ℹ {message}{RESET}")


def print_prompt(message):
    """Print a prompt message."""
    return input(f"{YELLOW}→ {message}{RESET}")


def handle_interrupt(sig, frame):
    """Handle Ctrl+C gracefully."""
    print(f"\n\n{YELLOW}Setup cancelled. Run 'python3 setup.py' to resume anytime.{RESET}\n")
    sys.exit(0)


def redact_key(key):
    """Redact API key to show first 4 and last 4 chars."""
    if len(key) <= 8:
        return "..." + key[-4:]
    return key[:4] + "..." + key[-4:]


def upsert_env_var(key: str, value: str):
    """Insert or update a key in .env."""
    env_path = Path(".env")
    if not env_path.exists():
        return

    lines = env_path.read_text().splitlines()
    updated = False
    for idx, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[idx] = f"{key}={value}"
            updated = True
            break

    if not updated:
        lines.append(f"{key}={value}")

    env_path.write_text("\n".join(lines).rstrip() + "\n")


def read_env_var(key: str):
    """Read a key from .env if present."""
    env_path = Path(".env")
    if not env_path.exists():
        return ""
    for line in env_path.read_text().splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip()
    return ""


def test_openrouter_key(key: str) -> tuple:
    """Test OpenRouter API key by hitting the models endpoint."""
    try:
        import requests
        resp = requests.get(
            "https://openrouter.ai/api/v1/models",
            headers={"Authorization": f"Bearer {key}"},
            timeout=10
        )
        if resp.status_code == 200:
            return True, "Connected to OpenRouter"
        elif resp.status_code == 401:
            return False, "Invalid API key (401 Unauthorized)"
        else:
            return False, f"Unexpected response: {resp.status_code}"
    except ImportError:
        return True, "Skipped (requests not installed)"
    except Exception as e:
        return False, f"Connection failed: {e}"


def test_perplexity_key(key: str) -> tuple:
    """Test Perplexity API key."""
    try:
        import requests
        resp = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": "sonar", "messages": [{"role": "user", "content": "test"}]},
            timeout=10
        )
        if resp.status_code == 200:
            return True, "Connected to Perplexity"
        elif resp.status_code == 401:
            return False, "Invalid API key (401 Unauthorized)"
        else:
            return False, f"Unexpected response: {resp.status_code}"
    except ImportError:
        return True, "Skipped (requests not installed)"
    except Exception as e:
        return False, f"Connection failed: {e}"


def test_slack_webhook(url: str) -> tuple:
    """Test Slack webhook by sending a test message."""
    try:
        import requests
        resp = requests.post(
            url,
            json={"text": "AIAA Agentic OS setup test - you can ignore this message."},
            timeout=10
        )
        if resp.status_code == 200:
            return True, "Slack webhook working"
        else:
            return False, f"Webhook returned status {resp.status_code}"
    except ImportError:
        return True, "Skipped (requests not installed)"
    except Exception as e:
        return False, f"Connection failed: {e}"


# ═══════════════════════════════════════════════════════════
# Step 1: Welcome Screen
# ═══════════════════════════════════════════════════════════

def step_welcome():
    """Display welcome screen and overview."""
    print_banner("AIAA Agentic OS Setup v5.0")
    
    print(f"{BOLD}Welcome!{RESET} This wizard will help you:")
    print("  • Configure API keys for AI and automation")
    print("  • Create your agency profile (optional)")
    print("  • Set up dashboard access (optional)")
    print()
    print(f"{CYAN}This takes about 5-10 minutes. You can skip optional steps.{RESET}")
    print()
    
    input(f"{YELLOW}Press Enter to begin...{RESET}")


# ═══════════════════════════════════════════════════════════
# Step 2: OpenRouter API Key (REQUIRED)
# ═══════════════════════════════════════════════════════════

def step_openrouter():
    """Configure OpenRouter API key (required)."""
    print_step(2, 8, "OpenRouter API Key (Required)")
    
    print(f"{BOLD}What is this?{RESET} This powers all 133 AI skills in the system.")
    print()
    print("To get your key:")
    print("  1. Visit https://openrouter.ai/keys (opening in browser...)")
    print("  2. Sign up or log in")
    print("  3. Go to Profile → Keys")
    print("  4. Click 'Create Key' and copy it")
    print()
    
    # Open browser
    try:
        webbrowser.open("https://openrouter.ai/keys")
        print_success("Browser opened")
    except Exception:
        print_info("Couldn't open browser automatically. Please visit the URL manually.")
    
    print()
    
    # Validate key with retries
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        key = print_prompt("Paste your OpenRouter API key: ").strip()
        
        if key.lower() == "skip":
            confirm = print_prompt("⚠️  System won't work without this key. Skip anyway? (yes/no): ").lower()
            if confirm == "yes":
                print_error("Skipped OpenRouter key. You'll need to add it manually to .env later.")
                return None
            else:
                continue
        
        # Validate
        if key.startswith("sk-or-") and len(key) >= 20:
            print_info("Testing connection...")
            success, message = test_openrouter_key(key)
            if success:
                print_success(f"Valid key: {redact_key(key)} - {message}")
                return key
            else:
                print_error(f"Key format OK but test failed: {message}")
                use_anyway = print_prompt("Use this key anyway? (y/n): ").lower()
                if use_anyway in ["y", "yes"]:
                    return key
        else:
            print_error(f"Invalid key. Must start with 'sk-or-' and be at least 20 characters.")
            if attempt < max_retries:
                print_info(f"Try again ({attempt}/{max_retries})")
    
    print_error("Max retries reached. You'll need to add the key manually to .env later.")
    return None


# ═══════════════════════════════════════════════════════════
# Step 3: Optional API Keys
# ═══════════════════════════════════════════════════════════

def step_optional_keys():
    """Configure optional API keys."""
    print_step(3, 8, "Optional API Keys")
    
    keys = {}
    
    response = print_prompt("Want to add research & notification keys? (y/n/skip): ").lower()
    
    if response not in ["y", "yes"]:
        print_info("Skipped optional keys. You can add them later from the dashboard.")
        return keys
    
    print()
    
    # Perplexity
    print(f"{BOLD}Perplexity API Key{RESET} (for deep research and market intelligence)")
    print("Opening https://www.perplexity.ai/settings/api ...")
    try:
        webbrowser.open("https://www.perplexity.ai/settings/api")
    except Exception:
        pass
    
    perplexity_key = print_prompt("Paste Perplexity API key (or 'skip'): ").strip()
    if perplexity_key.lower() != "skip":
        if perplexity_key.startswith("pplx-"):
            print_info("Testing connection...")
            success, message = test_perplexity_key(perplexity_key)
            if success:
                keys["PERPLEXITY_API_KEY"] = perplexity_key
                print_success(f"Added: {redact_key(perplexity_key)} - {message}")
            else:
                print_error(f"Test failed: {message}")
                use_anyway = print_prompt("Use this key anyway? (y/n): ").lower()
                if use_anyway in ["y", "yes"]:
                    keys["PERPLEXITY_API_KEY"] = perplexity_key
        else:
            print_error("Invalid Perplexity key (should start with 'pplx-'). Skipping.")
    
    print()
    
    # Slack
    print(f"{BOLD}Slack Webhook URL{RESET} (for task completion notifications)")
    print("Opening https://api.slack.com/messaging/webhooks ...")
    try:
        webbrowser.open("https://api.slack.com/messaging/webhooks")
    except Exception:
        pass
    
    slack_url = print_prompt("Paste Slack webhook URL (or 'skip'): ").strip()
    if slack_url.lower() != "skip":
        if slack_url.startswith("https://hooks.slack.com/"):
            print_info("Testing webhook...")
            success, message = test_slack_webhook(slack_url)
            if success:
                keys["SLACK_WEBHOOK_URL"] = slack_url
                print_success(f"Added: {redact_key(slack_url)} - {message}")
            else:
                print_error(f"Test failed: {message}")
                use_anyway = print_prompt("Use this webhook anyway? (y/n): ").lower()
                if use_anyway in ["y", "yes"]:
                    keys["SLACK_WEBHOOK_URL"] = slack_url
        else:
            print_error("Invalid Slack webhook (should start with 'https://hooks.slack.com/'). Skipping.")
    
    return keys


# ═══════════════════════════════════════════════════════════
# Step 4: Create .env File
# ═══════════════════════════════════════════════════════════

def step_create_env(openrouter_key, optional_keys):
    """Create .env file from template."""
    print_step(4, 8, "Create Configuration File")
    
    env_path = Path(".env")
    example_path = Path(".env.example")
    
    # Check if .env exists
    if env_path.exists():
        response = print_prompt("Found existing .env. Overwrite? (y/n): ").lower()
        if response not in ["y", "yes"]:
            print_info("Keeping existing .env file.")
            return
    
    # Read template
    if not example_path.exists():
        print_error(".env.example not found. Creating minimal .env...")
        template = "OPENROUTER_API_KEY=\nFLASK_SECRET_KEY=\n"
    else:
        with open(example_path, "r") as f:
            template = f.read()
    
    # Generate Flask secret
    flask_secret = secrets.token_hex(32)
    
    # Replace values
    if openrouter_key:
        template = template.replace("OPENROUTER_API_KEY=", f"OPENROUTER_API_KEY={openrouter_key}")

    for key, value in optional_keys.items():
        template = template.replace(f"{key}=", f"{key}={value}")
    
    template = template.replace("FLASK_SECRET_KEY=", f"FLASK_SECRET_KEY={flask_secret}")
    
    # Write .env
    with open(env_path, "w") as f:
        f.write(template)

    # Carry forward token captured during install.sh (if present)
    claude_token = os.getenv("CLAUDE_SETUP_TOKEN", "").strip()
    if claude_token:
        upsert_env_var("CLAUDE_SETUP_TOKEN", claude_token)
    
    print_success("Created .env file")
    print()
    print(f"{BOLD}Configured:{RESET}")
    if openrouter_key:
        print(f"  • OpenRouter: {redact_key(openrouter_key)}")
    if "PERPLEXITY_API_KEY" in optional_keys:
        print(f"  • Perplexity: {redact_key(optional_keys['PERPLEXITY_API_KEY'])}")
    if "SLACK_WEBHOOK_URL" in optional_keys:
        print(f"  • Slack: {redact_key(optional_keys['SLACK_WEBHOOK_URL'])}")
    if claude_token:
        print(f"  • Claude token: {redact_key(claude_token)}")
    print(f"  • Flask Secret: (auto-generated)")


# ═══════════════════════════════════════════════════════════
# Step 5: Agency Profile
# ═══════════════════════════════════════════════════════════

def step_agency_profile():
    """Create agency profile (optional)."""
    print_step(5, 8, "Agency Profile (Optional)")
    
    print("This personalizes all content the AI generates for you.")
    print()
    
    response = print_prompt("Want to set up your agency profile? (y/n): ").lower()
    if response not in ["y", "yes"]:
        print_info("Skipped agency profile. You can add it later.")
        return
    
    print()
    print(f"{CYAN}Answer one question at a time (or press Enter to skip):{RESET}")
    print()
    
    # Collect info
    agency_name = print_prompt("Agency name: ").strip() or "Your Agency"
    website = print_prompt("Website URL (optional): ").strip() or "https://yoursite.com"
    services = print_prompt("Services offered: ").strip() or "AI automation, marketing, content"
    audience = print_prompt("Target audience: ").strip() or "B2B businesses"
    differentiator = print_prompt("What makes you different: ").strip() or "Data-driven approach"
    
    print()
    print(f"{CYAN}Brand voice (pick one or describe):{RESET}")
    print("  Examples: professional, casual, bold, friendly, technical, conversational")
    voice = print_prompt("Brand voice: ").strip() or "professional"
    
    owner = print_prompt("Owner/founder name: ").strip() or "Your Name"
    
    # Create context directory
    context_dir = Path("context")
    context_dir.mkdir(exist_ok=True)
    
    # Check for existing files
    overwrite_all = False
    for filename in ["agency.md", "brand_voice.md", "services.md", "owner.md"]:
        filepath = context_dir / filename
        if filepath.exists() and not overwrite_all:
            response = print_prompt(f"{filename} exists. Overwrite? (y/n/all): ").lower()
            if response == "all":
                overwrite_all = True
            elif response not in ["y", "yes"]:
                print_info(f"Keeping existing {filename}")
                continue
    
    # Write agency.md
    agency_md = f"""# {agency_name}

## Overview
{agency_name} specializes in {services.lower()}.

**Target Audience:** {audience}

**Differentiator:** {differentiator}

## Website
{website}

## Contact
Owner: {owner}
"""
    
    with open(context_dir / "agency.md", "w") as f:
        f.write(agency_md)
    
    # Write brand_voice.md
    voice_md = f"""# Brand Voice Guide

## Voice Characteristics
**Primary Voice:** {voice.title()}

## Tone Guidelines
- Write in a {voice} tone
- Keep content aligned with our {differentiator.lower()} positioning
- Speak to {audience.lower()} with clarity and authority

## Do's
- Use clear, actionable language
- Focus on results and value
- Stay consistent with our brand identity

## Don'ts
- Don't use jargon unless targeting technical audiences
- Don't make promises we can't keep
- Don't copy competitor messaging
"""
    
    with open(context_dir / "brand_voice.md", "w") as f:
        f.write(voice_md)
    
    # Write services.md
    services_md = f"""# Services

## Core Offerings
{services}

## Target Market
{audience}

## Service Delivery
We deliver {services.lower()} with a focus on {differentiator.lower()}.
"""
    
    with open(context_dir / "services.md", "w") as f:
        f.write(services_md)
    
    # Write owner.md
    owner_md = f"""# Owner Profile

**Name:** {owner}
**Role:** Founder
**Agency:** {agency_name}

## Expertise
{differentiator}

## Contact
Website: {website}
"""
    
    with open(context_dir / "owner.md", "w") as f:
        f.write(owner_md)
    
    print()
    print_success("Created agency profile in context/")
    print(f"  • agency.md")
    print(f"  • brand_voice.md")
    print(f"  • services.md")
    print(f"  • owner.md")


# ═══════════════════════════════════════════════════════════
# Step 6: Dashboard Password
# ═══════════════════════════════════════════════════════════

def step_dashboard_password():
    """Set up dashboard password (optional)."""
    print_step(6, 8, "Dashboard Password (Optional)")
    
    print("Secure your web dashboard with a password.")
    print()
    
    response = print_prompt("Want to set up a dashboard password? (y/n): ").lower()
    if response not in ["y", "yes"]:
        print_info("Skipped dashboard password. Default: admin/admin")
        return
    
    print()
    
    # Get username
    username = print_prompt("Username [admin]: ").strip() or "admin"
    
    # Get password
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        password = getpass.getpass(f"{YELLOW}→ Password (min 8 chars): {RESET}").strip()
        
        if len(password) < 8:
            print_error("Password must be at least 8 characters.")
            if attempt < max_retries:
                continue
            else:
                print_info("Skipped password setup.")
                return
        
        confirm = getpass.getpass(f"{YELLOW}→ Confirm password: {RESET}").strip()
        
        if password != confirm:
            print_error("Passwords don't match.")
            if attempt < max_retries:
                continue
            else:
                print_info("Skipped password setup.")
                return
        
        # Hash password
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        # Update .env
        upsert_env_var("DASHBOARD_USERNAME", username)
        upsert_env_var("DASHBOARD_PASSWORD_HASH", password_hash)
        
        print()
        print_success(f"Dashboard secured: {username} / ********")
        return


# ═══════════════════════════════════════════════════════════
# Step 7: Claude Setup Token
# ═══════════════════════════════════════════════════════════

def step_claude_token():
    """Capture Claude setup token and store it in .env."""
    print_step(7, 8, "Claude Setup Token (Optional)")

    print("This lets the dashboard run Claude agent loops from the browser.")
    print("You only need to do this once.")
    print()

    if shutil.which("claude") is None:
        print_info("Claude CLI not found. Install with: npm install -g @anthropic-ai/claude-code")
        return None

    existing_token = os.getenv("CLAUDE_SETUP_TOKEN", "").strip() or read_env_var("CLAUDE_SETUP_TOKEN")
    if existing_token:
        print_success(f"Existing Claude token detected: {redact_key(existing_token)}")
        keep = print_prompt("Keep this token? (y/n): ").lower().strip()
        if keep in ["y", "yes"]:
            upsert_env_var("CLAUDE_SETUP_TOKEN", existing_token)
            return existing_token

    response = print_prompt("Set up Claude token now? (y/n): ").lower().strip()
    if response not in ["y", "yes"]:
        print_info("Skipped. You can add it later in Dashboard Settings.")
        return None

    print()
    print_info("Running 'claude setup-token' (browser login may open)...")

    token = None
    try:
        result = subprocess.run(
            ["claude", "setup-token"],
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        output = (result.stdout or "") + "\n" + (result.stderr or "")
        # Most setup tokens are JWT-like strings that begin with 'eyJ'.
        match = re.search(r"(eyJ[A-Za-z0-9._-]+)", output)
        if match:
            token = match.group(1).strip()
    except subprocess.TimeoutExpired:
        print_error("Token setup timed out.")
    except Exception as exc:
        print_error(f"Token setup command failed: {exc}")

    if not token:
        print()
        print_info("Could not auto-capture token from CLI output.")
        token = print_prompt("Paste Claude setup token manually (or press Enter to skip): ").strip()

    if not token:
        print_info("Skipped Claude token setup.")
        return None

    upsert_env_var("CLAUDE_SETUP_TOKEN", token)
    print_success(f"Claude token saved to .env: {redact_key(token)}")
    return token


# ═══════════════════════════════════════════════════════════
# Step 8: Done
# ═══════════════════════════════════════════════════════════

def step_done(openrouter_key, optional_keys, claude_token=None):
    """Display completion summary."""
    print_step(8, 8, "Setup Complete!")
    
    print(f"{BOLD}Configuration Summary:{RESET}")
    print()
    
    if openrouter_key:
        print(f"{GREEN}✓{RESET} OpenRouter API: {redact_key(openrouter_key)}")
    else:
        print(f"{RED}✗{RESET} OpenRouter API: Not configured")
    
    if "PERPLEXITY_API_KEY" in optional_keys:
        print(f"{GREEN}✓{RESET} Perplexity API: {redact_key(optional_keys['PERPLEXITY_API_KEY'])}")
    
    if "SLACK_WEBHOOK_URL" in optional_keys:
        print(f"{GREEN}✓{RESET} Slack Webhook: {redact_key(optional_keys['SLACK_WEBHOOK_URL'])}")
    
    if Path("context/agency.md").exists():
        print(f"{GREEN}✓{RESET} Agency profile created")
    
    if Path(".env").exists():
        with open(".env", "r") as f:
            if "DASHBOARD_PASSWORD_HASH=" in f.read() and "DASHBOARD_PASSWORD_HASH=\n" not in f.read():
                print(f"{GREEN}✓{RESET} Dashboard password configured")
    if claude_token:
        print(f"{GREEN}✓{RESET} Claude setup token: {redact_key(claude_token)}")
    
    print()
    print(f"{BOLD}{CYAN}Next Steps:{RESET}")
    print()
    print("1. Launch Claude Code:")
    print(f"   {YELLOW}claude{RESET}")
    print()
    print("2. Say to Claude:")
    print(f'   {YELLOW}"I just set up AIAA Agentic OS. Read AGENTS.md and help me test it."{RESET}')
    print()
    print("3. Optional — Deploy your dashboard:")
    print(f'   {YELLOW}"Deploy my dashboard to Railway"{RESET}')
    print()
    print("4. If dashboard is deployed, open /chat and run a first request:")
    print(f'   {YELLOW}"Write cold emails for Acme Corp targeting CTOs"{RESET}')
    print()
    
    print_banner("Setup Complete! 🚀")


# ═══════════════════════════════════════════════════════════
# Main Function
# ═══════════════════════════════════════════════════════════

def main():
    """Run the setup wizard."""
    # Handle Ctrl+C
    signal.signal(signal.SIGINT, handle_interrupt)
    
    try:
        # Step 1: Welcome
        step_welcome()
        
        # Step 2: OpenRouter (required)
        openrouter_key = step_openrouter()
        
        # Step 3: Optional keys
        optional_keys = step_optional_keys()
        
        # Step 4: Create .env
        step_create_env(openrouter_key, optional_keys)
        
        # Step 5: Agency profile
        step_agency_profile()
        
        # Step 6: Dashboard password
        step_dashboard_password()

        # Step 7: Claude token
        claude_token = step_claude_token()

        # Step 8: Done
        step_done(openrouter_key, optional_keys, claude_token=claude_token)
        
    except KeyboardInterrupt:
        handle_interrupt(None, None)
    except Exception as e:
        print()
        print_error(f"Unexpected error: {e}")
        print(f"{YELLOW}Please report this issue or run setup again.{RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
