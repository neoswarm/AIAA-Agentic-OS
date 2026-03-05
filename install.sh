#!/usr/bin/env bash
# ============================================================================
# AIAA Agentic OS — Installer v5.0
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/lucassynnott/AIAA-Agentic-OS/main/install.sh | bash
#   OR: bash install.sh
# ============================================================================

# --- Colors & Symbols ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

OK="✅"
FAIL="❌"
WAIT="⏳"
SKIP="⚠️"

REPO_URL="https://github.com/lucassynnott/AIAA-Agentic-OS.git"
REPO_DIR="AIAA-Agentic-OS"
FULL_INSTALL=false

# Track results: 0=success, 1=failed, 2=skipped
declare -A RESULTS

# --- Helpers ---
banner() {
  printf "\n${CYAN}${BOLD}╔══════════════════════════════════════════════════════╗\n"
  printf "║         AIAA Agentic OS Installer v5.0              ║\n"
  printf "║         Skills-First AI Agency Framework             ║\n"
  printf "╚══════════════════════════════════════════════════════╝${NC}\n\n"
}

section() { echo -e "\n${BLUE}${BOLD}── $1 ──${NC}"; }
ok()   { echo -e "  ${GREEN}${OK}  $1${NC}"; }
fail() { echo -e "  ${RED}${FAIL}  $1${NC}"; }
skip() { echo -e "  ${YELLOW}${SKIP}  $1${NC}"; }
info() { echo -e "  ${WAIT}  $1"; }
has_cmd() { command -v "$1" &>/dev/null; }
upsert_env_line() { # $1=key $2=value $3=file
  local key="$1" value="$2" file="$3"
  [ ! -f "$file" ] && return 1
  if grep -q "^${key}=" "$file"; then
    if [ "$OS" = "macos" ]; then
      sed -i '' "s|^${key}=.*|${key}=${value}|" "$file"
    else
      sed -i "s|^${key}=.*|${key}=${value}|" "$file"
    fi
  else
    echo "${key}=${value}" >> "$file"
  fi
}

detect_os() {
  section "Detecting platform"; OS="unknown"
  case "$(uname -s)" in
    Darwin*) OS="macos";;
    Linux*)  grep -qEi "(microsoft|wsl)" /proc/version 2>/dev/null && OS="wsl" || OS="linux";;
    MINGW*|MSYS*|CYGWIN*) OS="windows";;
  esac
  case "$OS" in
    macos)   ok "macOS ($(sw_vers -productVersion 2>/dev/null || echo '?'))";;
    linux)   ok "Linux detected";;
    wsl)     ok "WSL detected — using apt-get";;
    windows) fail "Native Windows — please use WSL. Exiting."; exit 1;;
    *)       fail "Unknown OS. Trying Linux-style install."; OS="linux";;
  esac
}

install_homebrew() {
  section "Homebrew (macOS package manager)"
  if [ "$OS" != "macos" ]; then
    skip "Not macOS — skipping Homebrew"; RESULTS[homebrew]=2; return
  fi
  if has_cmd brew; then
    skip "Already installed — $(brew --version | head -1)"; RESULTS[homebrew]=2; return
  fi
  info "Installing Homebrew (may ask for your password)..."
  if /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"; then
    [ -f /opt/homebrew/bin/brew ] && eval "$(/opt/homebrew/bin/brew shellenv)"
    ok "Homebrew installed"; RESULTS[homebrew]=0
  else fail "Homebrew install failed"; RESULTS[homebrew]=1; fi
}

install_python() {
  section "Python 3.8+"
  if has_cmd python3; then skip "Already installed — $(python3 --version 2>&1)"; RESULTS[python]=2; return; fi
  info "Installing Python 3..."
  case "$OS" in
    macos) has_cmd brew && { brew install python3 && ok "Python installed" && RESULTS[python]=0 || { fail "Python install failed"; RESULTS[python]=1; }; } \
           || { fail "Install Python from python.org"; RESULTS[python]=1; };;
    linux|wsl) sudo apt-get update -qq && sudo apt-get install -y -qq python3 python3-pip python3-venv \
               && ok "Python installed" && RESULTS[python]=0 || { fail "Python install failed"; RESULTS[python]=1; };;
  esac
}

