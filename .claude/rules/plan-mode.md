# Plan Mode — Plan First, Build Second

## Rule: A minute of planning saves 10 minutes of building.

## When to Use Plan Mode
- Complex multi-step builds (3+ phases)
- New capability creation (Leader Manufacturing)
- Multi-file changes or refactors
- Workflow orchestration with dependencies
- Any task where failure is expensive to undo

## Planning Checklist
Before writing ANY code or running ANY script:

1. **State the goal** — What exactly needs to happen?
2. **Check existing tools** — Does a directive/script/skill bible already exist?
3. **Identify dependencies** — What API keys, files, context needed?
4. **Map the sequence** — What order must steps execute in?
5. **Define done** — What does success look like? What are quality gates?
6. **Identify risks** — What could fail? What's the rollback plan?

## Plan Format
```
GOAL: [one sentence]
EXISTING TOOLS: [directives/scripts that help]
DEPENDENCIES: [API keys, files, context]
STEPS:
  1. [step] → output: [what it produces]
  2. [step] → output: [what it produces]
  3. [step] → output: [what it produces]
QUALITY GATES: [how to validate]
RISKS: [what could go wrong]
```

## Anti-Patterns
- ❌ Jumping straight into code without reading existing directives
- ❌ Creating new scripts without checking if one already exists
- ❌ Running multi-step workflows without checkpoints
- ❌ Skipping context loading "to save time"
- ❌ Assuming API keys are present without checking

## When to Skip Planning
- Single-step tasks (one script, one output)
- Simple lookups or reads
- Tasks with clear, unambiguous instructions
