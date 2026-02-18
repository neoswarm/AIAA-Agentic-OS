# 7-Phase Execution Flow

Every request follows these phases IN ORDER. Do not skip phases.

## Phase 1: Parse User Input
- Extract intent, map to capability
- Examples: "Write a VSL" → `vsl_funnel_orchestrator`, "Research company" → `company_market_research`

## Phase 2: Capability Check
- Directive exists? → Load and execute
- No directive but script exists? → Use script directly
- Nothing exists? → Create new directive + script (Leader Manufacturing)
- Quick check: `ls directives/ | grep -i "<keyword>"` and `ls execution/ | grep -i "<keyword>"`

## Phase 3: Load Context
Priority order:
1. `context/agency.md` → Always first
2. `context/brand_voice.md` → For content creation
3. `clients/{name}/*.md` → For client-specific work
4. `skills/SKILL_BIBLE_*.md` → Domain expertise
5. `directives/*.md` → Workflow SOPs

## Phase 4: Execute Directive
- Check prerequisites (API keys, inputs)
- Run each workflow phase in order
- Save checkpoints to `.tmp/`

## Phase 5: Quality Gates
- Required fields present?
- Output format correct?
- Word count/length appropriate?
- No API errors?

## Phase 6: Delivery
1. Save locally → `.tmp/<project>/<filename>.md`
2. Google Doc → `execution/create_google_doc.py`
3. Slack → `execution/send_slack_notification.py`

## Phase 7: Self-Annealing
- Errors? → Fix script, update directive
- Better approach? → Update skill bible
- Edge case? → Add to directive