install_git() {
  section "Git"
  if has_cmd git; then skip "Already installed — $(git --version)"; RESULTS[git]=2; return; fi
  info "Installing Git..."
  case "$OS" in
    macos) has_cmd brew && { brew install git && ok "Git installed" && RESULTS[git]=0 || { fail "Git install failed"; RESULTS[git]=1; }; } \
           || { fail "Run: xcode-select --install"; RESULTS[git]=1; };;
    linux|wsl) sudo apt-get update -qq && sudo apt-get install -y -qq git \
               && ok "Git installed" && RESULTS[git]=0 || { fail "Git install failed"; RESULTS[git]=1; };;
  esac
}

install_node() {
  section "Node.js / npm"
  if has_cmd node; then skip "Already installed — node $(node --version), npm $(npm --version 2>/dev/null || echo 'n/a')"; RESULTS[node]=2; return; fi
  info "Installing Node.js..."
  case "$OS" in
    macos) has_cmd brew && { brew install node && ok "Node.js installed" && RESULTS[node]=0 || { fail "Node.js install failed"; RESULTS[node]=1; }; } \
           || { fail "Install Node.js from nodejs.org"; RESULTS[node]=1; };;
    linux|wsl) curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash - 2>/dev/null \
               && sudo apt-get install -y -qq nodejs && ok "Node.js installed" && RESULTS[node]=0 \
               || { fail "Node.js install failed"; RESULTS[node]=1; };;
  esac
}

install_npm_tool() { # $1=label $2=key $3=cmd $4=package
  section "$1"
  if has_cmd "$3"; then skip "Already installed — $("$3" --version 2>&1 | head -1)"; RESULTS[$2]=2; return; fi
  if ! has_cmd npm; then fail "npm not available"; RESULTS[$2]=1; return; fi
  info "Installing $1..."
  npm install -g "$4" 2>/dev/null && ok "$1 installed" && RESULTS[$2]=0 \
    || { fail "$1 install failed — try: npm install -g $4"; RESULTS[$2]=1; }
}

clone_repo() {
  section "Cloning AIAA Agentic OS"
  if [ -d "$REPO_DIR" ]; then
    info "Directory exists — pulling latest..."
    cd "$REPO_DIR" && git pull && ok "Repository updated" && RESULTS[repo]=0 \
      || { fail "git pull failed"; RESULTS[repo]=1; }
  else
    has_cmd git || { fail "Git not available"; RESULTS[repo]=1; return; }
    info "Cloning repository..."
    git clone "$REPO_URL" && cd "$REPO_DIR" && ok "Repository cloned" && RESULTS[repo]=0 \
      || { fail "Clone failed — check network"; RESULTS[repo]=1; }
  fi
}

install_pip_deps() {
  section "Python dependencies"
  local req_file="requirements.txt"
  if [ "$FULL_INSTALL" = true ]; then
    req_file="requirements-full.txt"
    info "Installing ALL dependencies (AI, Google, scraping, etc.)..."
  fi
  [ ! -f "$req_file" ] && { fail "$req_file not found"; RESULTS[pip_deps]=1; return; }
  has_cmd python3 || has_cmd pip3 || { fail "Python not available"; RESULTS[pip_deps]=1; return; }
  info "Installing Python packages..."
  python3 -m pip install -r "$req_file" --quiet 2>/dev/null \
    || pip3 install -r "$req_file" --quiet 2>/dev/null \
    && ok "Python dependencies installed" && RESULTS[pip_deps]=0 \
    || { fail "pip install failed — try: pip3 install -r $req_file"; RESULTS[pip_deps]=1; }
}

