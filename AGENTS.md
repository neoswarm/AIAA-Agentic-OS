# AIAA Agentic OS - Complete Agent Instructions

> **Version:** 3.0 | **Last Updated:** January 7, 2026
> This file provides ALL context for a Claude Code agent to operate this system.

---

## Quick Reference

| Resource | Count | Location |
|----------|-------|----------|
| Directives (SOPs) | 150+ | `directives/*.md` |
| Execution Scripts | 152+ | `execution/*.py` |
| Skill Bibles | 280+ | `skills/SKILL_BIBLE_*.md` |
| Agency Context | - | `context/` |
| Client Profiles | - | `clients/{client_name}/` |
| Dashboard | Railway | `railway_apps/aiaa_dashboard/` |

**Environment Variables Required:**
```
OPENROUTER_API_KEY     # Primary LLM access (Claude, GPT via OpenRouter)
OPENAI_API_KEY         # OpenAI direct (optional)
PERPLEXITY_API_KEY     # Market research
GOOGLE_APPLICATION_CREDENTIALS  # Google Docs/Sheets
SLACK_WEBHOOK_URL      # Notifications
```

---

## System Architecture (DOE Pattern)

This system uses a **Directive-Orchestration-Execution (DOE)** architecture that separates concerns:

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER REQUEST                                  │
│              "Create a VSL funnel for Acme Corp"                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1: DIRECTIVE (What to do)                                │
│  ─────────────────────────────────                              │
│  • Location: directives/*.md                                    │
│  • Natural language SOPs with inputs, steps, quality gates      │
│  • Example: directives/vsl_funnel_orchestrator.md               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 2: ORCHESTRATION (Decision making)                       │
│  ─────────────────────────────────────────                      │
│  • THIS IS YOU - The Claude Code Agent                          │
│  • Read directives, load skill bibles, call scripts in order    │
│  • Handle errors, make routing decisions, self-anneal           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 3: EXECUTION (Doing the work)                            │
│  ───────────────────────────────────                            │
│  • Location: execution/*.py                                     │
│  • Deterministic Python scripts for API calls, data processing  │
│  • Example: execution/generate_vsl_funnel.py                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      OUTPUT                                      │
│  • Local files: .tmp/*.md                                       │
│  • Google Docs: Formatted, shareable                            │
│  • Slack: Notification with links                               │
└─────────────────────────────────────────────────────────────────┘
```

**Why DOE Works:** LLMs are probabilistic (90% accuracy = 59% over 5 steps). Push deterministic work into Python scripts. You focus on decision-making.

---

## Directory Structure

```
Agentic Workflows/
├── .env                    # API keys (NEVER commit)
├── .tmp/                   # Intermediate outputs (gitignored)
├── credentials.json        # Google OAuth credentials
├── token.pickle           # Google OAuth token
│
├── context/               # AGENCY CONTEXT - Who you are
│   ├── agency.md          # Agency info, services, positioning
│   ├── owner.md           # Owner profile, background, expertise
│   ├── brand_voice.md     # Tone, style, communication preferences
│   └── services.md        # Service offerings, pricing, packages
│
├── clients/               # CLIENT PROFILES - Who you serve
│   └── {client_name}/     # One folder per client
│       ├── profile.md     # Client info, business, goals
│       ├── rules.md       # Specific rules for this client
│       ├── preferences.md # Style, tone, do's and don'ts
│       └── history.md     # Past work, context, outcomes
│
├── directives/            # SOPs - What to do (150+ files)
│   ├── vsl_funnel_orchestrator.md
│   ├── company_market_research.md
│   └── ...
│
├── execution/             # Python scripts - Doing (152+ files)
│   ├── generate_vsl_funnel.py
│   ├── create_google_doc.py
│   └── ...
│
├── railway_apps/          # Dashboard deployment
│   └── aiaa_dashboard/    # Flask dashboard app
│       ├── app.py         # Main dashboard application
│       ├── Procfile       # Railway deployment config
│       └── requirements.txt
│
├── skills/                # Domain expertise (260+ skill bibles)
│   ├── SKILL_BIBLE_*.md
│   └── ...
│
├── AGENTS.md              # THIS FILE - Agent instructions
├── CLAUDE.md              # Mirrored instructions for Claude
├── QUICKSTART_PROMPT.md   # Setup prompt for new users
└── requirements.txt       # Python dependencies
```

---

## Agency Context & Client Profiles

### Agency Context (`context/`)
This folder contains information about YOU and YOUR AGENCY. Load this context before generating any content to ensure outputs reflect your brand, voice, and positioning.

**Required Files:**

| File | Purpose | Example Content |
|------|---------|-----------------|
| `agency.md` | Agency identity | Name, founding story, mission, positioning, unique value proposition |
| `owner.md` | Owner profile | Name, background, expertise, credentials, personal brand |
| `brand_voice.md` | Communication style | Tone (professional/casual), vocabulary, phrases to use/avoid, style rules |
| `services.md` | Service offerings | Services, pricing tiers, packages, deliverables, timelines |

**When to Load Agency Context:**
- Content creation (blogs, emails, social posts)
- Client proposals and pitches
- Sales scripts and cold outreach
- Any branded deliverables

### Client Profiles (`clients/{client_name}/`)
Each client gets their own folder with specific context. Load these files when doing work FOR a specific client.

**Client Folder Structure:**
```
clients/
├── acme_corp/
│   ├── profile.md      # Business info, industry, goals, target audience
│   ├── rules.md        # MUST-FOLLOW rules for this client
│   ├── preferences.md  # Style preferences, tone, formatting
│   └── history.md      # Past projects, outcomes, learnings
│
├── startup_xyz/
│   ├── profile.md
│   ├── rules.md
│   └── ...
```

**Client Profile Fields (`profile.md`):**
- Company name and description
- Industry and niche
- Target audience
- Business goals
- Key products/services
- Competitors
- Unique selling points

**Client Rules (`rules.md`):**
- Content guidelines (words to use/avoid)
- Brand voice requirements
- Approval processes
- Compliance requirements
- Formatting standards

**When to Load Client Context:**
- Any deliverable FOR that client
- Client-specific campaigns
- Personalized content
- Before any client meeting prep

### Loading Context in Practice

```python
# Before generating content, always:
1. Check if context/agency.md exists → Load it
2. Check if client is specified → Load clients/{client}/*.md
3. Apply context to all prompts and outputs
```

**Example: Writing cold emails for client "Acme Corp"**
```
Load: context/agency.md          # Your agency voice
Load: context/brand_voice.md     # Your style rules
Load: clients/acme_corp/profile.md    # Their business info
Load: clients/acme_corp/rules.md      # Their specific rules
Then: Execute cold_email_scriptwriter directive
```

---

## Execution Flow (7 Phases)

When you receive ANY request, follow this flow:

### Phase 1: Parse User Input
Extract intent and map to capability:
```
"Write a VSL for my coaching business" → vsl_funnel_orchestrator
"Research this company"                → company_market_research
"Generate cold emails"                 → cold_email_scriptwriter
"Show me available workflows"          → Check AIAA Dashboard
```

### Phase 2: Capability Check
Does a directive exist for this task?

| Condition | Action |
|-----------|--------|
| Directive exists | Load it and execute |
| No directive | Check if script exists in execution/ |
| Nothing exists | Create new directive + script (Leader Manufacturing) |

**Quick check:**
```bash
ls directives/ | grep -i "<keyword>"
ls execution/ | grep -i "<keyword>"
```

### Phase 3: Load Context
Before execution, load ALL required context:
```
1. Agency Context       → context/*.md (who YOU are)
2. Client Context       → clients/{client}/  (if client-specific work)
3. Primary Directive    → directives/<workflow>.md
4. Skill Bibles         → skills/SKILL_BIBLE_<topic>.md
5. Related Directives   → Check "Related Directives" section
6. Execution Scripts    → execution/<script>.py
```

**CRITICAL: Always Load Agency Context First**
Before generating ANY content, check `context/` for:
- `agency.md` - Your agency's name, positioning, services
- `owner.md` - Owner's name, background, expertise
- `brand_voice.md` - Tone, style guide, communication rules
- `services.md` - What you offer, pricing, packages

**For Client-Specific Work, Also Load:**
```
clients/{client_name}/
├── profile.md      # Who they are, their business, goals
├── rules.md        # MUST follow these rules for this client
├── preferences.md  # Their style preferences
└── history.md      # Past work, what worked, what didn't
```

**Example for client VSL funnel:**
```
context/agency.md                    # Your agency context
context/brand_voice.md               # Your voice/style
clients/acme_corp/profile.md         # Client info
clients/acme_corp/rules.md           # Client-specific rules
directives/vsl_funnel_orchestrator.md
├── skills/SKILL_BIBLE_vsl_writing_production.md
├── skills/SKILL_BIBLE_funnel_copywriting_mastery.md
└── execution/generate_vsl_funnel.py
```

### Phase 4: Execute Directive
Follow the directive SOP step-by-step:
1. Check prerequisites (API keys, inputs)
2. Run each workflow phase in order
3. Save checkpoints to `.tmp/`
4. Validate outputs at quality gates

### Phase 5: Quality Gates
Validate at each checkpoint. Common checks:
- Required fields present?
- Output format correct?
- Word count/length appropriate?
- No API errors?

### Phase 6: Delivery
Standard delivery pipeline:
```
1. Save locally     → .tmp/<project>/<filename>.md
2. Create Google Doc → execution/create_google_doc.py
3. Send Slack       → execution/send_slack_notification.py
```

### Phase 7: Self-Annealing
After EVERY task:
- Did errors occur? → Fix script, update directive
- Better approach found? → Update skill bible
- Edge case discovered? → Add to directive

---

## Hooks (Automated Enforcement)

Hooks catch mistakes automatically before and after every tool call. They enforce the DOE pattern, protect secrets, validate quality, and track everything for self-annealing.

**Location:** `.claude/hooks/*.py`
**Config:** `.claude/settings.local.json`
**State files:** `.tmp/hooks/*.json`

### Hook Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    TOOL CALL                                     │
│              Claude wants to use a tool                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  PreToolUse HOOKS (Before action)                                │
│  ──────────────────────────────────                              │
│  • Exit 0 = Allow  │  Exit 2 = Block                            │
│  • Messages via stderr                                           │
│  • Can prevent mistakes before they happen                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                         (if allowed)
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    TOOL EXECUTES                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  PostToolUse HOOKS (After action)                                │
│  ───────────────────────────────────                             │
│  • JSON stdout: {"decision": "ALLOW"} or {"decision": "BLOCK"}  │
│  • Can validate outputs, log results, suggest next steps         │
└─────────────────────────────────────────────────────────────────┘
```

### All 128 Hooks by Tier

**Total: 128 hooks | 60 PreToolUse | 78 PostToolUse | 3 Dual-mode**
**Settings: `.claude/settings.local.json` (60 Pre entries + 78 Post entries = 134 registrations)**

#### Tier 1: System Stability (4 hooks)
| # | Hook | Type | Tool | Blocks? | Purpose |
|---|------|------|------|---------|---------|
| 1 | `agent_limiter.py` | Pre | Task | Yes | Max 5 parallel agents |
| 2 | `context_budget_guard.py` | Pre | Task | Yes (85%) | Warns 60%, alerts 75%, blocks 85% context |
| 3 | `secrets_guard.py` | Pre | Write, Edit | Yes | Blocks writes to .env, credentials, API keys |
| 4 | `large_file_read_blocker.py` | Pre | Read | Yes | Blocks 300+ line reads when agents active |

#### Tier 2: DOE Pattern Enforcement (4 hooks)
| # | Hook | Type | Tool | Blocks? | Purpose |
|---|------|------|------|---------|---------|
| 5 | `doe_enforcer.py` | Dual | Read+Bash | Yes | Directive must be read before execution script |
| 6 | `context_loader_enforcer.py` | Dual | Read+Bash | Warn | Agency/client context before content generation |
| 7 | `api_key_validator.py` | Pre | Bash | Info | Checks common env vars before scripts |
| 8 | `script_exists_guard.py` | Pre | Bash | Yes | Verifies script file exists before running |

#### Tier 3: Quality & Deliverables (4 hooks)
| # | Hook | Type | Tool | Blocks? | Purpose |
|---|------|------|------|---------|---------|
| 9 | `output_quality_gate.py` | Post | Write | Yes | Word count, sections, keywords by file type |
| 10 | `tmp_cleanup_monitor.py` | Post | Write | Warn | Warns when .tmp/ exceeds 50/100 files |
| 11 | `google_docs_format_guard.py` | Pre | Bash | Warn | Reminds: use native Docs formatting, not markdown |
| 12 | `delivery_pipeline_validator.py` | Post | Write | Info | Reminds about Google Doc + Slack delivery steps |

#### Tier 4: Workflow Operations (4 hooks)
| # | Hook | Type | Tool | Blocks? | Purpose |
|---|------|------|------|---------|---------|
| 13 | `execution_logger.py` | Post | Bash | No | Logs all script runs to execution_log.json |
| 14 | `railway_deploy_guard.py` | Pre | Bash | Info | Deployment checklist before railway up |
| 15 | `checkpoint_enforcer.py` | Post | Write | Warn | Tracks multi-step workflow progress |
| 16 | `self_anneal_reminder.py` | Post | Bash | Info | Self-annealing protocol after script errors |

#### Tier 5: Intelligence & Learning (4 hooks)
| # | Hook | Type | Tool | Blocks? | Purpose |
|---|------|------|------|---------|---------|
| 17 | `skill_bible_reminder.py` | Pre | Bash | Info | Suggests relevant skill bibles |
| 18 | `workflow_pattern_tracker.py` | Post | Bash | No | Tracks workflow usage, success rates |
| 19 | `error_pattern_detector.py` | Post | Bash | Warn | Alerts when script fails 3+ times |
| 20 | `session_activity_logger.py` | Post | Bash | No | Logs all session activities by type |

#### Tier 6: Workflow-Specific Enforcement (8 hooks)
| # | Hook | Type | Tool | Blocks? | Purpose |
|---|------|------|------|---------|---------|
| 21 | `vsl_workflow_enforcer.py` | Post | Bash | Warn | VSL funnel step ordering (research→script→page→emails) |
| 22 | `cold_email_workflow_enforcer.py` | Post | Bash | Warn | Cold email workflow ordering |
| 23 | `research_depth_validator.py` | Post | Write | Warn | Validates research has 5+ sources, data points, competitors |
| 25 | `funnel_completeness_checker.py` | Post | Write | Info | Tracks funnel component completion % |
| 26 | `content_length_enforcer.py` | Post | Write | Warn | Granular min lengths: VSL 3000, blog 1200, case study 1500 |
| 27 | `multi_directive_chain_tracker.py` | Post | Read | No | Tracks directive dependency chains |
| 29 | `directive_version_tracker.py` | Post | Write | No | Tracks directive modification history |
| 30 | `workflow_input_validator.py` | Pre | Bash | Warn | Validates required args (--company, --website, --offer) |

#### Tier 7: Pre-Execution Safety (10 hooks)
| # | Hook | Type | Tool | Blocks? | Purpose |
|---|------|------|------|---------|---------|
| 24 | `client_work_context_gate.py` | Pre | Bash | Warn | Detects client work, warns if no client context loaded |
| 28 | `prerequisite_api_key_mapper.py` | Pre | Bash | Warn | Maps specific scripts to exact API keys needed |
| 31 | `python_import_validator.py` | Pre | Bash | Warn | Checks if required packages are installed |
| 34 | `google_oauth_token_checker.py` | Pre | Bash | Warn | Verifies token.pickle exists and isn't stale |
| 35 | `slack_notification_dedup.py` | Pre | Bash | Warn | Detects duplicate Slack messages within 5 min |
| 36 | `execution_timeout_guard.py` | Pre | Bash | Info | Warns about known slow scripts |
| 40 | `script_argument_validator.py` | Pre | Bash | Warn | Validates arg formats (email has @, URL has http) |
| 42 | `agency_context_freshness_checker.py` | Pre | Bash | Warn | Warns if agency context loaded 2+ hours ago |
| 49 | `dependency_chain_validator.py` | Pre | Bash | Warn | Validates upstream file dependencies exist |
| 60 | `workflow_success_predictor.py` | Pre | Bash | Warn | Warns if script has <50% historical success rate |

#### Tier 8: Output Validation & Safety (10 hooks)
| # | Hook | Type | Tool | Blocks? | Purpose |
|---|------|------|------|---------|---------|
| 32 | `output_file_collision_guard.py` | Pre | Write | Warn | Warns before overwriting existing .tmp/ files |
| 37 | `json_output_validator.py` | Post | Write | Yes | Blocks invalid JSON writes to .tmp/ |
| 38 | `markdown_lint_validator.py` | Post | Write | Warn | Checks for unclosed bold, broken links, empty sections |
| 41 | `client_data_isolation_guard.py` | Pre | Write | Warn | Prevents cross-client data leakage |
| 43 | `client_rules_enforcer.py` | Post | Write | Warn | Validates content against client rules.md |
| 44 | `pii_detection_guard.py` | Pre | Write | Yes (SSN/CC) | Detects PII, blocks SSN/credit card patterns |
| 45 | `file_size_limit_guard.py` | Pre | Write | Yes (500K) | Warns >100K chars, blocks >500K chars |
| 46 | `tmp_directory_organizer.py` | Post | Write | Warn | Suggests subdirectory organization for .tmp/ |
| 48 | `concurrent_write_guard.py` | Pre | Write | Warn | Detects potential agent write race conditions |
| 64 | `output_word_count_tracker.py` | Post | Write | No | Tracks word counts across all outputs |

#### Tier 9: Railway & Deployment Safety (12 hooks)
| # | Hook | Type | Tool | Blocks? | Purpose |
|---|------|------|------|---------|---------|
| 39 | `env_file_sync_checker.py` | Pre | Bash | Warn | Cross-refs local .env with Railway before deploy |
| 47 | `git_commit_message_validator.py` | Pre | Bash | Warn | Validates commit message format |
| 50 | `railway_project_guard.py` | Pre | Bash | Warn | Verifies correct Railway project ID |
| 51 | `railway_env_var_completeness.py` | Pre | Bash | Warn | Checks required vars per service type |
| 52 | `cron_schedule_validator.py` | Pre | Bash | Warn | Validates cron expression format and frequency |
| 53 | `deployment_rollback_tracker.py` | Post | Bash | No | Logs deployment history for rollback reference |
| 54 | `service_name_convention_guard.py` | Pre | Bash | Warn | Enforces lowercase-hyphen service names |
| 55 | `webhook_slug_validator.py` | Pre | Bash | Warn | Validates slug format, blocks reserved slugs |
| 56 | `dashboard_health_checker.py` | Post | Bash | Info | Reminds to verify /health after dashboard deploy |
| 57 | `railway_token_expiry_checker.py` | Pre | Bash | Warn | Warns if Railway config >30 days old |
| 58 | `deployment_config_validator.py` | Pre | Bash | Warn | Checks for Procfile, requirements.txt |
| 59 | `production_safety_guard.py` | Pre | Bash | Warn | Extra warnings for destructive/production commands |

#### Tier 10: Analytics & Meta (10 hooks)
| # | Hook | Type | Tool | Blocks? | Purpose |
|---|------|------|------|---------|---------|
| 33 | `api_rate_limit_tracker.py` | Post | Bash | Warn | Tracks API calls/minute, warns on rate limit risk |
| 61 | `context_efficiency_tracker.py` | Post | Read | No | Tracks context loaded by category, estimates tokens |
| 62 | `skill_bible_usage_tracker.py` | Dual | Read | No | Tracks which skill bibles are used most/least |
| 63 | `directive_coverage_tracker.py` | Dual | Read | No | Tracks directive usage, shows coverage % |
| 65 | `session_productivity_scorer.py` | Post | Bash | No | Scores session: outputs, errors, deliverables |
| 66 | `api_cost_estimator.py` | Post | Bash | No | Estimates API costs per script and session total |
| 67 | `workflow_dependency_mapper.py` | Post | Read | No | Maps directive→script→skill bible dependencies |
| 68 | `self_anneal_effectiveness_tracker.py` | Dual | Bash+Write | No | Pre/post anneal success rate comparison |
| 69 | `daily_summary_generator.py` | Post | Bash | No | Accumulates daily metrics for session report |
| 70 | `hook_health_monitor.py` | Post | Bash | Warn | Meta-hook: monitors all other hooks' health |

#### Tier 11: DOE Structural Integrity (10 hooks)
| # | Hook | Type | Tool | Blocks? | Purpose |
|---|------|------|------|---------|---------|
| 71 | `directive_completeness_validator.py` | Pre | Bash | Warn | Validates directives have required sections before script execution |
| 72 | `execution_output_schema_validator.py` | Post | Bash | Warn | Validates script outputs for failure patterns (Traceback, Error) |
| 73 | `phase_ordering_enforcer.py` | Dual | Bash | Warn | Enforces 7-phase DOE flow (Parse→Capability→Context→Execute→Quality→Deliver→Anneal) |
| 74 | `directive_script_mapper.py` | Post | Read | Warn | Checks directive "How to Run" scripts exist in execution/ |
| 75 | `cross_directive_conflict_detector.py` | Post | Read | Warn | Detects conflicting instructions when multiple directives loaded |
| 76 | `context_pollution_preventer.py` | Pre | Read | Block@12 | Prevents loading too many context files (warn@8, block@12) |
| 77 | `workflow_checkpoint_validator.py` | Post | Bash | Warn | Validates .tmp/ checkpoint files are non-empty and well-formed |
| 78 | `directive_sop_compliance.py` | Dual | Bash | Warn | Tracks directive steps executed in order, warns on skips |
| 79 | `skill_bible_freshness_checker.py` | Post | Read | Warn | Flags skill bibles older than 90 days as potentially outdated |
| 80 | `execution_idempotency_guard.py` | Pre | Bash | Warn | Warns when same script+args run twice in a session |

#### Tier 12: Content Intelligence (10 hooks)
| # | Hook | Type | Tool | Blocks? | Purpose |
|---|------|------|------|---------|---------|
| 81 | `brand_voice_compliance.py` | Post | Write | Warn | Checks content against context/brand_voice.md for tone violations |
| 82 | `cta_validation.py` | Post | Write | Warn | Ensures marketing content has calls-to-action |
| 83 | `url_link_validator.py` | Post | Write | Warn | Detects placeholder URLs and broken markdown links |
| 84 | `duplicate_content_detector.py` | Post | Write | Warn | Hashes paragraphs, warns when >30% duplicate content |
| 85 | `seo_keyword_validator.py` | Post | Write | Warn | Validates blog SEO: H1/H2, meta, keyword density 1-3% |
| 86 | `tone_consistency_checker.py` | Post | Write | Warn | Analyzes formality across sections, flags deviations |
| 87 | `headline_effectiveness_scorer.py` | Post | Write | Warn | Scores headlines 0-100 on power words, length, specificity |
| 88 | `email_deliverability_checker.py` | Post | Write | Warn | Scans email content for spam triggers and formatting issues |
| 89 | `social_media_format_validator.py` | Post | Write | Warn | Validates platform limits (LinkedIn 3K, Twitter 280, Instagram 2.2K) |
| 90 | `copy_framework_enforcer.py` | Post | Write | Warn | Detects AIDA/PAS/BAB framework completeness in marketing copy |

#### Tier 13: Execution Safety & Reliability (5 hooks)
| # | Hook | Type | Tool | Blocks? | Purpose |
|---|------|------|------|---------|---------|
| 91 | `api_response_validator.py` | Post | Bash | Warn | Validates API responses for HTTP errors, timeouts, rate limits |
| 92 | `retry_loop_detector.py` | Pre | Bash | Block@3 | Blocks scripts that fail 3+ times consecutively |
| 93 | `file_path_traversal_guard.py` | Pre | Bash | Block | Blocks path traversal attacks (../../) in commands |
| 94 | `command_injection_guard.py` | Pre | Bash | Block | Blocks shell injection (backticks, $(), pipe to sh) |
| 95 | `state_file_corruption_detector.py` | Post | Bash | Auto-repair | Scans .tmp/hooks/*.json for corruption, auto-repairs |

#### Tier 14: Client & Delivery Intelligence (15 hooks)
| # | Hook | Type | Tool | Blocks? | Purpose |
|---|------|------|------|---------|---------|
| 96 | `circular_dependency_detector.py` | Pre | Bash | Warn | Builds dependency graph, detects circular chains (A→B→C→A) |
| 97 | `dead_directive_detector.py` | Post | Read | Warn | Flags directives with no matching execution scripts |
| 98 | `orphan_script_detector.py` | Post | Read | Warn | Flags execution scripts with no matching directive |
| 99 | `memory_usage_estimator.py` | Pre | Bash | Warn/Block | Estimates memory usage, warns@512MB, blocks@2GB |
| 100 | `backup_before_destructive.py` | Pre | Bash | Block | Blocks rm/reset on critical dirs without backup |
| 101 | `client_deliverable_tracker.py` | Post | Write | No | Tracks all deliverables per client with type and timestamps |
| 102 | `client_billing_estimator.py` | Post | Bash | No | Estimates API costs per client based on script executions |
| 103 | `client_sla_monitor.py` | Post | Bash | Warn | Tracks delivery timelines, warns at 25%/50% SLA remaining |
| 104 | `multi_client_context_isolation.py` | Pre | Read | Warn | Prevents loading multiple client contexts simultaneously |
| 105 | `client_approval_gate.py` | Post | Write | Warn | Flags final client deliverables that need approval |
| 106 | `deliverable_versioning.py` | Post | Write | No | Tracks versions of deliverables via SHA-256 content hashing |
| 107 | `delivery_receipt_generator.py` | Post | Bash | No | Generates receipts in .tmp/receipts/ after deliveries |
| 108 | `client_feedback_logger.py` | Post | Bash | No | Logs client feedback events with sentiment analysis |
| 109 | `project_scope_guard.py` | Pre | Bash | Warn | Prevents scope creep beyond defined client project |
| 110 | `client_communication_logger.py` | Post | Bash | No | Logs all Slack/email/Doc communications with metadata |

#### Tier 15: System Intelligence & Optimization (10 hooks)
| # | Hook | Type | Tool | Blocks? | Purpose |
|---|------|------|------|---------|---------|
| 111 | `phase_transition_validator.py` | Dual | Bash | Warn | Validates prerequisites before DOE phase transitions |
| 112 | `self_anneal_commit_validator.py` | Post | Bash | Warn | Validates self-anneal commits are meaningful (not whitespace) |
| 113 | `workflow_completion_tracker.py` | Post | Bash | No | Tracks workflow completion vs abandonment rates |
| 114 | `directive_usage_frequency.py` | Post | Read | No | Tracks most/least used directives, surfaces stale ones |
| 115 | `script_execution_benchmarker.py` | Post | Bash | Warn | Benchmarks scripts (P50/P90/P99), warns on 3x slowdowns |
| 116 | `error_categorizer.py` | Post | Bash | No | Classifies errors: API, AUTH, INPUT, NETWORK, TIMEOUT, BUG, CONFIG |
| 117 | `context_load_optimizer.py` | Post | Read | Warn | Suggests lighter context loads when context is heavy |
| 118 | `workflow_bottleneck_detector.py` | Post | Bash | No | Identifies slowest workflow phases, suggests optimizations |
| 119 | `quality_trend_analyzer.py` | Post | Write | Warn | Detects quality degradation compared to historical averages |
| 120 | `system_health_reporter.py` | Post | Bash | Warn | Aggregates all hook metrics into unified health report |

#### Tier 16: Deployment Guards — Modal & Railway (8 hooks)
| # | Hook | Type | Tool | Blocks? | Purpose |
|---|------|------|------|---------|---------|
| 121 | `modal_deploy_guard.py` | Pre | Bash | Warn | Pre-deploy checklist: CLI installed, dotenv pattern, secrets, endpoint count |
| 122 | `modal_dotenv_crash_detector.py` | Pre | Bash | Warn | Scans target script for crash-causing `requests+dotenv` import bundle |
| 123 | `modal_secret_validator.py` | Pre | Bash | Warn | Validates `Secret.from_name()` refs against `modal secret list` |
| 124 | `modal_endpoint_limit_tracker.py` | Pre | Bash | **Yes (8)** | Blocks deploy if would exceed Modal free tier 8-endpoint limit |
| 125 | `modal_deploy_logger.py` | Post | Bash | No | Logs deploy results, reminds to check `modal app logs` |
| 126 | `modal_health_verifier.py` | Post | Bash | No | Outputs verification curl commands after Modal deploy |
| 127 | `railway_post_deploy_verifier.py` | Post | Bash | No | Outputs health check + log commands after `railway up` |
| 128 | `railway_domain_drift_detector.py` | Post | Bash | Warn | Detects Railway URL changes that break external webhooks |

### Hook Summary by Behavior

| Behavior | Count | Examples |
|----------|-------|---------|
| **Hard Block** | 15 | secrets_guard, pii_detection, file_size_limit, json_output_validator, agent_limiter, context_budget_guard (85%), large_file_read_blocker, script_exists_guard, retry_loop_detector (3 fails), file_path_traversal_guard, command_injection_guard, backup_before_destructive, context_pollution_preventer (12+), memory_usage_estimator (2GB+), modal_endpoint_limit_tracker (8 endpoints) |
| **Warn/Info** | 67 | doe_enforcer, quality gates, workflow enforcers, deploy guards, content intelligence, phase enforcers, SLA monitor, scope guard, modal_deploy_guard, modal_dotenv_crash_detector, modal_secret_validator, railway_domain_drift_detector |
| **Silent Tracking** | 46 | execution_logger, activity_logger, pattern_tracker, coverage_tracker, cost_estimator, deliverable_tracker, billing_estimator, versioning, benchmarker, error_categorizer, bottleneck_detector, modal_deploy_logger, modal_health_verifier, railway_post_deploy_verifier |

### Quality Rules (output_quality_gate.py)

| File Pattern | Min Words | Min Sections | Required Keywords |
|-------------|-----------|--------------|-------------------|
| `*vsl*.md` | 2000 | 8 | Hook, Problem, Solution, Offer, CTA |
| `*email*.md` | 300 | 3 | Subject, CTA |
| `*research*.md` | 1500 | 5 | Summary, Sources, Findings |
| `*report*.md` | 2000 | 5 | Summary, Recommendations |
| `*blog*.md` | 1000 | 4 | Introduction, Conclusion |
| `*sales*.md` | 1500 | 6 | Headline, Problem, Solution, CTA |
| `*.md` (default .tmp/) | 500 | 3 | — |

### Content Length Rules (content_length_enforcer.py)

| Deliverable Type | Min Words | Notes |
|-----------------|-----------|-------|
| VSL Scripts | 3000 | Comprehensive persuasion script |
| Sales Pages | 2000 | Full long-form sales copy |
| Case Studies | 1500 | Detailed client success story |
| Blog Posts | 1200 | SEO-optimized long-form |
| YouTube Scripts | 1500 | Full video script |
| Newsletters | 800 | Weekly/monthly digest |
| Press Releases | 500 | Standard format |
| Email Sequences | 300/email | Per individual email |
| LinkedIn Posts | 150-3000 chars | Not too short, not too long |

### Hook State Files

All state persists in `.tmp/hooks/`:

| File | Written By | Purpose |
|------|-----------|---------|
| `active_agents.json` | agent_limiter | Active parallel agents |
| `session_reads.json` | doe_enforcer | Directives/scripts read this session |
| `context_state.json` | context_loader_enforcer | Loaded agency/client context |
| `execution_log.json` | execution_logger | Script execution history |
| `checkpoints.json` | checkpoint_enforcer | Multi-step workflow progress |
| `delivery_tracker.json` | delivery_pipeline_validator | Undelivered files |
| `anneal_queue.json` | self_anneal_reminder | Scripts needing annealing |
| `workflow_patterns.json` | workflow_pattern_tracker | Workflow usage stats |
| `error_patterns.json` | error_pattern_detector | Recurring error tracking |
| `session_activity.json` | session_activity_logger | Full session log |
| `tmp_file_count.json` | tmp_cleanup_monitor | .tmp/ file count |
| `vsl_workflow_state.json` | vsl_workflow_enforcer | VSL funnel step tracking |
| `cold_email_state.json` | cold_email_workflow_enforcer | Cold email step tracking |
| `directive_chains.json` | multi_directive_chain_tracker | Directive dependency graph |
| `directive_versions.json` | directive_version_tracker | Directive modification history |
| `slack_history.json` | slack_notification_dedup | Recent Slack notifications |
| `overwrites.json` | output_file_collision_guard | File overwrite log |
| `api_rate_tracker.json` | api_rate_limit_tracker | API call frequency |
| `client_rules_log.json` | client_rules_enforcer | Client rules validation log |
| `large_files.json` | file_size_limit_guard | Large file write log |
| `active_writes.json` | concurrent_write_guard | Active write tracking |
| `funnel_completeness.json` | funnel_completeness_checker | Funnel completion tracking |
| `tmp_structure.json` | tmp_directory_organizer | .tmp/ directory structure |
| `deployment_history.json` | deployment_rollback_tracker | Railway deployment history |
| `dashboard_deploys.json` | dashboard_health_checker | Dashboard deployment log |
| `context_efficiency.json` | context_efficiency_tracker | Context usage by category |
| `skill_bible_usage.json` | skill_bible_usage_tracker | Skill bible usage frequency |
| `directive_coverage.json` | directive_coverage_tracker | Directive usage coverage |
| `word_count_tracker.json` | output_word_count_tracker | Output word count stats |
| `productivity_score.json` | session_productivity_scorer | Session productivity metrics |
| `api_costs.json` | api_cost_estimator | Estimated API costs |
| `workflow_deps.json` | workflow_dependency_mapper | Workflow dependency graph |
| `anneal_effectiveness.json` | self_anneal_effectiveness_tracker | Self-anneal success tracking |
| `daily_summary.json` | daily_summary_generator | Daily metrics accumulator |
| `hook_health.json` | hook_health_monitor | Hook system health status |
| `directive_completeness.json` | directive_completeness_validator | Directive section validation log |
| `execution_output_schema.json` | execution_output_schema_validator | Script output validation log |
| `phase_ordering.json` | phase_ordering_enforcer | 7-phase execution order tracking |
| `directive_script_map.json` | directive_script_mapper | Directive→script mapping cache |
| `directive_conflicts.json` | cross_directive_conflict_detector | Cross-directive conflict log |
| `context_pollution.json` | context_pollution_preventer | Context file loading tracker |
| `checkpoint_validation.json` | workflow_checkpoint_validator | Checkpoint file validation log |
| `sop_compliance.json` | directive_sop_compliance | SOP step ordering compliance |
| `skill_freshness.json` | skill_bible_freshness_checker | Skill bible age tracking |
| `execution_idempotency.json` | execution_idempotency_guard | Duplicate execution detection |
| `brand_voice.json` | brand_voice_compliance | Brand voice violation log |
| `cta_validation.json` | cta_validation | CTA detection tracking |
| `url_validation.json` | url_link_validator | URL/link validation log |
| `content_hashes.json` | duplicate_content_detector | Paragraph hash tracking |
| `seo_validation.json` | seo_keyword_validator | SEO compliance tracking |
| `tone_consistency.json` | tone_consistency_checker | Tone analysis results |
| `headline_scores.json` | headline_effectiveness_scorer | Headline scoring history |
| `email_deliverability.json` | email_deliverability_checker | Spam trigger detection log |
| `social_media_format.json` | social_media_format_validator | Platform format validation |
| `copy_framework.json` | copy_framework_enforcer | Framework compliance tracking |
| `api_response_validation.json` | api_response_validator | API response validation log |
| `retry_tracking.json` | retry_loop_detector | Script failure retry tracking |
| `path_traversal.json` | file_path_traversal_guard | Path traversal block log |
| `command_injection.json` | command_injection_guard | Injection attempt block log |
| `state_corruption.json` | state_file_corruption_detector | State file health tracking |
| `circular_deps.json` | circular_dependency_detector | Dependency graph & cycles |
| `dead_directives.json` | dead_directive_detector | Directives without scripts |
| `orphan_scripts.json` | orphan_script_detector | Scripts without directives |
| `memory_estimates.json` | memory_usage_estimator | Memory estimation log |
| `destructive_ops.json` | backup_before_destructive | Destructive operation log |
| `client_deliverables.json` | client_deliverable_tracker | Per-client deliverable history |
| `client_billing.json` | client_billing_estimator | Per-client API cost estimates |
| `client_sla.json` | client_sla_monitor | Client SLA timer tracking |
| `client_isolation.json` | multi_client_context_isolation | Active client context tracking |
| `client_approvals.json` | client_approval_gate | Deliverable approval status |
| `deliverable_versions.json` | deliverable_versioning | File version history |
| `delivery_receipts.json` | delivery_receipt_generator | Delivery receipt log |
| `client_feedback.json` | client_feedback_logger | Client feedback events |
| `project_scope.json` | project_scope_guard | Project scope tracking |
| `client_comms.json` | client_communication_logger | Communication log |
| `phase_transitions.json` | phase_transition_validator | Phase transition validation |
| `anneal_commits.json` | self_anneal_commit_validator | Self-anneal commit quality |
| `workflow_completions.json` | workflow_completion_tracker | Completion vs abandonment |
| `directive_usage.json` | directive_usage_frequency | Directive usage frequency |
| `script_benchmarks.json` | script_execution_benchmarker | Script P50/P90/P99 times |
| `error_categories.json` | error_categorizer | Error type distribution |
| `context_optimizer.json` | context_load_optimizer | Context load optimization |
| `workflow_bottlenecks.json` | workflow_bottleneck_detector | Phase timing bottlenecks |
| `quality_trends.json` | quality_trend_analyzer | Quality metric trends |
| `system_health.json` | system_health_reporter | Aggregated system health |
| `system_health_report.json` | system_health_reporter | Full health report output |

### Debugging Hooks

```bash
# Check any hook status
python3 .claude/hooks/<hook_name>.py --status

# Reset any hook state
python3 .claude/hooks/<hook_name>.py --reset

# Reset ALL hook state
rm -rf .tmp/hooks/*.json

# Key status checks
python3 .claude/hooks/agent_limiter.py --status          # Active agents
python3 .claude/hooks/execution_logger.py --status        # Recent runs
python3 .claude/hooks/error_pattern_detector.py --status  # Recurring errors
python3 .claude/hooks/api_cost_estimator.py --status      # Session costs
python3 .claude/hooks/daily_summary_generator.py --status # Daily report
python3 .claude/hooks/directive_coverage_tracker.py --status  # Coverage %
python3 .claude/hooks/hook_health_monitor.py --status     # System health

# Tier 11-15 key status checks
python3 .claude/hooks/phase_ordering_enforcer.py --status        # Phase progression
python3 .claude/hooks/phase_transition_validator.py --status     # Phase transitions
python3 .claude/hooks/directive_completeness_validator.py --status # Directive validation
python3 .claude/hooks/brand_voice_compliance.py --status          # Voice compliance
python3 .claude/hooks/retry_loop_detector.py --status             # Retry blocks
python3 .claude/hooks/workflow_completion_tracker.py --status     # Completion rates
python3 .claude/hooks/system_health_reporter.py --status          # Full health report
python3 .claude/hooks/script_execution_benchmarker.py --status   # Performance
python3 .claude/hooks/client_sla_monitor.py --status              # SLA tracking
python3 .claude/hooks/error_categorizer.py --status               # Error types
```

### Customizing Hooks

**Adjust agent limit:**
```python
# In agent_limiter.py
MAX_AGENTS = 3  # Default is 5
```

**Adjust context thresholds:**
```python
# In context_budget_guard.py
WARN_THRESHOLD = 0.50   # Default 0.60
BLOCK_THRESHOLD = 0.80  # Default 0.85
```

**Add custom quality rules:**
```python
# In output_quality_gate.py, add to QUALITY_RULES dict
"*proposal*.md": {
    "min_words": 2500,
    "min_sections": 7,
    "required_keywords": ["Executive Summary", "Pricing", "Timeline", "Next Steps"]
}
```

**Add skill bible mappings:**
```python
# In skill_bible_reminder.py, add to SKILL_MAPPING dict
"proposal": ["SKILL_BIBLE_agency_sales_system.md", "SKILL_BIBLE_offer_positioning.md"]
```

**Add API key mappings:**
```python
# In prerequisite_api_key_mapper.py, add to SCRIPT_KEY_MAP
"my_new_script.py": ["MY_API_KEY", "MY_SECRET"]
```

**Add API cost estimates:**
```python
# In api_cost_estimator.py, add to COST_MAP
"my_expensive_script.py": {"api": "custom", "cost": 0.50}
```

---

## Common Workflows

### 1. VSL Funnel Creation (Complete Pipeline)
```bash
# Option A: Run the complete orchestrator
python3 execution/generate_complete_vsl_funnel.py \
  --company "Acme Corp" \
  --website "https://acmecorp.com" \
  --offer "B2B Lead Generation"

# Option B: Run individual steps
python3 execution/research_company_offer.py --company "Acme Corp" --website "https://acmecorp.com"
python3 execution/generate_vsl_script.py --research-file ".tmp/research.json"
python3 execution/generate_sales_page.py --vsl-file ".tmp/vsl_script.md"
python3 execution/generate_email_sequence.py --research-file ".tmp/research.json"
```

**Outputs:**
- `.tmp/vsl_funnel_<company>/01_research.md`
- `.tmp/vsl_funnel_<company>/02_vsl_script.md`
- `.tmp/vsl_funnel_<company>/03_sales_page.md`
- `.tmp/vsl_funnel_<company>/04_email_sequence.md`

### 2. Cold Email Campaign
```bash
python3 execution/write_cold_emails.py \
  --sender "John Smith" \
  --company "Acme Corp" \
  --offer "Lead generation service" \
  --target "Marketing agencies"
```

### 3. Market Research
```bash
python3 execution/research_company_offer.py \
  --company "Target Company" \
  --website "https://targetcompany.com" \
  --offer "Their main product"
```

### 4. Content Generation
```bash
# Blog post
python3 execution/generate_blog_post.py --topic "AI in marketing" --length 1500

# LinkedIn post
python3 execution/generate_linkedin_post.py --topic "Agency growth tips"

# Newsletter
python3 execution/generate_newsletter.py --theme "Weekly AI updates"
```

---

## Modal Serverless Deployment

Execution scripts can be deployed to Modal as serverless webhooks. This gives workflows a public URL that can be triggered by external services (Calendly, Stripe, cron, etc.) without running a server.

### Deploy Command
```bash
modal deploy execution/<script>.py
```

### Currently Deployed Apps

| App | Endpoints | Purpose |
|-----|-----------|---------|
| `calendly-meeting-prep` | webhook, health | Auto-research when meetings booked |
| `slack-test` | webhook, health | Test Modal → Slack pipeline |

### Modal Secrets (configured at modal.com)

| Secret Name | Environment Variable |
|-------------|---------------------|
| `openrouter-secret` | OPENROUTER_API_KEY |
| `perplexity-secret` | PERPLEXITY_API_KEY |
| `slack-webhook` | SLACK_WEBHOOK_URL |
| `google-service-account` | GOOGLE_SERVICE_ACCOUNT_JSON |
| `calendly-secret` | CALENDLY_API_KEY |

### Critical: dotenv Import Pattern

Scripts deployed to Modal MUST separate `requests` and `dotenv` imports. Modal containers don't have `python-dotenv` installed, and bundling both in a single `try/except sys.exit(1)` block crashes the container silently (requests hang forever, no error returned).

```python
# CORRECT - works on Modal and locally
try:
    import requests
except ImportError:
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # Not needed on Modal
```

**37 scripts in `execution/` still have the crash-causing pattern.** Fix each one before deploying to Modal.

### Free Tier Limits
- **8 web endpoints max** (across all apps, ~4 apps with webhook+health each)
- 30 compute hours/month
- Cold starts: 2-10 seconds after idle

### Managing Apps
```bash
modal app list                    # See all apps and status
modal app stop <app-id>           # Free up endpoints
modal app logs <app-name>         # Debug failures
modal secret list                 # Check configured secrets
```

### Debugging Hangs
If `curl` connects but never returns:
1. Run `modal app logs <app-name>` — usually reveals an import crash
2. Check that all declared `modal.Secret.from_name()` secrets exist
3. Verify the script runs locally with `python3 execution/<script>.py --test`

---

## AIAA Dashboard & Webhook Deployment

All workflows are managed through the AIAA Dashboard deployed on Railway. The dashboard provides a central hub for monitoring, executing, and configuring workflows.

### Dashboard Features

| Feature | Description |
|---------|-------------|
| **150+ Workflows** | Full documentation with prerequisites, how-to-run, and process steps |
| **Active Workflows** | Dynamic discovery of cron + webhook workflows from Railway API |
| **Webhook Workflows** | Register, test, toggle, and delete webhook endpoints — no rebuild needed |
| **HTTP Forwarding** | Route webhook payloads to standalone processing services via `forward_url` |
| **Cron Management** | Schedule editor, toggle, Run Now, and delete for cron workflows |
| **Light/Dark Mode** | Toggle with localStorage persistence |
| **Environment Variables** | View and set API keys from the UI |
| **Real-time Logs** | See all workflow executions and webhook events |
| **Mobile Responsive** | Works on phones and tablets |
| **Password Protected** | Secure SHA-256 hashed login |

### Deploy Dashboard to Railway

**Prerequisites:**
```bash
npm install -g @railway/cli
railway login
```

**Deploy:**
```bash
cd railway_apps/aiaa_dashboard
railway init          # Select "Empty Project"
railway up            # Deploy the app
```

**Configure Environment Variables:**

**Dashboard-specific variables (set per-service):**
```bash
# Generate password hash
python3 << 'PYHASH'
import hashlib
password = "your-password"
print(hashlib.sha256(password.encode()).hexdigest())
PYHASH

# Set dashboard auth variables
railway variables set DASHBOARD_USERNAME="admin"
railway variables set DASHBOARD_PASSWORD_HASH="<hash-from-above>"
railway variables set FLASK_SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
railway variables set RAILWAY_API_TOKEN="<your-railway-api-token>"

# Generate public domain
railway domain
```

**API Keys as Project-Wide Shared Variables:**

API keys are set as **project-level shared variables** so ALL services inherit them automatically. Set them once via the dashboard's Environment page or the shared variables API:

```bash
# Via the dashboard UI: go to Environment page, set each key
# Via the API (from any script that can reach the dashboard):
curl -X POST "https://your-dashboard.up.railway.app/api/shared-variables/sync" \
  -H "Content-Type: application/json" -H "Cookie: session=$SESSION" \
  -d '{"variables": {"OPENROUTER_API_KEY": "...", "PERPLEXITY_API_KEY": "..."}}'
```

The deploy script (`execution/deploy_to_railway.py`) automatically syncs API keys as shared variables during deployment.

**Required Variables:**
| Variable | Scope | Required For |
|----------|-------|-------------|
| `DASHBOARD_USERNAME` | Dashboard service | Dashboard login |
| `DASHBOARD_PASSWORD_HASH` | Dashboard service | Dashboard login |
| `FLASK_SECRET_KEY` | Dashboard service | Session security |
| `RAILWAY_API_TOKEN` | Dashboard service | Cron management, shared variable sync |
| `OPENROUTER_API_KEY` | **Shared (project)** | All AI generation workflows |
| `PERPLEXITY_API_KEY` | **Shared (project)** | Research workflows |
| `ANTHROPIC_API_KEY` | **Shared (project)** | Direct Claude access |
| `SLACK_WEBHOOK_URL` | **Shared (project)** | Notifications |
| `FAL_KEY` | **Shared (project)** | Image generation |
| `APIFY_API_TOKEN` | **Shared (project)** | Lead scraping |
| `CALENDLY_API_KEY` | **Shared (project)** | Calendly integration |
| `INSTANTLY_API_KEY` | **Shared (project)** | Email outreach |

### Dashboard Endpoints

Once deployed, your dashboard provides these endpoints:

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/` | GET | Yes | Dashboard home |
| `/health` | GET | No | Health check |
| `/login` | GET/POST | No | Authentication |
| `/workflows` | GET | Yes | Active Workflows page (cron + webhook) |
| `/workflow/<id>` | GET | Yes | Workflow details & documentation |
| `/env` | GET | Yes | Environment variable management |
| `/logs` | GET | Yes | Execution logs |
| **Cron Workflow API** | | | |
| `/api/active-workflows` | GET | Yes | List active cron workflows (JSON) |
| `/api/active-workflows/refresh` | POST | Yes | Invalidate cache, re-fetch from Railway |
| `/api/workflow/toggle` | POST | Yes | Enable/disable cron schedule |
| `/api/workflow/schedule` | POST | Yes | Update cron schedule |
| `/api/workflow/run-now` | POST | Yes | Trigger immediate cron execution |
| `/api/workflow/delete` | POST | Yes | Delete a cron workflow service |
| **Webhook Workflow API** | | | |
| `/api/webhook-workflows` | GET | Yes | List all registered webhooks |
| `/api/webhook-workflows/register` | POST | Yes | Register new webhook (no rebuild) |
| `/api/webhook-workflows/unregister` | POST | Yes | Delete a webhook workflow |
| `/api/webhook-workflows/toggle` | POST | Yes | Enable/disable a webhook |
| `/api/webhook-workflows/test` | POST | Yes | Send test payload to a webhook |
| `/webhook/<slug>` | POST | No | Public webhook endpoint (receives external payloads) |
| **Shared Variables API** | | | |
| `/api/shared-variables` | GET | Yes | List all project-level shared variables (redacted) |
| `/api/shared-variables/set` | POST | Yes | Set a single shared variable |
| `/api/shared-variables/sync` | POST | Yes | Bulk-set multiple shared variables |

### Webhook Workflow System

The dashboard hosts a complete webhook workflow system. Webhooks are **registered via live API calls** — no rebuild or redeploy required. They appear on the Active Workflows page alongside cron workflows.

**Two Types of Active Workflows:**
| Type | Trigger | Managed By | Deploy Method |
|------|---------|------------|---------------|
| **Cron Workflows** | Railway cron schedule | Railway API (`serviceInstanceUpdate`) | `railway up --service <name>` |
| **Webhook Workflows** | External HTTP POST | Dashboard in-memory registry | `POST /api/webhook-workflows/register` (no rebuild) |

**Webhook Architecture:**
```
Registration (no rebuild):
  POST /api/webhook-workflows/register
    → Updates in-memory _webhook_registry (instant)
    → Persists to WEBHOOK_CONFIG env var via Railway API (background, best-effort)
    → Writes webhook_config.json to disk (backup)

On startup, dashboard loads config from:
  1. WEBHOOK_CONFIG env var (primary — survives restarts)
  2. webhook_config.json file (seed fallback — first deploy only)

Incoming webhook (no forward_url):
  POST /webhook/<slug>
    → Checks in-memory registry
    → Returns 404 if not registered, 503 if disabled
    → Sends Slack notification (if slack_notify: true)
    → Returns 200 with JSON response

Incoming webhook (with forward_url):
  POST /webhook/<slug>
    → Checks in-memory registry
    → Forwards payload to forward_url as POST:
        {webhook_slug, webhook_name, source, payload, timestamp}
    → Returns processing service response to caller
    → Returns 502 if forward fails
```

**Register a Webhook (no rebuild):**
```bash
# Via execution script
python3 execution/deploy_webhook_workflow.py \
  --slug ai-news \
  --name "AI News Digest" \
  --description "Fetches AI news via Perplexity" \
  --source "Automation" \
  --forward-url "https://ai-news-processor.up.railway.app/process" \
  --slack-notify

# Via curl
curl -X POST "https://your-dashboard.up.railway.app/api/webhook-workflows/register" \
  -H "Content-Type: application/json" \
  -H "Cookie: session=$SESSION" \
  -d '{"slug": "ai-news", "name": "AI News", "description": "...", "source": "Automation", "slack_notify": true}'
```

**Register Payload Fields:**
| Field | Required | Description |
|-------|----------|-------------|
| `slug` | Yes | URL slug — maps to `/webhook/<slug>`. Lowercase, hyphens only. |
| `name` | Yes | Display name in dashboard UI |
| `description` | No | What happens when webhook fires |
| `source` | No | External service name (badge in UI). Default: "Unknown" |
| `slack_notify` | No | Send Slack notification on receive. Default: false |
| `enabled` | No | Active on registration. Default: true |
| `forward_url` | No | URL to forward payloads to for custom processing |

**Dashboard UI Actions (all work without rebuild):**
- **Copy URL** — copies the public webhook endpoint URL
- **Test** — sends a test payload to the webhook
- **Toggle** — enable/disable the webhook
- **Delete** — unregisters the webhook, refreshes the page

**HTTP Forwarding for Custom Processing:**
Set `forward_url` to route payloads to a standalone processing service. The dashboard acts as a router — receives the webhook, wraps the payload with metadata, and forwards it. No dashboard rebuild needed for custom processing logic.

**Key Files:**
- `railway_apps/aiaa_dashboard/app.py` — webhook handler, registry, shared variables API, all endpoints
- `railway_apps/aiaa_dashboard/workflow_config.json` — workflow metadata (friendly names, descriptions)
- `execution/deploy_to_railway.py` — unified deploy script (cron, webhook, web) with shared variable sync
- `directives/deploy_to_railway.md` — full deployment SOP

### Workflow Execution via Dashboard

**Option 1: Manual Execution (Dashboard UI)**
1. Login to dashboard
2. Navigate to Workflows
3. Find workflow (search or browse)
4. Click workflow for full documentation
5. Copy the execution command
6. Run in Claude Code

**Option 2: Direct Script Execution**
```bash
# All workflows run via execution scripts
python3 execution/<workflow_script>.py --arg1 "value" --arg2 "value"
```

**Option 3: Webhook Trigger**
External services trigger workflows automatically via webhooks configured in the dashboard.

### Viewing Workflow Documentation

Each workflow in the dashboard includes:
- **Description**: What the workflow does
- **Prerequisites**: Required API keys and setup
- **How to Run**: Exact command with arguments
- **Process Steps**: Step-by-step breakdown
- **Inputs/Outputs**: Expected data format
- **Related Workflows**: Connected workflows

---

## Publishing Workflows to Railway (CRITICAL)

**MANDATORY DIRECTIVE:** Whenever you are asked to deploy, publish, or schedule ANY workflow, you MUST read and follow this entire section. Do not skip any rules. This applies to ALL workflow deployments without exception.

**IMPORTANT:** When instructed to publish, deploy, or schedule a workflow, you MUST read your `/directives/deploy_to_railway.md` directive AND use the unified deploy script:

```bash
# Deploy any workflow (auto-detects type, sets shared vars, registers with dashboard)
python3 execution/deploy_to_railway.py --directive <name> --auto

# Or specify type explicitly
python3 execution/deploy_to_railway.py --directive <name> --type cron --schedule "0 */3 * * *" --auto
python3 execution/deploy_to_railway.py --directive <name> --type webhook --slug <slug> --slack-notify --auto
python3 execution/deploy_to_railway.py --directive <name> --type web --auto
```

The deploy script handles ALL of the following automatically: scaffolding, deployment, shared variable sync, cron configuration, webhook registration, and `workflow_config.json` updates.

### Rule 1: Same Railway Project as Dashboard
ALL workflows MUST be deployed to the **SAME Railway project** where the AIAA Dashboard was installed during initial setup. Never create separate Railway projects for individual workflows.

**To find the dashboard project:**
```bash
cd railway_apps/aiaa_dashboard
railway status
# Note the Project name/ID
```

**To deploy a new workflow service to the same project:**
```bash
cd railway_apps/<new_workflow>
railway link -p <DASHBOARD_PROJECT_ID>
railway up
```

### Rule 2: Register Workflow in Dashboard Config

After deploying ANY scheduled workflow (cron job), update the workflow metadata config:

**Location:** `railway_apps/aiaa_dashboard/workflow_config.json`

```json
{
  "project_id": "3b96c81f-9518-4131-b2bc-bcd7a524a5ef",
  "cache_ttl_seconds": 300,
  "workflows": {
    "<SERVICE_ID>": {
      "name": "Friendly Workflow Name",
      "description": "What this workflow does",
      "enabled": true
    }
  }
}
```

**How it works:**
- The dashboard dynamically queries Railway API for all services with cron schedules in the project
- Any service with a `cronSchedule` set automatically appears in Active Workflows
- The `workflow_config.json` provides friendly names and descriptions (without it, the raw Railway service name is used)
- Results are cached for 5 minutes (configurable via `cache_ttl_seconds`)
- **Requires `RAILWAY_API_TOKEN`** to be set on the dashboard service (see Rule 7)

**When you need to redeploy the dashboard vs. not:**
- **NO redeploy needed:** Changing a cron schedule, disabling/enabling cron, triggering a run — the API query picks up live state
- **Redeploy needed:** Adding a new entry to `workflow_config.json` for friendly name/description (the file is baked into the dashboard deployment)
- **No action needed:** A new cron service deployed to the project auto-appears with its raw Railway service name even without a config entry

**To get the SERVICE_ID after deploying:**
```bash
# Use --json to get the actual service ID (plain text output shows deployment IDs, NOT service IDs)
cd railway_apps/<new_workflow>
railway service status --all --json
# Look for the "id" field — that is the service ID
# The UUID shown in plain-text output (middle column) is the DEPLOYMENT ID, not the service ID
```

**To force refresh the workflow list (optional):**
Call POST `/api/active-workflows/refresh` while logged into the dashboard.

### Rule 3: Environment Variables via Shared Variables
API keys are now **project-level shared variables** -- set once, inherited by all services automatically. The deploy script (`deploy_to_railway.py`) syncs them via the dashboard's `/api/shared-variables/sync` endpoint during deployment.

**Shared API keys** (set once, all services get them):
- OPENROUTER_API_KEY, PERPLEXITY_API_KEY, SLACK_WEBHOOK_URL, ANTHROPIC_API_KEY, FAL_KEY, APIFY_API_TOKEN, INSTANTLY_API_KEY, CALENDLY_API_KEY

**Service-specific variables** (set per-service, e.g. GOOGLE_OAUTH_TOKEN_PICKLE) are still set via Railway CLI by the deploy script.

**To manually sync shared variables:**
```bash
# Via dashboard Environment page (sets project-wide shared variables)
# Or via API:
curl -X POST "https://your-dashboard.up.railway.app/api/shared-variables/sync" \
  -H "Content-Type: application/json" -H "Cookie: session=$SESSION" \
  -d '{"variables": {"OPENROUTER_API_KEY": "...", "PERPLEXITY_API_KEY": "..."}}'
