# Self-Annealing Protocol

## Run after EVERY task completion. The system must improve continuously.

## Step 1: Check for Errors
```
Error occurred → Read stack trace → Fix script → Test → Update directive
```
- Did anything fail during execution?
- Were there API timeouts or rate limits?
- Did quality gates catch issues?

## Step 2: Update Directive
Add learnings to the directive file:
- New edge cases discovered
- Better approaches found
- Quality gate refinements
- Missing prerequisites identified

## Step 3: Update Skill Bible
Add domain knowledge to relevant skill bible:
- New techniques that worked
- Mistakes to avoid
- Industry-specific insights

## Step 4: Commit Changes
```bash
git add directives/ execution/ skills/
git commit -m "Self-anneal: [what was learned]"
```

## When to Self-Anneal
- Script fails → Fix and document
- Output quality is low → Tighten quality gates
- New pattern discovered → Add to skill bible
- Missing capability → Create directive + script (Leader Manufacturing)
- Edge case hit → Add to directive's Edge Cases section

## Anti-Patterns
- ❌ Skipping annealing because "it worked fine"
- ❌ Making fixes without committing them
- ❌ Updating code without updating the directive
- ❌ Ignoring recurring errors (check error_pattern_detector)
