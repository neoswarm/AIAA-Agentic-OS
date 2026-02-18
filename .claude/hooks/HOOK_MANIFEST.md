# Hook Manifest

> **Active Hooks:** 35 | **Archived:** 93 | **Last Pruned:** 2026-02-17

This system uses a minimal hook set focused on safety-critical blocking, essential quality gates, deployment safety, and key analytics. The remaining 93 hooks are archived in `_archived/` and can be restored individually.

---

## Active Hooks (35)

### Tier 1: Safety Critical — Hard Blockers (15 hooks)

These hooks **block dangerous operations** and cannot be removed without risking data loss, secret exposure, or system instability.

| # | Hook | Type | Tool | Blocks? | Purpose |
|---|------|------|------|---------|---------|
| 1 | `agent_limiter.py` | Pre | Task | Yes | Max 5 parallel agents |
| 2 | `context_budget_guard.py` | Pre | Task | Yes (85%) | Warns 60%, alerts 75%, blocks 85% context |
| 3 | `secrets_guard.py` | Pre | Write+Edit | Yes | Blocks writes to .env, credentials, API keys |
| 4 | `pii_detection_guard.py` | Pre | Write | Yes (SSN/CC) | Detects PII, blocks SSN/credit card patterns |
| 5 | `file_size_limit_guard.py` | Pre | Write | Yes (500K) | Warns >100K chars, blocks >500K chars |
| 6 | `large_file_read_blocker.py` | Pre | Read | Yes | Blocks 300+ line reads when agents active |
| 7 | `context_pollution_preventer.py` | Pre | Read | Block@12 | Prevents loading too many context files |
| 8 | `script_exists_guard.py` | Pre | Bash | Yes | Verifies script file exists before running |
| 9 | `retry_loop_detector.py` | Pre | Bash | Block@3 | Blocks scripts that fail 3+ times consecutively |
| 10 | `file_path_traversal_guard.py` | Pre | Bash | Block | Blocks path traversal attacks (../../) |
| 11 | `command_injection_guard.py` | Pre | Bash | Block | Blocks shell injection (backticks, $(), pipe to sh) |
| 12 | `memory_usage_estimator.py` | Pre | Bash | Warn/Block | Warns@512MB, blocks@2GB |
| 13 | `backup_before_destructive.py` | Pre | Bash | Block | Blocks rm/reset on critical dirs without backup |
| 14 | `json_output_validator.py` | Post | Write | Yes | Blocks invalid JSON writes to .tmp/ |
| 15 | `modal_endpoint_limit_tracker.py` | Pre | Bash | Yes (8) | Blocks exceeding Modal free tier 8-endpoint limit |

### Tier 2: Quality & Workflow — Warn Only (10 hooks)

These hooks **warn** about quality issues and enforce workflow patterns. They never block execution.

| # | Hook | Type | Tool | Blocks? | Purpose |
|---|------|------|------|---------|---------|
| 16 | `doe_enforcer.py` | Dual | Read+Bash | Warn | Directive must be read before execution script |
| 17 | `output_quality_gate.py` | Post | Write | Warn | Word count, sections, keywords by file type |
| 18 | `content_length_enforcer.py` | Post | Write | Warn | Granular min lengths by deliverable type |
| 19 | `execution_logger.py` | Post | Bash | No | Logs all script runs to execution_log.json |
| 20 | `error_pattern_detector.py` | Post | Bash | Warn | Alerts when script fails 3+ times |
| 21 | `self_anneal_reminder.py` | Post | Bash | Info | Self-annealing protocol after script errors |
| 22 | `skill_bible_reminder.py` | Pre | Bash | Info | Suggests relevant skill bibles |
| 23 | `delivery_pipeline_validator.py` | Post | Write | Info | Reminds about Google Doc + Slack delivery steps |
| 24 | `client_work_context_gate.py` | Pre | Bash | Warn | Detects client work, warns if no client context loaded |
| 25 | `brand_voice_compliance.py` | Post | Write | Warn | Checks content against brand_voice.md |

### Tier 3: Deployment Safety (5 hooks)

These hooks protect against deployment mistakes on Railway and Modal.

| # | Hook | Type | Tool | Blocks? | Purpose |
|---|------|------|------|---------|---------|
| 26 | `railway_deploy_guard.py` | Pre | Bash | Info | Deployment checklist before railway up |
| 27 | `deployment_config_validator.py` | Pre | Bash | Warn | Checks for Procfile, requirements.txt |
| 28 | `modal_deploy_guard.py` | Pre | Bash | Warn | Modal pre-deploy checklist |
| 29 | `modal_dotenv_crash_detector.py` | Pre | Bash | Warn | Scans for crash-causing requests+dotenv import pattern |
| 30 | `production_safety_guard.py` | Pre | Bash | Warn | Extra warnings for destructive/production commands |

### Tier 4: Analytics — Silent Tracking (5 hooks)

These hooks track metrics silently. Zero performance impact on tool calls.