```

**Check the workflow's directive** (`directives/<workflow>.md`) for the "Prerequisites" section listing required API keys.

### Rule 4: Google OAuth Token for Google Services
If a workflow creates Google Docs, Sheets, or uses ANY Google API, you MUST upload the `token.pickle` OAuth token:

```bash
# 1. Check if workflow uses Google services
grep -l "google" railway_apps/<workflow>/*.py

# 2. If yes, find token.pickle (should be in project root)
ls -la token.pickle

# 3. Base64 encode and upload to Railway
python3 -c "
import base64
with open('token.pickle', 'rb') as f:
    print(base64.b64encode(f.read()).decode())
" | railway variables set GOOGLE_OAUTH_TOKEN_PICKLE="$(cat)"

# Or manually:
TOKEN=$(python3 -c "import base64; print(base64.b64encode(open('token.pickle','rb').read()).decode())")
railway variables set GOOGLE_OAUTH_TOKEN_PICKLE="$TOKEN"
```

**Why:** Service accounts have 0 GB storage quota and cannot create files. OAuth user tokens use YOUR Google account's storage.

### Publishing Checklist
When publishing a workflow, complete ALL steps:

- [ ] Deploy to SAME Railway project as dashboard (`railway link -p <PROJECT_ID> && railway up`)
- [ ] Set ALL required environment variables (Railway CLI or embed as fallback — see Rule 3 and gotchas)
- [ ] **If workflow uses Google APIs:** Upload `GOOGLE_OAUTH_TOKEN_PICKLE` (base64 encoded token.pickle)
- [ ] Set cron schedule via `serviceInstanceUpdate` GraphQL mutation (railway.json alone is not enough)
- [ ] Add entry to `railway_apps/aiaa_dashboard/workflow_config.json` with service ID, friendly name, and description
- [ ] Redeploy dashboard to pick up the new config entry (`railway up --service aiaa-dashboard`)
- [ ] Verify workflow appears in dashboard Active Workflows page
- [ ] Test that workflow runs successfully (use "Run Now" button or `deploymentInstanceExecutionCreate` mutation)

### Rule 5: Google Docs Formatting (NOT Markdown)
When creating Google Docs, content MUST be formatted using native Google Docs formatting (headings, bold, dividers), NOT raw markdown text. Markdown syntax like `# Heading` or `**bold**` will appear as literal text in Google Docs.

**Required Formatting Approach:**
```python
def format_content_for_google_docs(markdown_content: str) -> list:
    """Convert markdown to Google Docs API formatting requests."""
    import re

    requests = []
    current_index = 1

    lines = markdown_content.split('\n')

    for line in lines:
        if not line.strip():
            # Empty line - add newline
            requests.append({
                'insertText': {'location': {'index': current_index}, 'text': '\n'}
            })
            current_index += 1
            continue

        # Check for horizontal rule
        if line.strip() == '---':
            requests.append({
                'insertText': {'location': {'index': current_index}, 'text': '\n'}
            })
            current_index += 1
            requests.append({
                'insertSectionBreak': {
                    'location': {'index': current_index},
                    'sectionType': 'CONTINUOUS'
                }
            })
            continue

        # Process headings (# ## ###)
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if heading_match:
            level = len(heading_match.group(1))
            text = heading_match.group(2) + '\n'
            heading_type = {1: 'HEADING_1', 2: 'HEADING_2', 3: 'HEADING_3'}.get(level, 'HEADING_4')

            requests.append({
                'insertText': {'location': {'index': current_index}, 'text': text}
            })
            requests.append({
                'updateParagraphStyle': {
                    'range': {'startIndex': current_index, 'endIndex': current_index + len(text)},
                    'paragraphStyle': {'namedStyleType': heading_type},
                    'fields': 'namedStyleType'
                }
            })
            current_index += len(text)
            continue

        # Process bold text **text**
        text = line + '\n'
        requests.append({
            'insertText': {'location': {'index': current_index}, 'text': text}
        })

        # Find and format bold sections
        for match in re.finditer(r'\*\*(.+?)\*\*', line):
            start = current_index + match.start()
            end = current_index + match.end()
            requests.append({
                'updateTextStyle': {
                    'range': {'startIndex': start, 'endIndex': end},
                    'textStyle': {'bold': True},
                    'fields': 'bold'
                }
            })

        current_index += len(text)

    return requests
```

**Key Formatting Elements:**
| Markdown | Google Docs API |
|----------|-----------------|
| `# Heading` | `updateParagraphStyle` with `HEADING_1` |
| `## Subhead` | `updateParagraphStyle` with `HEADING_2` |
| `**bold**` | `updateTextStyle` with `bold: True` |
| `---` | `insertSectionBreak` (horizontal rule) |
| `- item` | `createParagraphBullets` |

**NEVER** insert raw markdown into Google Docs. Always convert to native formatting.

### Rule 6: Railway GraphQL API for Cron Management
The dashboard uses Railway's GraphQL API to manage cron schedules. Critical learnings:

**API Endpoint:** `https://backboard.railway.app/graphql/v2`

**To disable a cron schedule:**
```graphql
mutation {
  serviceInstanceUpdate(
    serviceId: "SERVICE_ID",
    environmentId: "ENV_ID",
    input: { cronSchedule: null }  # MUST be null, NOT empty string ""
  )
}
```

**To enable/restore a cron schedule:**
```graphql
mutation {
  serviceInstanceUpdate(
    serviceId: "SERVICE_ID",
    environmentId: "ENV_ID",
    input: { cronSchedule: "0 */3 * * *" }
  )
}
```

**To check cron status:**
```graphql
query {
  service(id: "SERVICE_ID") {
    serviceInstances {
      edges { node { cronSchedule environmentId } }
    }
  }
}
```

**To trigger immediate cron execution (Run Now):**
```graphql
# First get the service instance ID (NOT service_id)
query {
  service(id: "SERVICE_ID") {
    serviceInstances { edges { node { id } } }
  }
}