setup_claude_token() {
  section "Claude Setup Token (Optional)"
  if ! has_cmd claude; then
    skip "Claude CLI not found — skipping token setup"
    RESULTS[claude_token]=2
    return
  fi

  info "This links your Claude subscription to dashboard chat."
  read -r -p "$(echo -e ${YELLOW}→ Set up Claude token now? (y/n): ${NC})" response
  if [[ "$response" != "y" && "$response" != "yes" ]]; then
    skip "Skipped — add token later in Dashboard Settings"
    RESULTS[claude_token]=2
    return
  fi

  info "Running: claude setup-token (browser may open)..."
  local raw token
  raw="$(claude setup-token 2>/dev/null || true)"
  token="$(printf '%s\n' "$raw" | grep -Eo 'eyJ[A-Za-z0-9._-]+' | tail -n 1)"

  if [ -z "$token" ]; then
    read -r -p "$(echo -e ${YELLOW}→ Paste token manually (or leave blank to skip): ${NC})" token
  fi

  if [ -z "$token" ]; then
    skip "Token not captured — you can configure later"
    RESULTS[claude_token]=2
    return
  fi

  export CLAUDE_SETUP_TOKEN="$token"
  if [ -f ".env" ]; then
    upsert_env_line "CLAUDE_SETUP_TOKEN" "$token" ".env" \
      && ok "Claude setup token saved to .env" && RESULTS[claude_token]=0 \
      || { fail "Failed to write token to .env"; RESULTS[claude_token]=1; }
  else
    ok "Claude setup token captured for setup wizard"
    RESULTS[claude_token]=0
  fi
}

launch_setup() {
  section "Launching setup wizard"
  [ ! -f "setup.py" ] && { fail "setup.py not found"; return; }
  has_cmd python3 || { fail "Python not available. Install Python 3.8+ then run: python3 setup.py"; return; }
  ok "Starting interactive setup..."; echo ""
  python3 setup.py
}

print_summary() {
  printf "\n${CYAN}${BOLD}╔══════════════════════════════════════════════════════╗\n"
  printf "║                 Installation Summary                 ║\n"
  printf "╚══════════════════════════════════════════════════════╝${NC}\n\n"
  local all_good=true
  for tool in homebrew python git node claude_code railway repo pip_deps claude_token; do
    local status="${RESULTS[$tool]:-}" label="$tool"
    [[ "$tool" == "claude_code" ]] && label="Claude Code"
    [[ "$tool" == "claude_token" ]] && label="Claude token"
    [[ "$tool" == "pip_deps" ]] && label="pip deps"
    case "$status" in
      0) echo -e "  ${GREEN}${OK}  ${label} — installed${NC}";;
      1) echo -e "  ${RED}${FAIL}  ${label} — FAILED${NC}"; all_good=false;;
      2) echo -e "  ${YELLOW}${SKIP}  ${label} — already present${NC}";;
      *) echo -e "  ${YELLOW}${SKIP}  ${label} — skipped${NC}";;
    esac
  done
  echo ""
  $all_good && echo -e "  ${GREEN}${BOLD}All clear! Your Agentic OS environment is ready.${NC}" \
            || echo -e "  ${YELLOW}Some steps had issues. Review the errors above.${NC}"
  echo ""
}

verify_install() {
  section "Verifying installation"
  local pass=0 fail_count=0

  if has_cmd python3; then
    local pyver=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
    ok "Python $pyver"; ((pass++))
  else fail "Python not found"; ((fail_count++)); fi

  if python3 -c "import flask, requests, dotenv" 2>/dev/null; then
    ok "Core Python packages"; ((pass++))
  else fail "Missing core packages - run: pip install -r requirements.txt"; ((fail_count++)); fi

  if [ -f ".env" ]; then
    ok ".env file exists"; ((pass++))
  else skip ".env not found - run: cp .env.example .env"; fi

  if has_cmd git; then ok "Git available"; ((pass++)); else fail "Git not found"; ((fail_count++)); fi
  if has_cmd node; then ok "Node.js available"; ((pass++)); else skip "Node.js not found (optional)"; fi

  echo ""
  if [ $fail_count -eq 0 ]; then
    ok "All checks passed ($pass/$pass)"
  else
    fail "$fail_count check(s) failed, $pass passed"
  fi
}

main() {
  banner
  detect_os
  install_homebrew
  install_python
  install_git
  install_node
  install_npm_tool "Claude Code CLI" "claude_code" "claude" "@anthropic-ai/claude-code"
  install_npm_tool "Railway CLI" "railway" "railway" "@railway/cli"
  clone_repo
  install_pip_deps
  setup_claude_token
  print_summary
  verify_install
  launch_setup
}

for arg in "$@"; do
  case "$arg" in
    --full) FULL_INSTALL=true;;
    --verify) verify_install; exit 0;;
  esac
done

main