| # | Hook | Type | Tool | Blocks? | Purpose |
|---|------|------|------|---------|---------|
| 31 | `api_cost_estimator.py` | Post | Bash | No | Estimates API costs per script and session total |
| 32 | `session_activity_logger.py` | Post | Bash | No | Logs all session activities by type |
| 33 | `workflow_pattern_tracker.py` | Post | Bash | No | Tracks workflow usage, success rates |
| 34 | `hook_health_monitor.py` | Post | Bash | Warn | Meta-hook: monitors all other hooks' health |
| 35 | `system_health_reporter.py` | Post | Bash | Warn | Aggregates all hook metrics into unified health report |

---

## Settings Registration Summary

| Section | Count | Details |
|---------|-------|---------|
| PreToolUse | 23 entries | 2 Task, 3 Write, 1 Edit, 2 Read, 15 Bash |
| PostToolUse | 14 entries | 1 Read, 5 Write, 8 Bash |
| **Total registrations** | **37** | (35 unique hooks; doe_enforcer + secrets_guard registered twice) |

---

## Archived Hooks (93)

All archived hooks are in `.claude/hooks/_archived/`. They are fully functional and can be restored at any time.

<details>
<summary>Full list of archived hooks (click to expand)</summary>

| Hook | Original Tier | Why Archived |
|------|--------------|--------------|
| `agency_context_freshness_checker.py` | Pre-Execution Safety | Low value — context freshness rarely matters |
| `api_key_validator.py` | DOE Enforcement | Redundant with prerequisite_api_key_mapper |
| `api_rate_limit_tracker.py` | Analytics | Marginal value — API providers handle rate limits |
| `api_response_validator.py` | Execution Safety | Redundant with error_pattern_detector |
| `checkpoint_enforcer.py` | Workflow Ops | Low signal-to-noise ratio |
| `circular_dependency_detector.py` | Client & Delivery | Edge case — rarely triggered |
| `client_approval_gate.py` | Client & Delivery | Process overhead |
| `client_billing_estimator.py` | Client & Delivery | Rarely used |
| `client_communication_logger.py` | Client & Delivery | Too verbose |
| `client_data_isolation_guard.py` | Output Safety | Redundant with client_work_context_gate |
| `client_deliverable_tracker.py` | Client & Delivery | Process overhead |
| `client_feedback_logger.py` | Client & Delivery | Rarely used |
| `client_rules_enforcer.py` | Output Safety | Subsumed by brand_voice_compliance |
| `client_sla_monitor.py` | Client & Delivery | Overhead for solo operation |
| `cold_email_workflow_enforcer.py` | Workflow-Specific | Too narrow — single workflow |
| `concurrent_write_guard.py` | Output Safety | Edge case with agent_limiter active |
| `context_efficiency_tracker.py` | Analytics | Low value analytics |
| `context_load_optimizer.py` | Analytics | Suggestions rarely actionable |
| `context_loader_enforcer.py` | DOE Enforcement | Redundant with doe_enforcer |
| `copy_framework_enforcer.py` | Content Intelligence | Too prescriptive |
| `cron_schedule_validator.py` | Deployment | Edge case |
| `cross_directive_conflict_detector.py` | DOE Integrity | Edge case |
| `cta_validation.py` | Content Intelligence | Low priority |
| `daily_summary_generator.py` | Analytics | System_health_reporter covers this |
| `dashboard_health_checker.py` | Deployment | Redundant with manual checks |
| `dead_directive_detector.py` | DOE Integrity | One-time audit tool, not per-call |
| `deliverable_versioning.py` | Client & Delivery | Git handles versioning |
| `delivery_receipt_generator.py` | Client & Delivery | Process overhead |
| `dependency_chain_validator.py` | Pre-Execution Safety | Edge case |
| `deployment_rollback_tracker.py` | Deployment | Rarely needed |
| `directive_completeness_validator.py` | DOE Integrity | One-time audit tool |
| `directive_coverage_tracker.py` | Analytics | One-time audit tool |
| `directive_script_mapper.py` | DOE Integrity | One-time audit tool |
| `directive_sop_compliance.py` | DOE Integrity | Too rigid |
| `directive_usage_frequency.py` | Analytics | Low value |
| `directive_version_tracker.py` | Workflow Ops | Git handles versioning |
| `duplicate_content_detector.py` | Content Intelligence | Rarely useful |
| `email_deliverability_checker.py` | Content Intelligence | Narrow scope |
| `env_file_sync_checker.py` | Deployment | Redundant with deploy guards |
| `error_categorizer.py` | Analytics | Covered by error_pattern_detector |
| `execution_idempotency_guard.py` | DOE Integrity | More annoying than helpful |
| `execution_output_schema_validator.py` | DOE Integrity | Covered by error_pattern_detector |
| `execution_timeout_guard.py` | Pre-Execution Safety | Low value |
| `funnel_completeness_checker.py` | Workflow-Specific | Too narrow |
| `git_commit_message_validator.py` | Deployment | Low value |
| `google_docs_format_guard.py` | Quality | Low value |
| `google_oauth_token_checker.py` | Pre-Execution Safety | Edge case |
| `headline_effectiveness_scorer.py` | Content Intelligence | Subjective scoring |
| `markdown_lint_validator.py` | Quality | Noisy warnings |
| `modal_deploy_logger.py` | Deployment | Low value logging |
| `modal_health_verifier.py` | Deployment | Manual verification sufficient |
| `modal_secret_validator.py` | Deployment | Covered by modal_deploy_guard |
| `multi_client_context_isolation.py` | Client & Delivery | Edge case |
| `multi_directive_chain_tracker.py` | DOE Integrity | Low value |
| `orphan_script_detector.py` | DOE Integrity | One-time audit tool |
| `output_file_collision_guard.py` | Output Safety | Low priority — files are temp |
| `output_word_count_tracker.py` | Analytics | Covered by output_quality_gate |
| `phase_ordering_enforcer.py` | DOE Integrity | Too rigid |
| `phase_transition_validator.py` | System Intelligence | Too rigid |
| `prerequisite_api_key_mapper.py` | Pre-Execution Safety | Redundant overhead |
| `project_scope_guard.py` | Client & Delivery | Too restrictive |
| `python_import_validator.py` | Pre-Execution Safety | Slow, low value |
| `quality_trend_analyzer.py` | System Intelligence | Low signal |
| `railway_domain_drift_detector.py` | Deployment | Edge case |
| `railway_env_var_completeness.py` | Deployment | Covered by deploy guards |
| `railway_post_deploy_verifier.py` | Deployment | Manual verification sufficient |
| `railway_project_guard.py` | Deployment | Edge case |
| `railway_token_expiry_checker.py` | Deployment | Edge case |
| `research_depth_validator.py` | Quality | Too prescriptive |
| `script_argument_validator.py` | Pre-Execution Safety | Redundant with argparse |
| `script_execution_benchmarker.py` | System Intelligence | Low priority |
| `self_anneal_commit_validator.py` | System Intelligence | Low value |
| `self_anneal_effectiveness_tracker.py` | Analytics | Low value |
| `seo_keyword_validator.py` | Content Intelligence | Too narrow |
| `service_name_convention_guard.py` | Deployment | Edge case |
| `session_productivity_scorer.py` | Analytics | Vanity metric |
| `skill_bible_freshness_checker.py` | DOE Integrity | One-time audit |
| `skill_bible_usage_tracker.py` | Analytics | Low value |
| `slack_notification_dedup.py` | Pre-Execution Safety | Edge case |
| `social_media_format_validator.py` | Content Intelligence | Too narrow |
| `state_file_corruption_detector.py` | Execution Safety | Edge case |
| `tmp_cleanup_monitor.py` | Quality | Low priority |
| `tmp_directory_organizer.py` | Quality | Low priority |
| `tone_consistency_checker.py` | Content Intelligence | Subjective |
| `url_link_validator.py` | Content Intelligence | Low priority |
| `vsl_workflow_enforcer.py` | Workflow-Specific | Too narrow |
| `webhook_slug_validator.py` | Deployment | Edge case |
| `workflow_bottleneck_detector.py` | System Intelligence | Low value |
| `workflow_checkpoint_validator.py` | DOE Integrity | Low value |
| `workflow_completion_tracker.py` | System Intelligence | Low value |
| `workflow_dependency_mapper.py` | Analytics | One-time audit |
| `workflow_input_validator.py` | Pre-Execution Safety | Redundant with argparse |
| `workflow_success_predictor.py` | Pre-Execution Safety | Unreliable predictions |