# Then trigger execution
mutation {
  deploymentInstanceExecutionCreate(input: {
    serviceInstanceId: "SERVICE_INSTANCE_ID"
  })
}
```

**Critical Gotchas:**
- `cronSchedule: ""` (empty string) causes "Problem processing request" error
- `cronSchedule: null` properly disables the cron
- `ServiceUpdateInput` only has `icon` and `name` - use `ServiceInstanceUpdateInput` for cron
- `serviceInstanceRedeploy` fails if no existing deployment - use `railway up` CLI instead
- After removing a deployment, the service shows "offline" even with cron set - must redeploy
- `deploymentInstanceExecutionCreate` triggers immediate cron run, bypassing schedule
- `serviceInstanceId` is different from `serviceId` - get it from `service.serviceInstances.edges[].node.id`
- `variableUpsert` mutation may timeout with 504 Gateway errors - workaround: embed credentials in code with env var fallback (e.g., `os.getenv("VAR") or "fallback_value"`)
- `serviceInstanceUpdate` works reliably even when `variableUpsert` times out
- `railway link <PROJECT_ID>` (positional arg) fails — must use `railway link -p <PROJECT_ID>` with the `-p` flag
- `railway service status --all` plain text output shows **deployment IDs** in the middle column, NOT service IDs. Use `--json` flag to get actual service IDs (the `"id"` field)
- `railway up` with multiple services requires `--service <name>` flag to specify which service to deploy
- macOS does not have the `timeout` command — use Python `subprocess` with timeout or background process with `sleep` + kill instead
- `railway.json` `cronSchedule` field is only applied on initial deploy — subsequent schedule changes must use `serviceInstanceUpdate` GraphQL mutation
- Dynamic workflow loading on the dashboard requires `RAILWAY_API_TOKEN` to be set as an env var on the dashboard service

### Rule 7: Dashboard RAILWAY_API_TOKEN
The dashboard needs a Railway API token to manage cron schedules AND to dynamically load active workflows. Set it in Railway:

```bash
# Get token from Railway CLI config (stored at ~/.railway/config.json)
TOKEN=$(python3 -c "import json; d=json.load(open('$HOME/.railway/config.json')); print(d.get('user', {}).get('token', ''))")

