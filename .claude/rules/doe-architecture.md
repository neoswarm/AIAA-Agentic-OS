# DOE Architecture (Directive-Orchestration-Execution)

## Why DOE
LLMs are probabilistic — 90% accuracy per step = 59% over 5 steps. Push deterministic work into Python scripts. You focus on decision-making.

## Three Layers

**Layer 1: DIRECTIVE** (What to do)
- Location: `directives/*.md`
- Natural language SOPs with inputs, steps, quality gates

**Layer 2: ORCHESTRATION** (You — the Claude agent)
- Read directives, load skill bibles, call scripts in order
- Handle errors, make routing decisions, self-anneal

**Layer 3: EXECUTION** (Doing the work)
- Location: `execution/*.py`
- Deterministic Python scripts for API calls, data processing

## Flow
```
User Request → Directive (SOP) → You (orchestrate) → Script (execute) → Output
```

## Output Destinations
- Local files: `.tmp/*.md`
- Google Docs: formatted, shareable
- Slack: notification with links

## Key Rules
- NEVER inline what a script can do deterministically
- ALWAYS check for existing directives/scripts before creating new ones
- Directive tells WHAT, script does HOW, you decide WHEN and IF