</details>

---

## How to Restore an Archived Hook

1. **Move the hook back** from `_archived/` to the hooks root:
   ```bash
   mv .claude/hooks/_archived/<hook_name>.py .claude/hooks/
   ```

2. **Add its registration** to `.claude/settings.local.json`:
   - Determine if it's PreToolUse or PostToolUse (check the archived hook's original tier above or read its source)
   - Determine which tool it monitors (Task, Read, Write, Edit, or Bash)
   - Add the entry to the appropriate array:
   ```json
   {
     "tool": "<Tool>",
     "command": "python3 .claude/hooks/<hook_name>.py"
   }
   ```

3. **Verify** by running: `python3 .claude/hooks/<hook_name>.py --status`

## How to Archive an Active Hook

1. Move it: `mv .claude/hooks/<hook_name>.py .claude/hooks/_archived/`
2. Remove its entry from `.claude/settings.local.json`
3. Update this manifest

---

## Notes

- **__pycache__** directories in `.claude/hooks/` can be safely deleted
- Hook state files in `.tmp/hooks/*.json` are not affected by archiving — they just stop being updated
- All 35 active hooks fire on every relevant tool call. Total overhead: ~23 PreToolUse checks + ~14 PostToolUse checks per tool invocation (only matching tool type entries fire)