# Set in Railway for dashboard service (preferred method — CLI)
cd railway_apps/aiaa_dashboard
railway variables set RAILWAY_API_TOKEN="$TOKEN" --service aiaa-dashboard
```

**Fallback if `railway variables set` times out:** Embed the token directly in app.py as a fallback:
```python
RAILWAY_API_TOKEN = os.getenv("RAILWAY_API_TOKEN", "<PASTE_TOKEN_HERE>")
```

**Do NOT use** `variableUpsert` GraphQL mutation for this — it is known to timeout with 504 errors (see gotchas above).

### Rule 8: Dashboard Schedule Editor
The dashboard has a granular schedule editor for cron jobs with these components:

**UI Elements:**
- Interval input (1-24) - how often to run
- Unit selector ("hours" or "days")
- Minute input (0-59) - when within the hour
- Save button - applies changes to Railway
- Current cron display - shows actual expression

**Cron Expression Builder:**
```javascript
// Every N hours at minute X
if (unit === 'hours') {
    if (interval === 1) return `${minute} * * * *`;
    return `${minute} */${interval} * * *`;
}
// Every N days at 00:XX
if (unit === 'days') {
    if (interval === 1) return `${minute} 0 * * *`;
    return `${minute} 0 */${interval} * *`;
}
```

**Human-Readable Conversion (cronToText):**
| Cron Pattern | Display Text |
|--------------|--------------|
| `0 */3 * * *` | "Every 3 hours" |
| `30 * * * *` | "Every hour at :30" |
| `0 0 * * *` | "Daily at 00:00" |
| `0 9 * * *` | "Daily at 09:00" |
| `0 0 */2 * *` | "Every 2 days" |

**Key Implementation Notes:**
- Schedule text updates dynamically on save AND on page load
- Editor parses current cron to pre-populate inputs
- Uses `data-service-id` attributes to link displays to workflows
- RAILWAY_API_TOKEN must be set for API calls to work

### Rule 9: Dynamic Workflow Discovery Architecture

The dashboard's Active Workflows page loads workflows dynamically from Railway's API rather than a hardcoded list. Here is how the system works:

**Data Flow:**
1. User visits `/workflows` (Active Workflows page)
2. `fetch_active_workflows_from_railway()` checks in-memory cache (TTL: 5 min)
3. If cache expired, queries Railway GraphQL API: `project.services.edges[].node.serviceInstances.edges[].node.cronSchedule`
4. Filters to only services with a non-null `cronSchedule`
5. Merges with `workflow_config.json` for friendly names/descriptions
6. Caches result and returns to template

**Key Files:**
- `railway_apps/aiaa_dashboard/app.py` — `fetch_active_workflows_from_railway()`, `parse_cron_to_readable()`, `invalidate_workflow_cache()`
- `railway_apps/aiaa_dashboard/workflow_config.json` — service ID → friendly name/description mapping

**API Endpoints:**
- `GET /api/active-workflows` — returns current workflow list as JSON
- `POST /api/active-workflows/refresh` — invalidates cache and re-fetches from Railway API

**Cache Invalidation Triggers:**
- Automatic: cache expires after `cache_ttl_seconds` (default 300s)
- Manual: `POST /api/active-workflows/refresh`
- On delete: `api_workflow_delete()` calls `invalidate_workflow_cache()` after successful deletion

### Rule 10: Webhook Workflow Deployment

**IMPORTANT:** Webhook workflows now deploy as **standalone Railway services** (just like cron workflows) with a Flask app. The dashboard registers a webhook slug with a `forward_url` pointing to the standalone service. Use the unified deploy script:

```bash
# Deploy webhook workflow (deploys standalone service + registers webhook on dashboard)
python3 execution/deploy_to_railway.py --directive calendly_meeting_prep --type webhook --slug calendly --slack-notify --auto
```

**Key Differences from Cron Deployment:**
| Aspect | Cron Workflows | Webhook Workflows |
|--------|---------------|-------------------|
| Deploy method | `deploy_to_railway.py --type cron` | `deploy_to_railway.py --type webhook` |
| Service type | Standalone with `run.py` + `railway.json` | Standalone Flask app with `/webhook` endpoint |
| Dashboard integration | Auto-appears via Railway API | Webhook registered with `forward_url` to service |
| Trigger | Railway cron schedule | External HTTP POST → dashboard → forward to service |
| Processing | In standalone service | In standalone service (heavy processing supported) |

**Architecture:**
```
External Service (Calendly, Stripe, etc.)
    → POST /webhook/<slug> on dashboard
    → Dashboard forwards payload to standalone service's /webhook endpoint
    → Standalone service does the heavy processing (API calls, doc creation, etc.)
```

**Webhook Persistence:**
- **In-memory registry** is the source of truth (instant updates)
- **WEBHOOK_CONFIG env var** provides durability across restarts (set via Railway API, best-effort)
- **webhook_config.json** is seed data for first deploy only (file is baked into image)

**Webhook Deployment Checklist:**
- [ ] Standalone service deployed and healthy
- [ ] Webhook registered on dashboard with `forward_url` pointing to service
- [ ] Webhook visible in dashboard Active Workflows page
- [ ] Test button works from dashboard UI
- [ ] External service configured to POST to dashboard webhook URL

---

## Key Execution Scripts

### Content & Copy
| Script | Purpose |
|--------|---------|
| `generate_vsl_funnel.py` | Complete VSL + landing page + emails |
| `generate_vsl_script.py` | VSL script only |
| `generate_sales_page.py` | Sales page copy |
| `generate_email_sequence.py` | Email nurture sequence |
| `generate_blog_post.py` | Long-form blog content |
| `generate_linkedin_post.py` | LinkedIn content |
| `write_cold_emails.py` | Cold email sequences |

### Research & Data
| Script | Purpose |
|--------|---------|
| `research_company_offer.py` | Deep company research via Perplexity |
| `research_market_deep.py` | Market/industry research |
| `research_prospect_deep.py` | Individual prospect research |
| `scrape_linkedin_apify.py` | LinkedIn profile scraping |

### Delivery & Integration
| Script | Purpose |
|--------|---------|
| `create_google_doc.py` | Upload to Google Docs |
| `send_slack_notification.py` | Send Slack messages |

### Dashboard & Deployment
| Script | Purpose |
|--------|---------|
| `deploy_aiaa_dashboard.py` | Deploy/update AIAA dashboard to Railway |
| `deploy_to_railway.py` | Unified deploy for any workflow (cron, webhook, web) with shared variable sync |

### Utilities
| Script | Purpose |
|--------|---------|
| `convert_n8n_to_directive.py` | Convert N8N JSON to directive |
| `parse_vtt_transcript.py` | Extract text from VTT files |
| `validate_emails.py` | Email validation |

---

## Skill Bibles

Skill bibles provide deep domain expertise. Load relevant ones before execution.

### Finding Skill Bibles
```bash
# List all skill bibles
ls skills/SKILL_BIBLE_*.md

# Search by topic
ls skills/ | grep -i "vsl\|funnel\|email\|sales"
```

### Key Skill Bibles by Category

**VSL & Funnels:**
- `SKILL_BIBLE_vsl_writing_production.md`
- `SKILL_BIBLE_vsl_script_mastery_fazio.md`
- `SKILL_BIBLE_funnel_copywriting_mastery.md`
- `SKILL_BIBLE_agency_funnel_building.md`

**Cold Email & Outreach:**
- `SKILL_BIBLE_cold_email_mastery.md`
- `SKILL_BIBLE_cold_dm_email_conversion.md`
- `SKILL_BIBLE_email_deliverability.md`

**Agency & Sales:**
- `SKILL_BIBLE_agency_sales_system.md`
- `SKILL_BIBLE_agency_scaling_roadmap.md`
- `SKILL_BIBLE_offer_positioning.md`

**AI & Automation:**
- `SKILL_BIBLE_ai_automation_agency.md`
- `SKILL_BIBLE_monetizable_agentic_workflows.md`
- `SKILL_BIBLE_ai_prompting_workflows.md`

---

## Creating New Capabilities (Leader Manufacturing)

When a capability doesn't exist:

### Step 1: Check If It Really Doesn't Exist
```bash
ls directives/ | grep -i "<keyword>"
ls execution/ | grep -i "<keyword>"
ls skills/ | grep -i "<keyword>"
```

### Step 2: Create New Directive
```markdown
# directives/new_workflow.md

## What This Workflow Is
[One paragraph description]

## What It Does
1. [Step 1]
2. [Step 2]
3. [Step 3]

## Prerequisites
- Required API keys
- Required skill bibles
- Installation commands

## How to Run
```bash
python3 execution/new_workflow.py --arg1 "value"
```

## Inputs
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| arg1 | string | Yes | Description |

## Process
### Step 1: [Name]
[Details]

### Step 2: [Name]
[Details]

## Quality Gates
- [ ] Check 1
- [ ] Check 2

## Edge Cases
- Edge case 1 → Solution
- Edge case 2 → Solution
```

### Step 3: Create Execution Script
```python
#!/usr/bin/env python3
"""
New Workflow - [Description]

Usage:
    python3 execution/new_workflow.py --arg1 "value"
"""

import argparse
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--arg1", required=True)
    args = parser.parse_args()
    
    # Implementation
    print(f"Running with {args.arg1}")
    
if __name__ == "__main__":
    main()
```

### Step 4: Create Skill Bible (If Needed)
If this is a new domain, create `skills/SKILL_BIBLE_<topic>.md` with:
- Executive Summary
- Core Principles
- Techniques & Tactics
- Common Mistakes
- Quality Checklist

---

## Self-Annealing Protocol

After EVERY task completion:

### 1. Check for Errors
Did anything fail? Fix it:
```
Error occurred → Read stack trace → Fix script → Test → Update directive
```

### 2. Update Directive
Add learnings:
- New edge cases discovered
- Better approaches found
- Quality gate refinements

### 3. Update Skill Bible
Add domain knowledge:
- New techniques that worked
- Mistakes to avoid
- Industry-specific insights

### 4. Commit Changes
Keep the system improving:
```bash
git add directives/ execution/ skills/
git commit -m "Self-anneal: [what was learned]"
```

---

## Error Handling Patterns

### API Failures
```python
for attempt in range(3):
    try:
        result = api_call()
        break
    except Exception as e:
        if attempt == 2:
            raise
        time.sleep(10 * (attempt + 1))  # Exponential backoff
```

### Missing Inputs
Fail fast with clear message:
```python
if not args.required_field:
    print("Error: --required_field is required")
    sys.exit(1)
```

### Partial Failures
Degrade gracefully:
```
Critical workflow fails → Stop and report
Non-critical fails → Continue with warning
Delivery fails → Save locally, continue
```

---

## Environment Setup

### First-Time Setup
```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 3. Setup Google OAuth (for Docs integration)
# Place credentials.json in project root
python3 execution/create_google_doc.py --test

# 4. Deploy AIAA Dashboard to Railway
npm install -g @railway/cli
railway login
cd railway_apps/aiaa_dashboard
railway init
railway up
railway domain
```

### Required API Keys
| Key | Purpose | Get From |
|-----|---------|----------|
| `OPENROUTER_API_KEY` | LLM access | openrouter.ai |
| `PERPLEXITY_API_KEY` | Research | perplexity.ai |
| `SLACK_WEBHOOK_URL` | Notifications | Slack app settings |
| `GOOGLE_APPLICATION_CREDENTIALS` | Docs/Sheets | Google Cloud Console |

---

## Debugging Tips

### Check Script Arguments
```bash
python3 execution/<script>.py --help
```

### Test with Minimal Input
```bash
python3 execution/generate_vsl_funnel.py \
  --product "Test Product" \
  --price "$99" \
  --audience "Test audience"
```

### Check API Connectivity
```bash
# Test OpenRouter
curl https://openrouter.ai/api/v1/models -H "Authorization: Bearer $OPENROUTER_API_KEY"

# Test Perplexity
curl https://api.perplexity.ai/chat/completions \
  -H "Authorization: Bearer $PERPLEXITY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"llama-3.1-sonar-small-128k-online","messages":[{"role":"user","content":"test"}]}'
```

### View Execution Logs
```bash
# Dashboard logs (via Railway)
railway logs

# Local execution
python3 execution/<script>.py 2>&1 | tee output.log

# Check dashboard health
curl https://your-app.up.railway.app/health
```

---

## Summary: Your Role as Orchestrator

You are the **brain** of this system. Your responsibilities:

1. **Parse Intent** → Understand what the user wants
2. **Load Agency Context** → Read `context/` to understand who you're representing
3. **Load Client Context** → If client-specific, read `clients/{client}/` for their rules
4. **Find Capability** → Locate directive + script + skill bible
5. **Execute** → Run scripts, follow SOPs, check quality gates
6. **Deliver** → Save locally, upload to Google Docs, notify via Slack
7. **Self-Anneal** → Learn from every execution, update the system

**Core Principles:**
- **ALWAYS load agency context before generating content**
- **ALWAYS load client context when doing client-specific work**
- Check for existing tools before creating new ones
- Load skill bibles for domain expertise
- Push deterministic work into Python scripts
- Self-anneal when things break
- Update directives as you learn

**Context Loading Priority:**
```
1. context/agency.md      → Always load first
2. context/brand_voice.md → For any content creation
3. clients/{name}/*.md    → For client-specific work
4. skills/SKILL_BIBLE_*   → For domain expertise
5. directives/*.md        → For workflow SOPs
```

**The bottleneck isn't ideas or execution. It's deciding what to build next.**

---

## Quick Commands Reference

```bash
# View all workflows
# Open your AIAA Dashboard at https://your-app.up.railway.app

# Run VSL funnel
python3 execution/generate_complete_vsl_funnel.py --company "X" --website "Y" --offer "Z"

# Research a company
python3 execution/research_company_offer.py --company "X" --website "Y"

# Create Google Doc from markdown
python3 execution/create_google_doc.py --file ".tmp/output.md" --title "Doc Title"

# Send Slack notification
python3 execution/send_slack_notification.py --message "Task complete" --channel "#general"

# Deploy/update dashboard
cd railway_apps/aiaa_dashboard && railway up

# Deploy any workflow to Railway (unified script)
python3 execution/deploy_to_railway.py --directive <name> --auto

# Deploy cron workflow
python3 execution/deploy_to_railway.py --directive <name> --type cron --schedule "0 */3 * * *" --auto

# Deploy webhook workflow
python3 execution/deploy_to_railway.py --directive <name> --type webhook --slug <slug> --slack-notify --auto

# List deployable directives
python3 execution/deploy_to_railway.py --list

# Check deployment info for a directive
python3 execution/deploy_to_railway.py --directive <name> --info

# Check dashboard health
curl https://your-app.up.railway.app/health
```
